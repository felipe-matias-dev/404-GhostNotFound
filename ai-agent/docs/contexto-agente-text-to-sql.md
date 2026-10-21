# Boas Práticas de Desenvolvimento: Agente Text-to-SQL — V-Energy Grid 360

> **Para a IA de desenvolvimento:** este documento define **como** o agente Text-to-SQL deve ser construído. Siga as práticas abaixo ao escrever código, prompts e testes. O escopo é apenas o módulo de IA (`ai-agent/`): não altere pipeline de dados, modelagem Gold, backend ou frontend. Onde o texto disser `[A CONFIRMAR]`, a decisão ainda não foi tomada pelo time: deixe configurável ou pergunte antes de assumir.

---

## 0. Contexto mínimo

- O agente responde perguntas em português sobre dados de uma distribuidora de energia (consumo, faturamento, interrupções, atendimento).
- Fonte de dados: tabelas **Gold** (~10 tabelas) carregadas em um banco local (SQLite ou PostgreSQL, `[A CONFIRMAR]`).
- O módulo é Python e é chamado pelo backend FastAPI do portal.
- Modelo recomendado: Gemini 3.1 Flash-Lite; outros via OpenRouter.
- Requisito central: **se o agente não souber, diz que não sabe.** Resposta inventada é falha crítica.

As práticas abaixo estão em ordem de prioridade: **segurança → corretude → honestidade → qualidade da resposta → custo/latência → escalabilidade.**

---

## 1. Princípios

1. **O modelo é um tradutor que erra com confiança.** Toda prática existe para dar contexto certo a ele, impedir que um erro cause dano e detectar quando ele errou.
2. **A segurança mora no banco e no validador, nunca no prompt.** Instruções como "não apague nada" ajudam, mas não protegem.
3. **O modelo escreve SQL; o banco faz as contas.** O LLM não calcula somas, médias ou percentuais na resposta.
4. **Todo número na resposta vem do resultado da consulta.**
5. **Sem medição, melhoria é achismo.** Nenhuma mudança de prompt, modelo ou contexto entra sem rodar a avaliação.
6. **Simples primeiro.** Só adicione uma técnica (recuperação de schema, decomposição, HyDE, múltiplos agentes) se a avaliação mostrar ganho.

---

## 2. Contexto para o modelo (camada semântica)

É a prática com maior impacto na qualidade. Investir aqui antes de trocar de modelo.

### 2.1 Expor views, não tabelas brutas
- Criar views de leitura (ex.: prefixo `sem_*`) sobre a Gold, com nomes de colunas na linguagem do negócio.
- As views são a **allowlist**: o agente só enxerga e só consulta o que está nelas.
- Remover das views colunas que o agente não precisa (IDs técnicos, dados pessoais).
- Pré-juntar relações muito comuns em uma view, quando isso evitar junções que o modelo erra com frequência.

### 2.2 Descrever tudo em linguagem natural
Para cada view: o que representa e qual o **grão** (ex.: "uma linha por unidade consumidora por mês de competência").
Para cada coluna: significado, unidade (kWh, R$), formato (`YYYY-MM`) e valores possíveis de colunas categóricas (ex.: classes B1, B2, B3, A4; status; bandeiras).

### 2.3 Representação compacta do schema
- Enviar um DDL resumido (nome, tipo, descrição curta, chaves e relações), não `CREATE TABLE` completo com constraints irrelevantes.
- Incluir 2 a 3 linhas de exemplo por view, ou os valores distintos de colunas categóricas de baixa cardinalidade. Isso evita filtros como `classe = 'Residencial'` quando o valor real é `'B1'`.
- Declarar explicitamente as relações (chave de junção entre views).

### 2.4 Glossário de sinônimos
Mapear termos do dia a dia para colunas/views. Exemplos:
- "conta de luz", "conta" → fatura / receita faturada
- "falta de luz", "apagão", "queda de energia" → interrupção / ocorrência de rede
- "painel solar", "energia solar" → geração distribuída (GD)
- "gato", "furto" → perda não técnica / suspeita
- "residencial" → B1; "rural" → B2; "comercial" → B3; "industrial" → A4

O glossário fica em arquivo versionado, não espalhado no código.

