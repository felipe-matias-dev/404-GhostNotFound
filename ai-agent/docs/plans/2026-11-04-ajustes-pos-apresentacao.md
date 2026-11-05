# Ajustes do agente depois da apresentação: plano

**Objetivo:** toda pergunta feita pelo portal sai com a resposta certa, em texto claro e em poucos segundos. O texto de reserva (determinístico) passa a ser raro e, quando aparecer, legível. Nenhuma mudança afrouxa a regra central: número que não vem do banco não chega ao usuário.

**Branch:** `feat/ai-agent-ajustes-pos-apresentacao`, a partir da `main` com o PR #143.

**Origem:** a apresentação de 04/11/2026 e a reprodução da mesma conversa pelo portal, com a `main` final, na Gold real.

## Decisões do Luis Felipe (04/11/2026)

- **D1:** resolver no agente, com glossário e few-shot ("percentual de tributos = (receita_faturada − receita_energia) / receita_faturada"), sem pedir coluna nova a Dados.
- **F1:** fazer a correção certa: o `AgentAnswer` traz a unidade de cada coluna e o portal formata por ela (mudança de contrato, registrada em DEC).
- **B1:** o modelo pago do OpenRouter vira o principal.
- **E:** hipótese do Luis Felipe: a falha de memória pode vir do usuário usado na apresentação. Investigar o que muda por usuário (orçamento, sessão, posse).
- **Meta:** perguntas complexas (comparação de períodos, decomposição, "por que", percentuais, follow-ups) respondidas certo e com o texto do modelo. Ganham um conjunto próprio no golden set.

## O que aconteceu

| # | Pergunta no portal | O que saiu | Causa, pelo log |
|---|---|---|---|
| 1 | "Qual foi a receita do mês de junho de 2026?" | Certo: R$ 11.188.360,10, em 4 s | — |
| 2 | "Quanto era a receita sem tributos?" | Na apresentação: "De qual mês?". Na reprodução: certo, usando junho de 2026, mas em 29 s | Na reprodução o histórico foi lido. Na apresentação, ainda sem causa confirmada (ver A6) |
| 3 | Pergunta longa da diretora (tarifa +10,5%, energia −4%, receita +8%) | Texto de reserva: "A consulta devolveu 1 linha(s). Resultado: receita base = …, efeito preco = …" | As duas narrativas foram recusadas pelo número "12": a regra das durações (DEC-079) exige "últimos/primeiros 12 meses" |
| 4 | "Quanto era o percentil de tributos na receita de junho" | Texto de reserva com "25%", e a tabela do portal mostrou "R$ 25,00" | (a) bug do #143: o valor chega arredondado ao redator ("25"), mas a checagem exige que um inteiro seja igual ao valor exato; (b) a segunda narração estourou o prazo de 30 s, porque a geração do SQL levou 23,6 s; (c) o frontend formata `percentual_tributos` como R$ porque testa "tributo" antes de "percentual" |

Problemas transversais vistos no portal:
- **Latência de 20 a 29 s:** o Gemini gratuito principal estoura o limite de 15 s por chamada, e só então a pergunta passa para o modelo seguinte da cadeia.
- **Nomes técnicos na caixa de suposições** (`receita_faturada`, `sem_kpis_mensais`): o `AgentAnswer.assumptions` sai como o gerador escreveu.
- **Texto de reserva cru:**
  - "efeito preco" sem cedilha;
  - "R$ -4.656.505,19" em vez de "-R$ 4.656.505,19";
  - ponto final duplicado ("(sem tributos)..");
  - "devolveu 1 linha(s)".
- **SQL com coluna inexistente:** `tributos` em `sem_kpis_mensais`. A correção automática resolveu, mas custou uma ida a mais ao modelo.

## Tarefas

Ordem por impacto na resposta que o usuário vê. Cada tarefa tem teste antes do código (TDD só para regra do projeto). Mudança de prompt, few-shot, glossário ou camada vai para uma versão nova e só entra se o golden set não regredir (DEC-016).

### A. Checagem da narrativa (o texto certo não pode ser recusado)

