# Arquitetura do agente: mapa do estado atual

Resumo para orientar quem chega ao `ai-agent/` (pessoa ou sessão de IA). A fonte da verdade continua sendo a [spec](specs/2026-10-19-architecture-design.md); este arquivo só diz o que existe hoje, onde está e o que falta. Atualize-o no mesmo PR que mudar o estado.

- **Atualizado em:** 23/10/2026, com a narração (item 8) sobre a `main` depois dos PRs #29, #30, #31, #32 e #35. O que está em revisão está na spec §1.

## 1. O que o agente faz

Recebe uma pergunta em português, gera um único `SELECT` sobre as views `sem_*`, valida, executa somente leitura no Postgres e devolve um `AgentAnswer` auditável. Se não souber, responde `unknown`. Também vai narrar os insights das telas (item 9).

## 2. Camadas e arquivos

Hexagonal: `domain` ← `application` ← `infrastructure`.

| Camada | Arquivo | O que tem | Estado |
|---|---|---|---|
| domain | `question.py` | `Question` (texto limpo e limitado) | pronto |
| domain | `sql.py` | `SqlDraft` (`ok`, `unknown`, `clarify`, `refuse`), `AttemptFeedback`, `ValidatedQuery`, `QueryResult` | pronto |
| domain | `errors.py` | `ErrorKind`, `SqlRejected`, `QueryExecutionError` | pronto, com `ErrorKind.REJECTED` (item 6) |
| domain | `numbers.py` | `unsupported_numbers`: números da narrativa (lidos em pt-BR) que não estão nos valores das linhas (DEC-019) | item 8 |
| domain | `semantic.py` | `SemanticLayer`, `ViewSpec`, `ColumnSpec`, `Relation`, glossário, regras, exemplos | pronto |
| domain | `answer.py` | `AgentAnswer` com `status` e invariantes por status (DEC-020), `Insight` | pronto (PR #21; texto em branco e `row_count >= 0` no PR #29) |
| application | `ports.py` | `TextToSqlAgent`, `SemanticLayerSource`, `SqlGenerator`, `SqlValidator`, `QueryExecutor`, `AnswerWriter`, `InsightWriter` | `ask.py` (`AskUseCase`), pronto (PR #30) |
| infrastructure | `sql_validator.py` | `SqlglotValidator`: um `SELECT`, allowlist de views, funções conhecidas, `LIMIT` imposto | pronto |
| infrastructure | `postgres_executor.py` | `PostgresQueryExecutor`: `BEGIN READ ONLY`, `statement_timeout`, SQLSTATE → `ErrorKind` | pronto |
| infrastructure | `sql_generator.py`, `prompt_renderer.py`, `llm.py` | PydanticAI com `output_type=SqlDraft`; prompt em `prompts/v1/`; delimitadores com nonce; Gemini direto (padrão) ou OpenRouter | pronto |
| infrastructure | `semantic_source.py`, `views_sql.py` | `YamlSemanticLayerSource` valida `semantic/semantic_layer.yaml` contra `contracts/gold_schema.yaml` (inclusive `consumers` e `sensitive`); `views_sql` gera `semantic/views.sql` | pronto |
| infrastructure | `answer_writer.py` | `PydanticAiAnswerWriter`: narra as linhas, com o conteúdo do banco delimitado como dado; prompt em `prompts/answer/v1/` | item 8 |
| raiz | `config.py`, `bootstrap.py`, `__main__.py` | `AgentSettings` (`VENERGY_AGENT_*`); `build_agent(settings)` monta o agente; `python -m venergy_agent "pergunta"` | pronto |

## 3. Fluxo do `ask()`

```
pergunta → Question → SemanticLayer (carregada uma vez)
        → SqlGenerator → SqlDraft
            unknown | clarify | refuse → AgentAnswer sem SQL
            ok → SqlglotValidator → PostgresQueryExecutor
                 erro corrigível → AttemptFeedback → nova tentativa (até 3)
                 erro do banco não classificado → failed
        → AnswerWriter (narrativa) → números conferidos com as linhas (DEC-019)
            falhou → texto determinístico (com os valores, se o resultado for pequeno)
        → AgentAnswer
```

Detalhes, confiança e logs: spec §5.1. O backend monta o agente uma vez por processo com `build_agent(AgentSettings())`.

Em branch: `InsightWriter` (`feat/ai-agent-insight`, prompt em `prompts/insight/v1/`, item 9). O golden set está em `eval/golden_set.yaml` (66 itens, alinhado à camada v0.2, rascunho até a revisão humana).

## 4. Camada semântica hoje

`semantic/semantic_layer.yaml` (versão 0.2.0 do arquivo) tem seis views:

| View | Tabela da Gold | Responde sobre |
|---|---|---|
| `sem_uc` | `gold_dim_uc` | cadastro, classe e classe do cadastro, alimentador, GD |
| `sem_faturamento_mensal` | `gold_fato_faturamento_mensal` | energia, receita (faturada, de energia, tributos, arrecadada), tarifa e bandeira por UC |
| `sem_continuidade_alimentador_mensal` | `gold_continuidade_alimentador_mensal` | DEC, FEC e interrupções por alimentador |
| `sem_kpis_mensais` | `gold_kpis_mensais` | totais da empresa por mês, inclusive chamados e satisfação |
| `sem_kpis_segmento_mensal` | `gold_kpis_segmento_mensal` | componentes somáveis por município, bairro, classe e GD; DEC, FEC e satisfação do recorte saem da soma dos componentes |
| `sem_receita_decomposicao` | `gold_receita_decomposicao` | efeitos de preço (tarifa e bandeira), volume e mix entre dois períodos `AAAA-MM/AAAA-MM` |

Relações: `sem_faturamento_mensal` ↔ `sem_uc` por `cod_uc`, e `sem_uc` ↔ `sem_continuidade_alimentador_mensal` por `cod_alimentador`. As views de KPIs e a decomposição não têm relação: respondem sozinhas (DEC-018).

Testes que protegem a camada: validação contra o contrato (`test_semantic_source.py`), toda SQL de exemplo passa pelo validador (`test_semantic_examples.py`), deriva do `views.sql` (`test_views_sql.py`) e consultas reais pelo validador e pelo executor (`tests/integration/test_semantic_views.py`).

## 5. Cobertura da Gold (contrato v0.2.0)

Regras do contrato para o agente (`conventions.agent`, DEC-022), conferidas no código: só tabelas com `agente` em `consumers`, só colunas `confirmada` ou `proposta` sem `sensitive: true`. "Receita" sem qualificador é `receita_faturada`.

| Tabela | Agente em `consumers` | Na camada semântica | Observação |
|---|---|---|---|
| `gold_dim_uc` | sim | `sem_uc` | `titular_mascarado` e `documento_mascarado` são `sensitive`: nunca entram |
| `gold_fato_faturamento_mensal` | sim | `sem_faturamento_mensal` | colunas de pagamento (`status_pagamento`, `dias_em_atraso`) e de leitura (`kwh_leitura`, `origem_kwh`) ainda não foram escolhidas |
| `gold_continuidade_alimentador_mensal` | sim | `sem_continuidade_alimentador_mensal` | |
| `gold_kpis_mensais` | sim | `sem_kpis_mensais` | |
| `gold_kpis_segmento_mensal` | sim | `sem_kpis_segmento_mensal` | |
| `gold_receita_decomposicao` | sim | `sem_receita_decomposicao` | método do efeito bandeira e `possui_gd` entre períodos ainda em aberto no contrato |
| `gold_reconciliacao_faturamento` | sim | não | candidata para perguntas sobre faturas fora do cadastro e correções de kWh |
| `gold_interrupcoes_uc`, `gold_atendimentos_uc`, `gold_medidor_uc` | sim | não | sem colunas nem chave no contrato: bloqueadas |
| `gold_fila_suspeitas` | **não** | não | fora do agente por decisão de produto (DEC-022) |

O banco local só tem a amostra sintética do backend (`venergy_api.amostra`). A Gold real ainda não foi entregue: os nomes e regras vêm do contrato, os números do golden set só se fixam com ela.

## 6. Lacunas conhecidas

- O YAML não registra a versão do contrato (`conventions.agent.contract_version`).
- D7 continua aberto: a carga apaga as tabelas da Gold sem `CASCADE` e falha se houver view `sem_*`. Procedimento manual no `README.md`.
- D1 continua aberto: as views ficam no schema `gold`, onde o `venergy_agent` lê todas as tabelas.
- O golden set (PR #32) ainda não tem revisão humana: `revisado_por` é nulo em todos os itens, e o gabarito só se fixa com a Gold real.
- Recortes de receita: a tela (`GET /receita/comparacao`, DEC-021) soma a fato com o cadastro atual da UC, e o agente soma `sem_kpis_segmento_mensal`. Os números só divergem se uma UC mudou de recorte; alinhar quando o backend migrar para a tabela de segmentos.

## 7. Onde está cada coisa

- Contrato com o backend e decisões de domínio: spec §4 e §5, DEC-020.
- Regras de segurança do SQL: spec §6 e `ai-agent/CLAUDE.md`.
- Pedidos para outras áreas (D1 a D9): spec §10.
- Ordem das próximas features: spec §11.
- Contrato da Gold: `contracts/gold_schema.yaml`; dicionário em `docs/dicionario-de-dados.md`.
- Planos executados e em curso: `docs/plans/`.