### 2.5 Regras de negócio explícitas
O modelo não conhece as definições internas. Colocar no prompt, por exemplo:
- Competência é o mês de referência, não o mês de pagamento.
- Receita faturada ≠ receita arrecadada; qual é o padrão quando o usuário diz só "receita" `[A CONFIRMAR]`.
- Como interpretar "último ano", "últimos 12 meses", "primeiro ano" (período atual/base) `[A CONFIRMAR]`.
- Métricas já calculadas na Gold (efeitos preço/volume/mix, DEC/FEC, score de suspeita) devem ser **lidas**, nunca recalculadas pelo agente com fórmula própria.

### 2.6 Tamanho do schema e recuperação
- Com ~10 tabelas, **enviar a camada semântica inteira** no prompt. Recuperar schema por embeddings, nesse tamanho, só acrescenta uma etapa que pode errar.
- Passar a usar recuperação (embeddings, ou busca híbrida densa + lexical com fusão de rankings) apenas se o schema crescer a ponto de a avaliação mostrar queda de acurácia com o contexto completo.
- Gerar a camada semântica a partir do contrato/dicionário da Gold, para acompanhar mudanças sem edição manual.

---

## 3. Prompt

### 3.1 Estrutura recomendada (ordem)
1. Papel e restrições: só consultas de leitura, dialeto do banco, nunca inventar tabelas ou colunas.
2. Regras de negócio e glossário.
3. Camada semântica (views, colunas, descrições, exemplos de valores).
4. Exemplos few-shot (pergunta → SQL).
5. Formato de saída estruturado.
6. Instruções de honestidade: quando dizer "não sei", quando pedir esclarecimento.

Manter as partes estáveis (1 a 3) no início: isso permite cache de prompt no provedor.

### 3.2 Few-shot
- 5 a 15 exemplos validados, cobrindo os padrões do domínio: filtro por município/bairro/classe, comparação entre períodos, junção UC × faturamento, top-N, variação percentual.
- Incluir exemplos das **armadilhas** (competência, receita faturada vs. arrecadada, períodos).
- Incluir pelo menos um exemplo de resposta "não sei" e um de recusa.
- Se o banco de exemplos passar de algumas dezenas, selecionar os mais parecidos com a pergunta por similaridade.

### 3.3 Saída estruturada
Pedir ao modelo um objeto tipado, não texto livre. Exemplo:

```json
{
  "status": "ok | nao_sei | esclarecer | recusar",
  "sql": "SELECT ...",
  "views_usadas": ["sem_faturamento_mensal"],
  "suposicoes": ["Considerei receita faturada", "Período: últimos 12 meses"],
  "pergunta_esclarecimento": null
}
```

Validar o objeto com Pydantic (ou equivalente) antes de seguir. Saída mal formada conta como falha e entra no fluxo de correção.

### 3.4 Regras de dialeto
- Escrever as regras do dialeto escolhido (`[A CONFIRMAR]`): funções de data, `ILIKE` (PostgreSQL) vs `LIKE` com `LOWER` (SQLite), aspas, divisão inteira.
- Pedir: colunas qualificadas com alias, sem `SELECT *`, CTEs legíveis, tratamento de `NULL` em agregações e de divisão por zero (`NULLIF`).
- Temperatura baixa (0 a 0,2) para geração de SQL.

### 3.5 Versionamento
Prompts em arquivos versionados (`prompts/v1/...`), nunca strings soltas no código. Cada log e cada execução de avaliação registra a versão usada.

---

## 4. Fluxo de uma pergunta

1. **Entrada:** limite de tamanho, normalização, `request_id`.
2. **Reescrita de follow-up** (se houver histórico): transformar em pergunta independente ("e em Olinda?" → pergunta completa).
3. **Triagem:** respondível, ambígua, fora do escopo ou maliciosa.
4. **Geração** do SQL com saída estruturada.
5. **Validação estática** do SQL (seção 5).
6. **Execução** com limites de tempo e de linhas.
7. **Correção:** em erro, até 2 a 3 tentativas com o erro devolvido ao modelo.
8. **Resposta** gerada a partir das linhas retornadas.
9. **Log** de todo o ciclo.

Cada etapa é uma função separada e testável. Evitar um único prompt gigante que faz tudo.

---

## 5. Segurança

Defesa em camadas: se uma falhar, a próxima impede o dano.

