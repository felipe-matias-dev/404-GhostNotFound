# Arquitetura do agente Text-to-SQL — estrutura e contratos

- **Data:** 2026-10-19
- **Escopo:** apenas `ai-agent/` (BC6 Assistente Analítico). Nada de backend, frontend ou pipeline de dados.
- **Base:** case Rocket Lab 2026.2 (Módulo 3), `PLANEJAMENTO_CONTRATOS.md` (§1.3, ADR-01/02/03) e o guia de boas práticas do agente.

## 1. Objetivo

Criar o esqueleto multi-camadas do agente: estrutura de pacotes, modelos de domínio, portas e configuração. Nenhum adapter (LLM, validador, banco, camada semântica) é implementado aqui: cada um vira uma feature em branch própria.

**Critério de sucesso:** `uv run pytest` e `uv run ruff check` passam em `ai-agent/`, e os contratos abaixo existem e estão cobertos pelos testes de invariantes da §7.

## 2. Decisões

| Decisão | Escolha | Motivo |
|---|---|---|
| Framework de agente (ADR-02) | PydanticAI, atrás de portas próprias | Saída tipada com retry de validação, suporte nativo a OpenRouter, `TestModel` para testes sem custo, troca isolada em um adapter |
| Provedor de LLM | OpenRouter (`openrouter:google/gemini-3.1-flash-lite`) | Recomendação do case; modelo e fallback trocáveis por variável de ambiente |
| Banco (ADR-01 em aberto) | Porta `QueryExecutor` com adapters SQLite e PostgreSQL (features futuras) | Dialeto configurável; não bloqueia a decisão do time |
| Organização | Hexagonal em 3 camadas (`domain` ← `application` ← `infrastructure`) | Framework isolado (§14 do guia), cada etapa testável com fakes |
| Triagem | Feita pelo `status` do `SqlDraft`, sem chamada extra ao LLM | "Simples primeiro"; etapa separada só com ganho medido na avaliação |
| Follow-up | Fora deste escopo (diferencial) | Obrigatórios primeiro |

## 3. Estrutura

```
ai-agent/
├── pyproject.toml
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
└── tests/unit/
```

**Regra de dependência:** `domain` não importa nada do projeto e não faz I/O. `application` importa apenas `domain`. `infrastructure` implementa as portas de `application`. O composition root (`bootstrap.py`) entra junto com o primeiro adapter.

`prompts/v1/`, `semantic/glossary.yaml` e `eval/golden.yaml` nascem com as features que os usam.

## 4. Domínio

### `question.py`
- `Question(text: str, session_id: str, request_id: str)`. `text` é normalizado com `strip` e não pode ficar vazio. `request_id` usa `uuid4` como padrão.

### `sql.py`
- `DraftStatus`: `ok`, `unknown`, `clarify`, `refuse`.
- `SqlDraft(status, sql, views_used, assumptions, clarification_question)` é a saída estruturada do LLM. Invariantes:
  - `ok` exige `sql`;
  - `clarify` exige `clarification_question`;
  - qualquer status diferente de `ok` exige `sql is None`.
- `AttemptFeedback(previous_sql, error_kind, message)` é a entrada da tentativa de correção.
- `ValidatedQuery(sql, views, applied_limit)` só é produzido pelo validador.
- `QueryResult(columns, rows, row_count, truncated)`.

### `errors.py`
- `ErrorKind`: `syntax`, `unknown_object`, `type_mismatch`, `timeout`.
- `SqlRejected(reason)` e `QueryExecutionError(kind, message)`. Resultado vazio não é erro.

### `semantic.py`
- `ColumnSpec(name, type, description, unit, allowed_values)`.
- `ViewSpec(name, description, grain, columns, sample_rows)`.
- `Relation(left_view, left_column, right_view, right_column)`.
- `GlossaryTerm(term, synonyms, maps_to)`, `BusinessRule(text)`, `FewShotExample(question, sql, expected_status)`.
- `SemanticLayer(version, views, relations, glossary, rules, examples)`. Invariante: toda `Relation` referencia views e colunas existentes. A propriedade `allowed_views` (frozenset dos nomes das views) é a allowlist do validador.