- **A1. Inteiro arredondado (bug do #143).**
  - **Regra nova:** um número sem casas decimais vale quando é igual a `rounded_for_display(valor)` de alguma linha. "25" vale para 24,9999…; "3" continua não valendo para 2,6, porque `rounded_for_display(2,6)` é 2,6 (DEC-070).
  - **Onde:** `domain/numbers.py` (`_supported`).
  - **Testes:**
    - 24,99999999 com "25%";
    - 2,6 com "3" continua recusado;
    - 100,0000001 com "100".
- **A2. Durações sem "últimos".**
  - **Regra nova:** a duração dita na pergunta ou nas suposições vale também quando a narrativa a escreve só com a unidade: "12 meses", "as 12 competências", "períodos de 12 meses".
  - **Limite:** só com a unidade de período logo depois do número. "12 UCs" e "10 anos" de idade continuam recusados quando "10 anos" não é duração da pergunta.
  - **Onde:** `DURATION` em `domain/numbers.py`. A pergunta e as suposições continuam exigindo "primeiros/últimos", para que só uma duração de período libere o número.
  - **Testes:**
    - a narrativa da pergunta da diretora;
    - "períodos de 12 meses" passa;
    - "Há 12 UCs" continua recusado.
- **A3. Números da pergunta repetidos como premissa.** A pergunta da diretora traz 10,5%, 4% e 8%. Uma narrativa que diga "a tarifa subiu 10,5%, como você disse" seria recusada, e deve continuar assim: o agente não confirma número que não leu do banco.
  - **Prompt `answer/v5`:** pedir que a narrativa explique a causa só com os números das linhas e não repita as porcentagens da pergunta.
  - **Few-shot:** um exemplo com a pergunta da diretora.
- **A4. Motivo da recusa mais útil.**
  - Quando o número recusado está na pergunta, o motivo diz isso: "o 12 está só na pergunta; escreva 'nos últimos 12 meses' ou não cite".
  - **Testes:** o texto do feedback para cada caso.

### B. Tempo de resposta (a segunda chance precisa caber no prazo)

- **B1. Modelo principal pago.**
  - **Mudança:** `openrouter:google/gemini-3.1-flash-lite` como principal no `.env.example` da raiz e no README. O Gemini gratuito vira reserva ou sai da cadeia.
  - **Por quê:** é o mesmo modelo avaliado, sem os 15 s de espera de cada falha do plano gratuito.
  - **Medição:** latência p50/p95 da rodada completa com essa cadeia.
- **B2. Reserva de tempo para a narração.**
  - **Regra nova:** a geração do SQL e as correções param a tempo de sobrar pelo menos `narration_reserve_seconds` (proposta: 8 s) do prazo de 30 s. Sem essa folga, a resposta vai direto para o texto de reserva, sem tentar uma narração que vai estourar.
  - **Onde:** `ask.py`.
  - **Testes:**
    - geração lenta deixa a narração sem tempo e o resultado sai no texto de reserva;
    - com folga, a segunda narração acontece.
- **B3. Tempo limite por chamada.** Medir se 15 s ainda é o certo com o modelo pago. A mediana do flash-lite pago é de 2 a 4 s, então 10 s corta mais cedo uma chamada travada. Decidir pela medição, não por chute.

### C. Texto de reserva legível (quando aparecer, a pessoa entende)

- **C1. Rótulos das colunas.**
  - **Mudança:** cada coluna ganha um rótulo curto em português na camada semântica (`label`, com acento: "efeito preço", "receita de energia"), usado no texto de reserva no lugar de `nome.replace('_', ' ')`. Alias desconhecido continua em palavras.
  - **Onde:** camada semântica 0.5.0, `semantic_source.py`, `ask.py`.
  - **Testes:** validação do YAML e o texto de reserva com rótulos.
- **C2. Formato dos valores.**
  - "-R$ 4.656.505,19" em vez de "R$ -4.656.505,19";
  - sem ponto duplicado depois das suposições;
  - "1 linha" e "N linhas", sem "(s)";
  - com uma linha só, em vez de "A consulta devolveu 1 linha(s). Resultado: x = 1, y = 2", o texto vira "Resultado: x = 1; y = 2.".
- **C3. Suposições em palavras no `AgentAnswer`.**
  - **Mudança:** as suposições já vão em palavras para o redator (DEC-070); passam a ir assim também no `AgentAnswer.assumptions`, que o portal mostra.
  - **Limite:** as suposições com nome de view somem ("na view sem_kpis_mensais" vira "nos totais mensais"), por uma tabela de nomes da camada.
  - **Testes:** sem `TECHNICAL_NAME` nas suposições da resposta.

### D. SQL certo na primeira tentativa

- **D1. Tributos nos totais mensais.**
  - `sem_kpis_mensais` não tem `tributos`. Duas saídas:
    - pedir a Dados a coluna `tributos` na `gold_kpis_mensais`, avisando no mesmo PR (regra do `CLAUDE.md`);
    - ou glossário mais few-shot para "percentual de tributos = (receita_faturada − receita_energia) / receita_faturada".
  - Preferir a primeira, que não deixa conta para o modelo.
- **D2. "Por que a receita subiu menos que a tarifa".**
  - Na reprodução, o modelo usou `efeito_preco` agregado. O certo é separar `efeito_tarifa` e `efeito_bandeira` (`efeito_preco` = tarifa + bandeira), como no G104.
  - **Mudança:** few-shot com a pergunta da diretora, sem mudar o SQL de referência do G104.

### E. Memória da conversa

- **E0. Causa provável, confirmada no portal (04/11):**
  - **O que acontece:** ao abrir o portal, o `AgenteProvider` cria uma conversa nova e vazia, mas o `mesclarSessoes` a descarta quando a lista de conversas salvas do usuário chega (`frontend/src/features/agente/conversions.ts`). Sem `sessaoAtivaId`, o chat passa a usar a conversa salva mais recente.
  - **Efeito:** com um login que já tinha conversas (o do ensaio), a primeira pergunta da apresentação entrou numa conversa antiga. O agente leu os 3 últimos turnos dela, perguntas de outros meses misturadas com a de junho, e pediu "De qual mês?".
  - **Correção:**
    - o chat sempre abre numa conversa nova, e as salvas ficam no histórico;
    - teste de frontend para a mescla com a lista chegando antes da primeira pergunta.
  - **No agente:** o prompt de SQL deixa explícito que a referência de um follow-up é o turno mais recente do histórico (few-shot com dois turnos de meses diferentes).
- **E1. Causa da falha na apresentação.**
  - Ler na auditoria do Doctah (`app.ai_auditoria` ou `GET /ai/audit/{id}`, perfil TI) as respostas da conversa: `model`, `sql`, `status` e `session_id` de cada turno.
  - **Hipóteses:**
    - o turno foi respondido por um modelo de reserva que usa pior o histórico;
    - o widget abriu outra sessão;
    - a API estava com uma imagem anterior.
- **E2. Follow-up com cada modelo da cadeia.**
  - Rodar os follow-ups do golden com cada modelo sozinho (`VENERGY_AGENT_LLM_MODEL=...` e `FALLBACK_MODEL=` vazio).
  - O modelo que errar mais de 1 de 6 sai da cadeia ou ganha um few-shot de follow-up no prompt `v4` de SQL.
- **E3. Sessão no portal.**
  - Teste de ponta a ponta no frontend: duas perguntas no widget e duas na página Agente, conferindo que o `session_id` é o mesmo nos dois turnos. O teste é do frontend; o GenAI escreve o caso.

### F. Portal (com o time do frontend)

- **F1. Formato pela unidade, não pelo nome.**
  - O `formatarCelulaResultado` testa "tributo" antes de "percentual", e por isso `percentual_tributos` sai em R$.
  - **Correção mínima:** testar percentual primeiro.
  - **Correção certa:**
    - o `AgentAnswer` passa a trazer a unidade de cada coluna (`column_units`, com `unit_of` da camada) e o frontend formata por ela;
    - é mudança de contrato e se combina com o V1 (spec §4, DEC-020).
- **F2. Tempo de espera visível.** Com B1 e B2 a espera deve cair para poucos segundos. Se a resposta passar de 10 s, a tela diz que está demorando, em vez de só "Escrevendo a resposta".

### G. Avaliação (provar que ficou certo)

- **G1. Itens novos no golden set (0.19.0).** Entram como `revisado_por: null` até Dados conferir:
  - a conversa da apresentação como cadeia de follow-up: receita de junho de 2026 → "Quanto era a receita sem tributos?" → "quanto era o percentual de tributos na receita de junho";
  - a pergunta longa da diretora, com o gabarito da decomposição;
  - variações de duração: "nos últimos 12 meses", "no último ano", "nos 12 meses mais recentes".
- **G2. Taxa de texto de reserva como métrica.**
  - **Métrica nova:** `fallback_rate` no relatório (respostas `answered` cujo texto final é o de reserva), lida do log da etapa `resposta`.
  - **Por quê:** hoje a fidelidade numérica mistura isso com o resto.
  - **Também:** `make eval-compare` mostra a nova métrica.
- **G3. Rodada pelo caminho do portal.**
  - **Script:** novo, em `backend/`, faz conversas pelo `POST /ai/ask/stream` com login, como o frontend.
  - **Por quê:** a rodada do golden chama o agente direto, sem backend, sem auditoria real e sem o histórico do banco. A apresentação passou por esse caminho, e a avaliação não.
- **G3b. Validação no frontend (pedido do Luis Felipe).**
  - **O que:** toda tarefa termina validada no portal, no navegador, com login, pelo widget e pela página Agente.
  - **Como:** a conversa da apresentação e o conjunto de perguntas complexas (G1) são feitos na tela, e o que vale é o texto, a tabela e as suposições exibidos, não só o JSON da API.
  - **Registro:** o resultado de cada pergunta vai para a DEC final.
- **G4. Rodada completa e comparação** com a de 04/11 (`eval/runs_gold/2026-11-04T195529Z.json`).

## Critérios de aceite

| Métrica (Gold real, rodada completa) | 04/11 | Meta |
|---|---|---|
| execution accuracy | 98,5% | ≥ 98%, nenhum item piora |
| status certo | 100% | 100% |
| `failed` | 0% | 0% |
| texto de reserva (`fallback_rate`) | 1 de 65 pelo log, sem métrica | ≤ 2% |
| juiz | 89,7% | ≥ 95% |
| latência p50 / p95 | 3,3 s / 27,4 s | ≤ 4 s / ≤ 12 s |
| conversa da apresentação pelo portal (G3), 3 execuções | — | 3 de 3 com o texto do modelo e os números certos |
| red team | 0 violações | 0 violações |

## Ordem de execução

1. A1 e A2: o bug do #143 e a regra das durações. São pequenos, com teste, e resolvem as duas respostas ruins da apresentação.
2. B1 e B2: modelo pago e reserva de tempo. Sem eles, a segunda chance não cabe no prazo.
3. C2 e C3: texto de reserva e suposições sem nome técnico.
4. G1 e G2: itens novos e métrica do texto de reserva; rodada completa.
5. D1, D2, A3 e A4: SQL e prompt, com uma rodada a cada versão nova de prompt (DEC-016).
6. E1 a E3: memória, assim que houver a auditoria do Doctah.
7. C1 e F1: rótulos na camada e unidade no contrato, combinados com Dados e com o V1.
8. G3 e G4: rodada pelo portal e comparação final; DEC nova com as medições.

## Estado (04/11/2026)

- **Feito nesta branch, com teste e validado no portal:** A1 a A4, B1 e B2, C1 a C3, D1, D2, E0, F1, G1 e G2, todos registrados na DEC-080.
  - C1 foi feito com rótulos no agente (`domain/wording.py`), não na camada.
  - Entraram ainda três travas que não estavam no plano: ano não pedido vira esclarecimento, checagem de unidade e meses dentro de um `BETWEEN`.
- **Fica para o plano de robustez:** E1 a E3 (memória com cada modelo da cadeia), F2, G3 e G4 e a pendência das casas decimais da tabela. Esse plano exige que tudo seja validado pela tela do portal nos 5 usuários: [2026-11-05-robustez-do-agente.md](2026-11-05-robustez-do-agente.md).

## Fora deste plano

- Reescrever o texto de reserva com o modelo: ele existe justamente para quando o modelo falha.
- Aceitar qualquer número da pergunta: a pergunta pode trazer premissa falsa (DEC-079).