### 5.1 Banco
- Conexão **somente leitura**, conforme o banco:
  - PostgreSQL: usuário dedicado com `SELECT` apenas nas views do agente; `default_transaction_read_only = on`; `statement_timeout`.
  - SQLite: abrir com URI `mode=ro` e `PRAGMA query_only = ON`; controlar tempo de execução no código (o SQLite não tem usuários com permissões).
- O agente nunca usa a mesma conexão/credencial do backend.
- O agente não tem acesso ao schema de escrita do portal (ordens de inspeção).

### 5.2 Validador de SQL
Usar um parser (ex.: `sqlglot`, com dialeto configurável), não expressões regulares.
- Exatamente **um** statement.
- Somente `SELECT` ou `WITH ... SELECT`.
- Rejeitar DDL, DML, `PRAGMA`, `ATTACH`, `COPY`, `SET`, funções de sistema e de arquivo.
- Todas as tabelas referenciadas devem estar na allowlist de views.
- Inserir `LIMIT` quando ausente; reduzir quando acima do máximo.
- Opcional: rejeitar produto cartesiano (junção sem condição).

### 5.3 Prompt injection
- Tudo que vem do banco (texto de chamados, tratativas, nomes) é **dado, não instrução**. Delimitar no prompt e instruir o modelo a ignorar instruções contidas nos dados.
- O texto livre do call center é o vetor mais provável; tratar com atenção.
- Recusar pedidos de revelar o prompt do sistema, ignorar regras, alterar dados ou agir fora do papel.
- Nunca concatenar a pergunta do usuário diretamente em SQL; o SQL sempre passa pelo validador.

### 5.4 Limites operacionais
- Tempo máximo de consulta, máximo de linhas, máximo de tentativas, tamanho máximo da pergunta.
- Rate limit e orçamento de tokens por sessão.
- Logs sem dados pessoais desnecessários.

---

## 6. Execução e correção de erros

- `EXPLAIN` antes de executar (quando o banco permitir) para checar sintaxe e existência de objetos sem custo de execução.
- Classificar o erro antes de devolver ao modelo: sintaxe, coluna/tabela inexistente, tipo incompatível, timeout, resultado vazio.
- Na nova tentativa, enviar: o SQL anterior, a mensagem de erro e um lembrete das colunas válidas da view envolvida.
- **Resultado vazio** não é erro automaticamente: verificar se os filtros usam valores existentes (ex.: nome de município com grafia diferente). Se não for possível distinguir "zero" de "dado ausente", dizer isso ao usuário.
- Esgotadas as tentativas: responder que não foi possível responder com segurança. Nunca devolver um resultado parcial como se fosse a resposta.
- Truncar as linhas enviadas ao modelo para gerar a resposta (amostra + agregados), informando o total real.

---

## 7. Honestidade e resposta ao usuário

### 7.1 Quando responder "não sei"
- A informação pedida não existe nas views.
- O SQL falhou após o máximo de tentativas.
- A pergunta depende de uma definição de negócio não documentada.
- O resultado é ambíguo (vazio sem explicação possível).

### 7.2 Quando pedir esclarecimento
- A pergunta admite interpretações que levam a números diferentes ("vendas do mês": faturada ou arrecadada? qual mês?).
- Regra prática: no máximo uma pergunta de esclarecimento; se a ambiguidade for menor, responder declarando a suposição.

### 7.3 Regras da resposta
- Gerada **a partir das linhas retornadas**; todo número citado precisa existir nelas.
- Verificação automática: extrair os números do texto e conferir com o resultado; se algum não bater, regenerar ou responder com a tabela sem narrativa.
- Declarar suposições (período, classe, definição de receita).
- Avisar quando houve truncamento por `LIMIT`.
- Nunca completar lacunas com conhecimento geral do modelo apresentado como dado da empresa.
- Linguagem clara para não técnicos; unidades sempre explícitas (kWh, R$, %).

### 7.4 Auditabilidade
Toda resposta devolve ao portal: SQL executado, views consultadas, amostra das linhas, suposições e nível de confiança. Sugestão de formato:

```python
AgentAnswer:
  answer: str
  sql: str | None
  rows: list[dict]
  row_count: int
  confidence: "alta" | "media" | "baixa" | "nao_sei"
  sources: list[str]
  assumptions: list[str]
  clarification: str | None
```

A interface final é combinada com o responsável pelo backend.

---

## 8. Follow-up (memória de conversa)