### `answer.py`
- `Confidence`: `high`, `medium`, `low`, `unknown`. O mapeamento para os rótulos em português fica no portal.
- `AgentAnswer(answer, sql, rows, row_count, confidence, sources, assumptions, clarification, request_id, prompt_version)`. Invariante: `row_count >= len(rows)`, porque `rows` é uma amostra e o total real vem declarado.
- `Insight(text, metrics_used)`.

Todos os modelos de domínio são imutáveis (`frozen`).

## 5. Portas (`application/ports.py`)

São `typing.Protocol` assíncronos:

| Porta | Assinatura | Observação |
|---|---|---|
| `TextToSqlAgent` | `ask(question: str, session_id: str) -> AgentAnswer` | Contrato de entrada com o backend (Partnership BC6↔BC7) |
| `SemanticLayerSource` | `load() -> SemanticLayer` | Gerada a partir do contrato/dicionário da Gold |
| `SqlGenerator` | `generate(question: Question, layer: SemanticLayer, feedback: AttemptFeedback \| None) -> SqlDraft` | Adapter PydanticAI |
| `SqlValidator` | `validate(sql: str, allowed_views: frozenset[str]) -> ValidatedQuery` | Levanta `SqlRejected`; adapter sqlglot |
| `QueryExecutor` | `execute(query: ValidatedQuery) -> QueryResult` | Levanta `QueryExecutionError`; conexão read-only |
| `AnswerWriter` | `write(question: Question, draft: SqlDraft, result: QueryResult) -> str` | Resposta só a partir das linhas |
| `InsightWriter` | `narrate(screen: str, metrics: Mapping[str, object]) -> Insight` | LLM só narra números prontos |

`SqlValidator` é síncrono, porque é CPU puro.

## 6. Configuração (`config.py`)

`AgentSettings` (pydantic-settings, prefixo `VENERGY_AGENT_`, lê `.env`):

| Campo | Padrão | Restrição |
|---|---|---|
| `llm_model` | `openrouter:google/gemini-3.1-flash-lite` | — |
| `fallback_model` | `None` | — |
| `openrouter_api_key` | obrigatório | `SecretStr` |
| `temperature` | `0.0` | `0 ≤ t ≤ 0.2` |
| `sql_dialect` | `sqlite` | `sqlite` \| `postgres` |
| `database_url` | obrigatório | — |
| `max_question_chars` | `500` | `> 0` |
| `max_rows` | `200` | `> 0` |
| `query_timeout_seconds` | `10` | `> 0` |
| `max_correction_attempts` | `3` | `1 ≤ n ≤ 3` |
| `prompt_version` | `v1` | — |

## 7. Testes

Só regras do projeto; nada de testar enums, Protocols ou a própria biblioteca.

1. `SqlDraft`: as três invariantes (parametrizadas) e um caso válido.
2. `SemanticLayer`: relação para view ou coluna inexistente é rejeitada; `allowed_views` expõe os nomes.
3. `AgentAnswer`: `row_count < len(rows)` é rejeitado.
4. `Question`: texto em branco é rejeitado.
5. `AgentSettings`: variável com prefixo sobrescreve o padrão; falta de `openrouter_api_key` falha; `temperature` e `max_correction_attempts` fora da faixa são rejeitados.

## 8. Fora do escopo (próximas features, cada uma em sua branch)

Na ordem dos obrigatórios:
1. Validador SQL (sqlglot).
2. Executores read-only SQLite/Postgres.
3. Camada semântica + glossário a partir do contrato Gold (mock).
4. Gerador PydanticAI + prompts versionados.
5. Orquestração `ask()` com loop de correção e "não sei".
6. Verificação numérica e `AnswerWriter`.
7. `InsightWriter`.
8. Logs estruturados.
9. Golden set.

Diferenciais (follow-up, avaliação automatizada) só depois.
