# Robustez do agente, lote 4: interpretações corrigíveis, análises prontas e várias consultas

**Objetivo:** fechar as três tarefas do plano de robustez que mudam o contrato ou o fluxo (T12.5, T13.3 e T13.1), na ordem e com as regras da DEC-085.
- O usuário consegue corrigir a leitura de um termo fora do glossário.
- As perguntas recorrentes têm resultado determinístico.
- Uma pergunta com vários fatos é respondida por várias consultas validadas, em vez de um `SELECT` forçado.

**Branch:** uma por tarefa, a partir da `APRESENTAÇÃO` depois do merge do lote 3 (PR #148):
- `feat/ai-agent-interpretacoes` (T12.5);
- `feat/ai-agent-analises-prontas` (T13.3);
- `feat/ai-agent-varias-consultas` (T13.1).

**Referências:**
- DEC-085 (proposta);
- plano geral `2026-11-05-robustez-do-agente.md` (T12.5, T13.1 e T13.3);
- spec §4 (contrato), §5 (fluxo) e §6 (validador);
- DEC-016, DEC-019, DEC-082 e DEC-084.

**Antes de começar:** a DEC-085 sai de proposta quando o backend e o portal aceitam os campos novos (`interpretations` e `steps`) e a tabela `app.ai_interpretacao_rejeitada`. A T13.3 não muda o contrato e pode começar antes desse acordo.

## Aceite (vale para as três tarefas)

1. Testes de unidade das regras novas, sem chamar o modelo real. Testes de integração no `venergy_test`.
2. Prompt novo em `prompts/v7/` (o `v6` é o da DEC-086). Com ele, o golden completo (narrado e com juiz) não regride em SQL nem em status nos itens em comum (DEC-016).
3. Itens novos do golden com `revisado_por: null`, e um conjunto novo de paráfrases e de perguntas inéditas na rodada (`make eval-variants`, `make eval-fora`).
4. Teste no portal com os 5 usuários (henrique, camila, rafael, beatriz, patricia), pela página Agente e pelo widget, com cenários novos em `frontend/e2e/agente.spec.ts`.
5. Evidência registrada na DEC-085 e progresso atualizado no plano geral.

## Tarefas

### L4.1 Interpretações corrigíveis (T12.5)

- **Domínio** (`domain/answer.py`, `domain/sql.py`):
  - `Interpretation(term, reading, alternatives)`, com até três alternativas;
  - `interpretations` no `SqlDraft` e no `AgentAnswer`, com até três itens e só nos status `answered` e `clarify`.
- **Prompt `v7/system.md`:** a seção "Palavras que não estão no glossário" passa a preencher `interpretations`, e não mais `assumptions`.
- **Caso de uso** (`application/ask.py`):
  - repassa as interpretações;
  - retira de `assumptions` o "Entendi 'X' como Y" que repetir uma interpretação;
  - toda alternativa que citar nome técnico cai (`TECHNICAL_NAME`).
- **Backend:**
  - coluna `interpretations` em `app.ai_auditoria`;
  - tabela `app.ai_interpretacao_rejeitada`;
  - `POST /ai/interpretacao-rejeitada` (dono da conversa, 403 para os outros);
  - contrato OpenAPI regerado;
  - todas as mudanças de banco por `garantir_estrutura_do_app`.
- **Portal** (`features/agente/`): "Entendi 'X' como Y" com o botão "não era isso". O botão mostra as alternativas como as opções de esclarecimento, envia a escolha e registra a rejeição.
- **Golden:** itens com termo fora do glossário e a leitura esperada em `interpretations`.
- **Testes:**
  - interpretação fora do status permitido é rejeitada;
  - interpretação duplicada some das suposições;
  - alternativa com nome técnico cai;
  - posse da rejeição (403).

### L4.2 Análises prontas (T13.3)

- **Camada semântica:** `analyses:` no `semantic/semantic_layer.yaml`, com `receita_por_que`, `comparar_periodos`, `pior_recorte` e `evolucao_mensal`. Cada análise tem um modelo de SQL, parâmetros tipados e um exemplo.
- **Domínio:**
  - `AnalysisSpec` e a montagem do SQL a partir dos parâmetros (`domain/analyses.py`), sem formatar texto do usuário dentro do SQL;
  - os valores entram por literal escapado pelo sqlglot.
- **Rascunho:** status `analysis` com `analysis_name` e `analysis_params`. O SQL montado passa pelo `SqlglotValidator` e pelo executor.
- **Erros:** parâmetro inválido ou análise desconhecida volta como erro corrigível (`AttemptFeedback`).
- **Testes:**
  - todo exemplo de análise passa no validador (como em `test_semantic_examples.py`) e executa no `venergy_test`;
  - parâmetro fora do permitido é recusado;
  - um valor com aspas não escapa do literal.

### L4.3 Várias consultas por pergunta (T13.1)

- **Domínio:**
  - `QueryPlan` com 2 a 4 passos;
  - `AnswerStep(question, sql, rows, row_count, truncated)`;
  - `steps` no `AgentAnswer`, só em `answered` e só com 2 ou mais passos.
- **Caso de uso:**
  - cada passo é validado e executado em sequência, dentro do prazo total da pergunta;
  - um passo que falha vira suposição ("não consegui obter X"), e se todos falharem o status é `failed`;
  - `sql`, `rows` e `row_count` vêm do primeiro passo.
- **Narração:** `prompts/answer/v9/` recebe os passos delimitados por nonce. A checagem de números e de unidade vale sobre a união das linhas.
- **Backend e portal:**
  - `steps` na auditoria e no contrato;
  - no portal, os passos aparecem recolhidos, cada um com o seu SQL e a sua tabela.
- **Golden:** G150 a G157 passam a ter referência por passo (`reference_sql` em lista), e `parts_matched` mede os passos.
- **Testes:**
  - um passo inválido derruba só ele;
  - o prazo vale para a soma dos passos;
  - um número de um passo é aceito na narração;
  - um número que não está em nenhum passo é recusado;
  - pergunta simples continua com um passo.

## Ordem e dependências

| Ordem | Tarefa | Depende de |
|---|---|---|
| 1 | L4.2 Análises prontas | merge do lote 3 |
| 2 | L4.1 Interpretações | acordo da DEC-085 |
| 3 | L4.3 Várias consultas | L4.2 medida e acordo da DEC-085 |

A L4.2 vem antes da L4.1 no calendário porque não muda o contrato e pode começar já. A DEC-085 mantém a ordem lógica (T12.5 primeiro) para quando o acordo sair.

## Regras

- Código do agente em inglês, sem comentários; documentação em português.
- Segurança no validador e no banco: análise pronta e passo de plano passam pelo `SqlglotValidator`, sem exceção.
- Avaliação na cota gratuita do Gemini (`--concurrency 1 --pause 6`). O modelo pago só entra para medir o tempo, com autorização.
- Commit, push e PR só com pedido explícito.