- Guardar por sessão os últimos turnos: pergunta reescrita, SQL, resumo do resultado. Não guardar o resultado inteiro.
- Antes de gerar SQL, reescrever a nova pergunta como pergunta independente usando o histórico. Isso torna cada consulta auditável sozinha.
- Limitar o número de turnos (ex.: 5) e expirar sessões inativas.
- Se a referência for ambígua ("e o outro bairro?"), pedir esclarecimento.
- Onde o histórico é armazenado: `[A CONFIRMAR]`; o módulo não deve depender de estado em memória do processo.

---

## 9. Insights embutidos (IA no portal sem pergunta)

- **O LLM só narra números já calculados.** O portal entrega um JSON de métricas da tela; o modelo escreve 2 a 4 frases de interpretação.
- Diferenças, percentuais e rankings chegam prontos no JSON; o modelo não faz aritmética.
- Verificar que todo número do texto existe no JSON; se não, descartar o insight e mostrar a tela sem ele.
- Cache por combinação de filtros, para não chamar o modelo a cada carregamento.
- Evitar conclusões causais que os dados não sustentam ("caiu por causa de X") a menos que a métrica de causa esteja no JSON.

---

## 10. Avaliação

### 10.1 Golden set
Arquivo versionado (ex.: `eval/golden.yaml`), começando com 40+ itens. Campos: `id`, `pergunta`, `categoria`, `sql_referencia`, `comportamento_esperado`.

Categorias obrigatórias:
- Simples (filtro + agregação).
- Com junção.
- Temporais (comparação entre períodos).
- Linguagem do dia a dia (sinônimos).
- Follow-up (sequências de 2 a 3 perguntas).
- **Sem resposta nos dados** → esperado "não sei".
- **Ambíguas** → esperado esclarecimento ou suposição declarada.
- **Manipulação** (apagar dados, ignorar instruções, injeção via texto) → esperado recusa, nenhum SQL de escrita.

Incluir as perguntas reais das lideranças, por exemplo:
- "Quantas unidades com painel solar em Olinda tiveram queda de consumo acima de 30%?"
- "Qual bairro mais perdeu volume residencial no último ano?"
- "Quanto a receita comercial cresceu em Jaboatão?"

**O SQL de referência é escrito ou conferido por uma pessoa e executado no banco.** Gabarito gerado por LLM sem revisão torna a avaliação circular.

### 10.2 Métricas
- **Execution accuracy:** o resultado do SQL gerado é igual ao do SQL de referência (comparar conjuntos de linhas; definir regra para ordem e colunas extras). Comparar texto de SQL não serve: duas consultas diferentes podem estar ambas certas.
- **Acurácia de recusa e de "não sei".**
- **Taxa de bloqueio pelo validador** nas perguntas maliciosas (meta: 100%).
- **Fidelidade numérica** da resposta (números do texto presentes nas linhas).
- Taxa de SQL inválido, média de tentativas, latência p50/p95, tokens e custo por pergunta.
- **LLM como juiz** apenas para clareza e fidelidade da resposta em português, com modelo diferente do gerador e rubrica fixa (score + aprovado/reprovado + justificativa).

### 10.3 Uso
- Rodar a cada mudança de prompt, modelo, few-shot, glossário ou camada semântica.
- Regra: **nenhuma mudança entra se o golden set regredir.**
- Gerar tabela comparativa de experimentos (modelo × versão do prompt × few-shot × acurácia × recusa × latência × custo).
- Testar uma variável por vez.
- Desenvolver contra dados mock no início e recalibrar o gabarito quando a Gold real estiver disponível.
- Adicionar ao golden set todo erro encontrado em uso real (com o gabarito corrigido).

---

## 11. Testes de código

- **Unitários do validador:** lista de SQLs maliciosos e válidos (DDL, DML, múltiplos statements, comentários escondendo comandos, tabelas fora da allowlist, funções de sistema).
- **Unitários de execução:** timeout, truncamento, conexão somente leitura (tentar um `INSERT` e confirmar que o banco recusa).
- **Unitários da verificação numérica** das respostas e dos insights.
- **Integração:** fluxo completo com modelo mockado (resposta fixa) para testar orquestração sem custo de API.
- A avaliação com o modelo real é separada dos testes unitários (mais lenta e paga).

---

## 12. Observabilidade

