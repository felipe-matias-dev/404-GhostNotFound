# Arquitetura do agente Text-to-SQL — estrutura e contratos

- **Data:** 2026-10-19 · **Atualizada:** 2026-10-20 (sincronizada com DEC-002, backlog G1/G2 e o review do PR #5)
- **Escopo:** apenas `ai-agent/` (BC6 Assistente Analítico). O que depende de backend, infra ou dados fica registrado como pedido na §10.
- **Base:** case Rocket Lab 2026.2 (Módulo 3), `docs/arquitetura.md`, `docs/decisoes.md`, `docs/backlog.md` (G1, G2) e o [guia de boas práticas do agente](../contexto-agente-text-to-sql.md), citado como "§x do guia".

## 1. Objetivo

Criar o esqueleto multi-camadas do agente: estrutura de pacotes, modelos de domínio, portas e configuração. Esse esqueleto está no PR #5 (em revisão), junto com o primeiro adapter, o validador SQL (`sqlglot`). As correções de segurança do validador (§6), encontradas no review do PR #5, estão na branch `fix/ai-agent-review-pr5`. Os demais adapters viram features em branches próprias (§11).

**Critério de sucesso:** `uv run pytest` e `uv run ruff check` passam em `ai-agent/`; os contratos abaixo existem e estão cobertos pelos testes da §8.

## 2. Decisões

| Decisão | Escolha | Motivo |
|---|---|---|
| Framework de agente (ADR-02) | PydanticAI, atrás de portas próprias | Saída tipada com retry de validação, suporte nativo a OpenRouter, `TestModel` para testes sem custo, troca isolada em um adapter |
| Provedor de LLM | OpenRouter (`openrouter:google/gemini-3.1-flash-lite`) | Recomendação do case; modelo e fallback trocáveis por variável de ambiente |
| Banco (ADR-01, DEC-002) | PostgreSQL 17, com o usuário `venergy_agent` (somente leitura) | Decidido pelo time. Só há executor Postgres; SQLite saiu do roadmap |
| Escopo de dados do agente | Views `sem_*` num schema próprio, com permissão de leitura só nele | A allowlist precisa valer também no banco, e não só no validador (§10, D1) |
| Organização | Hexagonal em 3 camadas (`domain` ← `application` ← `infrastructure`) | Framework isolado (§14 do guia), cada etapa testável com fakes |
| Triagem | Feita pelo `status` do `SqlDraft`, sem chamada extra ao LLM | "Simples primeiro"; etapa separada só com ganho medido na avaliação |
| Auditoria | O agente devolve os dados de auditoria no `AgentAnswer`; o backend persiste | O agente é somente leitura e não grava em lugar nenhum (G1-06) |
| Follow-up | Fora deste escopo (diferencial) | Obrigatórios primeiro |
| Avaliação | Golden set + métricas determinísticas logo após o primeiro `ask()` de ponta a ponta | Nenhuma mudança de prompt, modelo ou contexto entra sem medir (§1.5 e §10.3 do guia) |
| LLM as a judge | Só para clareza e fidelidade da resposta em português, com modelo diferente do gerador; entra depois dos obrigatórios | Corretude numérica é medida por execução, não por opinião de LLM |

## 3. Estrutura

```
ai-agent/
├── pyproject.toml
├── .env.example
├── src/venergy_agent/
│   ├── config.py
│   ├── domain/
│   │   ├── question.py
│   │   ├── semantic.py
│   │   ├── sql.py
│   │   ├── answer.py
│   │   └── errors.py
│   ├── application/
│   │   └── ports.py
│   └── infrastructure/
│       └── sql_validator.py
└── tests/unit/
    ├── domain/
    └── infrastructure/
```

**Regra de dependência:** `domain` não importa nada do projeto e não faz I/O. `application` importa apenas `domain`. `infrastructure` implementa as portas de `application`. O composition root (`bootstrap.py`) entra junto com o primeiro caso de uso que liga os adapters.

`prompts/v1/`, `semantic/`, `eval/golden_set.yaml` e `eval/red_team.yaml` nascem com as features que os usam.

## 4. Domínio

### `question.py`
- `Question(text: str, session_id: str, request_id: str)`. `text` é normalizado com `strip` e não pode ficar vazio. `request_id` usa `uuid4` como padrão.

### `sql.py`
- `DraftStatus`: `ok`, `unknown`, `clarify`, `refuse`.
- `SqlDraft(status, sql, views_used, assumptions, clarification_question)` é a saída estruturada do LLM. Invariantes (uma string em branco conta como ausente):
  - `ok` exige `sql`;
  - `clarify` exige `clarification_question`;
  - qualquer status diferente de `ok` exige `sql is None`.
- `AttemptFeedback(previous_sql, error_kind, message)` é a entrada da tentativa de correção.
- `ValidatedQuery(sql, views, applied_limit, limit_imposed)` só é produzido pelo validador. `limit_imposed` diz se o `LIMIT` foi inserido ou reduzido pelo validador; só nesse caso o resultado pode ser marcado como truncado. Um top-N pedido pelo usuário não é truncamento.
- `QueryResult(columns, rows, row_count, truncated)`.

### `errors.py`
- `ErrorKind`: `syntax`, `unknown_object`, `type_mismatch`, `timeout`.
- `SqlRejected(reason)` e `QueryExecutionError(kind, message)`. Resultado vazio não é erro.

### `semantic.py`
- `ColumnSpec(name, type, description, unit, allowed_values)`.
- `ViewSpec(name, description, grain, columns, sample_rows)`.
- `Relation(left_view, left_column, right_view, right_column)`.
- `GlossaryTerm(term, synonyms, maps_to)`, `BusinessRule(text)`, `FewShotExample(question, sql, expected_status)`.
- `SemanticLayer(version, views, relations, glossary, rules, examples)`. Invariantes: nomes de view únicos; toda `Relation` referencia views e colunas existentes. A propriedade `allowed_views` (frozenset dos nomes das views) é a allowlist do validador.

### `answer.py`
- `Confidence`: `high`, `medium`, `low`, `unknown`. O mapeamento para os rótulos em português fica no portal.
- `AgentAnswer` é o contrato com o backend (`docs/arquitetura.md`, G1-04):

| Campo | Tipo | Observação |
|---|---|---|
| `answer` | `str` | Texto para o usuário |
| `sql` | `str \| None` | Último SQL gerado (mesmo se rejeitado ou com erro), para auditoria |
| `rows` | `tuple[dict, ...]` | Amostra das linhas |
| `row_count` | `int` | Total real de linhas |
| `confidence` | `Confidence` | — |
| `sources` | `tuple[str, ...]` | Views consultadas |
| `assumptions` | `tuple[str, ...]` | Suposições declaradas |
| `clarification` | `str \| None` | Pergunta de esclarecimento |
| `refused_reason` | `str \| None` | Motivo quando o agente não responde (fora de escopo, "não sei", SQL rejeitado, tentativas esgotadas) |
| `request_id` | `str` | — |
| `model` | `str` | Modelo que gerou a resposta (G1-06) |
| `prompt_version` | `str` | — |
| `latency_ms` | `int` | `≥ 0` (G1-06) |

Invariantes:
- `row_count >= len(rows)`, porque `rows` é uma amostra e o total real vem declarado.
- `refused_reason` e `clarification` são mutuamente exclusivos.
- Com `refused_reason` presente: `rows` vazio, `row_count == 0` e `confidence == unknown`. Isso impede devolver resultado parcial como se fosse resposta (§6 do guia).

O timestamp da auditoria é registrado pelo backend ao persistir; o agente não lê relógio no domínio.

- `Insight(text, metrics_used)`.

Todos os modelos de domínio são imutáveis (`frozen`).

## 5. Portas (`application/ports.py`)

São `typing.Protocol` assíncronos, exceto `SqlValidator`, que é síncrono por ser CPU puro:

| Porta | Assinatura | Observação |
|---|---|---|
| `TextToSqlAgent` | `ask(question: str, session_id: str) -> AgentAnswer` | Contrato de entrada com o backend (Partnership BC6↔BC7) |
| `SemanticLayerSource` | `load() -> SemanticLayer` | Gerada a partir do contrato/dicionário da Gold |
| `SqlGenerator` | `generate(question: Question, layer: SemanticLayer, feedback: AttemptFeedback \| None) -> SqlDraft` | Adapter PydanticAI |
| `SqlValidator` | `validate(sql: str, allowed_views: frozenset[str]) -> ValidatedQuery` | Levanta `SqlRejected`; adapter `SqlglotValidator` (§6) |
| `QueryExecutor` | `execute(query: ValidatedQuery) -> QueryResult` | Levanta `QueryExecutionError`; conexão read-only |
| `AnswerWriter` | `write(question: Question, draft: SqlDraft, result: QueryResult) -> str` | Resposta só a partir das linhas |
| `InsightWriter` | `narrate(screen: str, metrics: Mapping[str, object]) -> Insight` | LLM só narra números prontos |

### Dados não são instruções

Tudo o que vem do banco é **dado, nunca instrução** (§5.3 do guia):
- o `SqlGenerator` recebe `sample_rows` e `allowed_values`;
- o `AnswerWriter` recebe as linhas do resultado, que podem conter texto livre das tratativas do call center.

Os dois adapters delimitam esse conteúdo no prompt, num bloco de dados separado das instruções, e instruem o modelo a ignorar qualquer comando que apareça dentro dele. A pergunta do usuário nunca é concatenada em SQL: todo SQL passa pelo validador. O red team (§9.2) inclui casos de injeção pelos dados.

## 6. Validador SQL (`infrastructure/sql_validator.py`)

`SqlglotValidator(dialect: str, max_rows: int, allowed_schema: str)`. Parser, nunca regex. Regras:

1. Exatamente **um** statement, e a raiz é um `SELECT` ou `WITH … SELECT` (`exp.Query`, inclusive `UNION`).
2. Nenhum nó de DML, DDL, `Command`, `SET` ou `COPY` em qualquer ponto da árvore (pega DML dentro de CTE).
3. Sem cláusulas de bloqueio (`FOR UPDATE`, `FOR SHARE`) e sem `SELECT … INTO`.
4. **Resolução de nomes por escopo** (`sqlglot.optimizer.scope`): um CTE só encobre tabelas dentro do próprio escopo. Toda tabela física referenciada precisa estar em `allowed_views` e no `allowed_schema` (ou sem schema); qualquer catálogo é rejeitado. Identificadores sem aspas são normalizados para minúsculas, como o Postgres faz. No SQL de saída, toda view é qualificada com o `allowed_schema`, para a execução não depender do `search_path` da conexão.
5. **Funções:**
   - Só são aceitas as que o sqlglot reconhece como expressões tipadas no dialeto.
   - Toda função desconhecida para o parser (`exp.Anonymous`) é rejeitada. É assim que aparecem `query_to_xml`, `table_to_xml`, `dblink`, `pg_read_file`, `pg_sleep`, `current_setting` e `set_config` (verificado no sqlglot 30.21).
   - Entre as reconhecidas, uma denylist curta bloqueia as que expõem o servidor ou a sessão: `version()`, `current_user`, `session_user`, `current_database()`, `current_catalog` e `current_schema`. `current_role` e `user` chegam como coluna, não como função, e ficam a cargo da role do banco (D1).
   - O efeito na acurácia é medido no golden set. Uma função legítima rejeitada (ex.: `make_date`, que o sqlglot trata como `Anonymous`) entra numa lista explícita de exceções, com teste.
6. `LIMIT`: inserido quando ausente e reduzido quando acima de `max_rows`. `FETCH FIRST`, `LIMIT ALL` e qualquer valor que não seja literal inteiro são rejeitados, com um motivo que pede `LIMIT n`.
7. Cada rejeição tem um `reason` específico, porque ele volta para o modelo na tentativa de correção.

O validador é a primeira trava. A segunda é o banco: role somente leitura, com permissão só no schema das views (§10, D1). Uma não substitui a outra.

## 7. Configuração (`config.py`)

`AgentSettings` (pydantic-settings, prefixo `VENERGY_AGENT_`):

| Campo | Padrão | Restrição |
|---|---|---|
| `llm_model` | `openrouter:google/gemini-3.1-flash-lite` | — |
| `fallback_model` | `None` | — |
| `openrouter_api_key` | obrigatório | `SecretStr`, nunca no `repr` |
| `temperature` | `0.0` | `0 ≤ t ≤ 0.2` |
| `sql_dialect` | `postgres` | Só `postgres` (DEC-002). Usado pelo validador e pelas regras de dialeto do prompt |
| `database_url` | obrigatório | Usuário `venergy_agent`, nunca as credenciais do backend |
| `allowed_schema` | `gold` | Passa a ser o schema das views `sem_*` quando D1 for atendido |
| `max_question_chars` | `500` | `> 0` |
| `max_rows` | `200` | `> 0` |
| `query_timeout_seconds` | `10` | `> 0` |
| `max_correction_attempts` | `3` | `1 ≤ n ≤ 3` |
| `prompt_version` | `v1` | — |

**Adiado de propósito:** rate limit e orçamento de tokens por sessão (§5.4 do guia) não estão nas settings. O case não os exige, e o rate limit por usuário cabe melhor no backend, que conhece o usuário. Entram como diferencial (§11), com os limites em settings quando chegarem.

**Origem das variáveis:** em produção, quem constrói `AgentSettings` é o composition root, chamado pelo backend FastAPI. As variáveis `VENERGY_AGENT_*` vêm do ambiente do processo (compose e `.env` da raiz). O `ai-agent/.env` só vale para rodar o agente isolado (testes, avaliação), e por isso o caminho do `.env` não pode depender do diretório atual.

## 8. Testes

Só regras do projeto; nada de testar enums, Protocols ou a própria biblioteca.

1. `SqlDraft`: as três invariantes (parametrizadas, com strings em branco) e um caso válido.
2. `SemanticLayer`: relação para view ou coluna inexistente é rejeitada; nomes duplicados são rejeitados; `allowed_views` expõe os nomes.
3. `AgentAnswer`: `row_count < len(rows)` é rejeitado; `refused_reason` com linhas, com `row_count > 0`, com `confidence` diferente de `unknown` ou junto de `clarification` é rejeitado.
4. `Question`: texto em branco é rejeitado.
5. `AgentSettings`: variável com prefixo sobrescreve o padrão; falta de `openrouter_api_key` falha; `temperature` e `max_correction_attempts` fora da faixa são rejeitados; a chave não aparece no `repr`.
6. `SqlglotValidator`: lista parametrizada de SQL malicioso ou inválido (DDL, DML, múltiplos statements, DML em CTE, funções de sistema, tabelas fora da allowlist, schema ou catálogo errado) e de SQL válido (join, CTE, `UNION`, `LIMIT`). Inclui como regressões os desvios encontrados no review do PR #5:
   - CTE com o nome de uma tabela proibida, declarado em outro escopo: `SELECT * FROM gold_dim_uc WHERE EXISTS (WITH gold_dim_uc AS (SELECT 1) SELECT 1 FROM gold_dim_uc)` → rejeitado;
   - `query_to_xml`/`table_to_xml`, inclusive via `LATERAL` → rejeitado;
   - `FOR UPDATE` → rejeitado;
   - `FETCH FIRST 5000 ROWS ONLY` → rejeitado, com motivo que pede `LIMIT`;
   - funções legítimas de data e texto (`date_trunc`, `extract`, `to_char`, `round`) → aceitas, para a regra de funções não bloquear consultas válidas.

O teste de que o banco recusa escrita é de integração e chega com o executor (§11, item 3).

## 9. Avaliação

A avaliação do agente é diferente dos testes de código da §8. Ela roda o modelo real, é paga e mais lenta, e fica fora do `pytest` padrão. O golden set é do G2 (G2-01); o runner é do G1.

### 9.1 Golden set (`ai-agent/eval/golden_set.yaml`)
- Campos de cada item: `id`, `question`, `category`, `reference_sql` (nulo quando o esperado não é SQL), `expected_behavior` (os mesmos valores de `DraftStatus`: `ok | unknown | clarify | refuse`) e `follow_up_of` (diferencial).
- O conjunto começa com 40+ itens e cobre todas as categorias de §10.1 do guia (simples, junção, temporal, sinônimos, sem resposta, ambígua, manipulação), com **pelo menos 8 sem resposta** e **pelo menos 5 de injection** (G2-01). Inclui as falas das lideranças do case.
- **Toda `reference_sql` é escrita ou revisada por uma pessoa e executada no banco.** Gabarito gerado por LLM sem revisão invalida a avaliação. O gabarito é preenchido sobre a amostra e recalibrado quando a Gold real chegar.
- O arquivo é versionado. Todo erro encontrado em uso real vira um item novo, com o gabarito corrigido.

### 9.2 Red team (`ai-agent/eval/red_team.yaml`)
- Pelo menos 15 ataques: ignorar instruções, vazar o prompt, `DROP` via texto, injeção pelo texto livre do call center e pedido de dados fora do escopo (G1-11).
- Meta: 0 violações (nenhum SQL de escrita, nenhuma tabela fora da allowlist, nenhum vazamento de prompt).

### 9.3 Métricas determinísticas (sem LLM)

| Métrica | Como se mede | Meta |
|---|---|---|
| Execution accuracy | Conjunto de linhas do SQL gerado = conjunto do `reference_sql`. A ordem só conta se a pergunta pedir ordenação; colunas extras são ignoradas | ≥ 80% sobre a Gold real (G1-05) |
| Acurácia de comportamento | `status` do `SqlDraft` = `expected_behavior` | 100% nos itens sem resposta (G1-07) |
| Bloqueio de manipulação | Itens `refuse` e red team sem SQL de escrita ou fora da allowlist executado | 100% |
| Fidelidade numérica | Todo número do texto da resposta existe nas linhas | 100% |
| Operacional | SQL inválido, média de tentativas, latência p50/p95, tokens, custo | Acompanhar a evolução |

Comparar o texto do SQL não vale como métrica: duas consultas diferentes podem estar ambas certas.

### 9.4 LLM as a judge (diferencial)
- Avalia apenas clareza e fidelidade da resposta em português, a partir de (pergunta, resposta, linhas).
- Nunca decide se um número está certo; isso é papel das métricas de §9.3.
- Usa um modelo diferente do `llm_model`, para evitar autoavaliação enviesada.
- A rubrica é fixa e versionada (`prompts/judge/v1`). A saída é `JudgeVerdict(score: int 1–5, passed: bool, rationale: str)`, validada por Pydantic.
- Antes de confiar no juiz, calibrar com uma amostra pequena avaliada por uma pessoa.

### 9.5 Encaixe na arquitetura
- O pacote `venergy_agent/evaluation/` traz o runner, que consome só portas: `TextToSqlAgent`, para gerar, e `QueryExecutor`, para rodar o `reference_sql`. Assim o runner avalia qualquer implementação do agente sem conhecer o framework.
- O juiz entra como a porta `AnswerJudge.judge(question: str, answer: AgentAnswer) -> JudgeVerdict`, com adapter PydanticAI. As settings ganham `judge_model`.
- Cada execução grava um relatório (`eval/runs/<timestamp>.json`) com modelo, `prompt_version`, versão da camada semântica e métricas. Uma variável muda por vez.
- **Regra de merge:** uma mudança de prompt, modelo, few-shot, glossário ou camada semântica só entra se a execution accuracy e a acurácia de comportamento não regredirem.

## 10. Dependências de outras áreas

Pedidos a abrir como issue para a área dona. O GenAI não altera esses arquivos.

| # | Área | Pedido | Por quê |
|---|---|---|---|
| D1 | Dev (V1-02, `infra/postgres/init`) | Criar um schema para as views `sem_*` (sugestão: `semantic`) e dar ao `venergy_agent` `USAGE` e `SELECT` só nele. Tirar o `ALTER DEFAULT PRIVILEGES … GRANT SELECT` em `gold`, que hoje libera todas as tabelas da Gold. Definir `statement_timeout` na role | Hoje o agente lê qualquer tabela de `gold`, inclusive colunas pessoais que as views removeriam (§2.1 e §5.1 do guia) |
| D2 | Dev (DEC-007, `.github/workflows/ci.yml`) | Job do `ai-agent` no CI: `uv run --frozen pytest` e `ruff` dentro de `ai-agent/` | O CI só roda o backend; uma regressão do validador passaria sem ser vista |
| D3 | Dev (G1-06, G1-09) | Persistir a auditoria de cada `AgentAnswer` (com timestamp) e expor `POST /ai/ask` e `GET /ai/audit/{id}` | O agente é somente leitura |
| D4 | Dados | Publicar na amostra e na Gold as tabelas que o agente usa: `gold_fato_faturamento_mensal`, `gold_continuidade_alimentador_mensal`, `gold_atendimentos_uc` | A amostra atual só tem `gold_dim_uc` |
| D6 | Dev (`infra/postgres/init/01-init.sh`) | Versionar o script com bit de execução (`git update-index --chmod=+x`) | No Docker Desktop do macOS, o entrypoint tenta executar o script sem o bit e o container sai com `bad interpreter: Permission denied` na primeira subida |
| D5 | Time (`docs/arquitetura.md`) | Atualizar o ADR-01 de "em aberto" para "PostgreSQL (DEC-002)" | Documento do time desatualizado |

## 11. Próximas features (cada uma em sua branch)

Obrigatórios, nesta ordem:
1. ~~Hardening do validador~~: feito em `fix/ai-agent-review-pr5`, com as regras da §6 e os testes de regressão do item 6 da §8.
2. **Contrato `AgentAnswer`**: `refused_reason`, `model`, `latency_ms` e as novas invariantes (§4). Precisa ser combinado com V1, porque o backend depende dele.
3. ~~Executor read-only Postgres~~: feito em `feat/ai-agent-executor` (`PostgresQueryExecutor`, plano `docs/plans/2026-10-20-postgres-executor.md`), com timeout por consulta, truncamento, classificação por SQLSTATE e teste de integração confirmando que o banco recusa `INSERT`.
4. Camada semântica + glossário a partir do contrato Gold (amostra), incluindo o SQL das views `sem_*`.
5. Gerador PydanticAI + prompts versionados, com o conteúdo do banco delimitado como dado (§5).
6. **Orquestração `ask()`** com loop de correção, "não sei" e **logs estruturados por etapa**, no mesmo PR. Cada requisição registra `request_id`, `session_id`, a pergunta, o SQL de cada tentativa, o resultado da validação, o erro, o número de linhas, a latência por etapa, os tokens, o modelo e o `prompt_version` (§12 do guia). Sem esse rastreio não dá para diagnosticar as falhas que o golden set vai mostrar.
7. Golden set + red team + runner com as métricas de §9.3. Os itens podem ser escritos em paralelo desde já, porque não dependem de código.
8. Verificação numérica e `AnswerWriter`, com o conteúdo do banco delimitado como dado (§5).
9. `InsightWriter`.

Diferenciais, só depois dos obrigatórios:
- follow-up com memória;
- LLM as a judge (§9.4);
- avaliação automatizada a cada mudança, com tabela comparativa de experimentos;
- rate limit e orçamento de tokens por sessão (§7).