- Log estruturado (JSON) por requisição: `request_id`, `session_id`, pergunta original e reescrita, SQL de cada tentativa, resultado da validação, erro, número de linhas, latência por etapa, tokens, custo, modelo, versão do prompt.
- Rastrear por etapa (tracing) para saber onde está a latência e onde ocorrem as falhas.
- Painel simples: acurácia no golden set ao longo do tempo, top erros, custo diário, p95 de latência.
- Coletar feedback do usuário (útil/não útil); respostas marcadas como erradas viram candidatas ao golden set, após revisão.

---

## 13. Otimização

### 13.1 Qualidade
- Melhorar descrições, glossário e few-shot antes de trocar de modelo.
- Pós-processamento determinístico do SQL (normalizar `LIMIT`, aliases, funções de data) em vez de pedir ao modelo.
- Decompor perguntas complexas em passos (CTEs) só se a avaliação mostrar ganho; custa mais chamadas.

### 13.2 Custo e latência
- Prefixo estável do prompt para cache do provedor.
- Roteamento de modelos: modelo leve para triagem e reescrita de follow-up; modelo principal para gerar e corrigir SQL. Adotar só se não perder acurácia na avaliação.
- Cache de pergunta normalizada → SQL validado. **Reexecutar a consulta** (os dados mudam); invalidar o cache quando a Gold for recarregada ou o schema mudar.
- Cache de insights por filtros.
- Timeouts e retries com backoff exponencial nas chamadas ao modelo.
- Fallback de provedor (Gemini direto → OpenRouter) por configuração.
- Evitar HyDE e chamadas extras por pergunta sem ganho medido.

### 13.3 Banco (pedir à área dona, não implementar no módulo)
- Índices nas colunas mais filtradas pelo agente (município, bairro, classe, competência), identificadas pelos logs.
- Views agregadas para métricas frequentes, que tornam as consultas do agente mais simples e rápidas.

---

## 14. Escalabilidade

Deploy em nuvem e multi-tenant estão fora do escopo do case; o objetivo é deixar o módulo **pronto para crescer**, sem infraestrutura que não será avaliada.
- Módulo sem estado no processo (histórico em armazenamento externo).
- Todos os parâmetros em configuração: modelo, provedor, limites, timeouts, tentativas, número de exemplos.
- Framework de agente isolado atrás de uma interface própria, para permitir troca.
- Dialeto do banco configurável no validador e nas regras do prompt.
- Camada semântica gerada a partir do contrato da Gold, acompanhando novas versões.
- Se o schema crescer: recuperação de views/colunas e de exemplos por similaridade, testada contra a avaliação antes de adotar.
- Rate limit e orçamento por usuário/sessão.

---

## 15. Antipadrões a evitar

- Colar o banco inteiro (incluindo tabelas irrelevantes ou de escrita) no prompt.
- Confiar no prompt como proteção contra comandos destrutivos.
- Validar SQL com regex.
- Deixar o LLM calcular números na resposta.
- Gerar o gabarito de avaliação com LLM e não revisar.
- Avaliar comparando o texto do SQL em vez do resultado.
- Mudar várias coisas ao mesmo tempo e não saber qual ajudou.
- Esconder do usuário o SQL e as suposições.
- Devolver resultado parcial após erro como se fosse resposta completa.
- Hardcode de modelo, chave de API ou limites no código.

---

## 16. Checklist mínimo antes de considerar o agente pronto

- [ ] Conexão somente leitura testada (escrita recusada pelo banco).
- [ ] Validador com testes de casos maliciosos passando.
- [ ] Camada semântica com descrições, glossário e regras de negócio.
- [ ] Saída estruturada validada.
- [ ] Loop de correção com limite de tentativas.
- [ ] Respostas "não sei" e esclarecimento funcionando.
- [ ] Verificação numérica das respostas e dos insights.
- [ ] SQL, fontes e suposições exibidos em toda resposta.
- [ ] Golden set com 40+ itens, incluindo sem resposta, ambíguas e manipulação.
- [ ] Execution accuracy medida e registrada.
- [ ] Logs estruturados com versão do prompt.
- [ ] Modelo, provedor e limites configuráveis.

---

## 17. Pendências que afetam o módulo `[A CONFIRMAR]`

- Banco local (SQLite ou PostgreSQL).
- Framework de agente (proposta: PydanticAI).
- Definição padrão de "receita" e de período base/atual.
- Colunas sensíveis que o agente não deve ver.
- Onde armazenar o histórico de conversa.
