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
| Avaliação | Golden set + métricas determinísticas logo após o primeiro `ask()` de ponta a ponta | Nenhuma mudança de prompt, modelo ou contexto entra sem medir (§1.5 e §10.3 do guia) |
| LLM as a judge | Só para clareza e fidelidade da resposta em português, com modelo diferente do gerador; entra depois dos obrigatórios | Corretude numérica é medida por execução, não por opinião de LLM |

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

## 8. Avaliação

A avaliação do agente é diferente dos testes de código da §7. Ela roda o modelo real, é paga e mais lenta, e fica fora do `pytest` padrão.

### 8.1 Golden set (`ai-agent/eval/golden.yaml`)
- Campos de cada item: `id`, `question`, `category`, `reference_sql` (nulo quando o esperado não é SQL), `expected_behavior` (os mesmos valores de `DraftStatus`: `ok | unknown | clarify | refuse`) e `follow_up_of` (diferencial).
- O conjunto começa com 40+ itens e cobre todas as categorias de §10.1 do guia: simples, junção, temporal, sinônimos, sem resposta, ambígua e manipulação. Inclui as perguntas reais das lideranças do case.
- **Toda `reference_sql` é escrita ou revisada por uma pessoa e executada no banco.** Gabarito gerado por LLM sem revisão invalida a avaliação.
- O arquivo é versionado. Todo erro encontrado em uso real vira um item novo, com o gabarito corrigido.

### 8.2 Métricas determinísticas (sem LLM)

| Métrica | Como se mede | Meta |
|---|---|---|
| Execution accuracy | Conjunto de linhas do SQL gerado = conjunto do `reference_sql`. A ordem só conta se a pergunta pedir ordenação; colunas extras são ignoradas | Acompanhar a evolução |
| Acurácia de comportamento | `status` do `SqlDraft` = `expected_behavior` | Acompanhar a evolução |
| Bloqueio de manipulação | Itens `refuse` sem nenhum SQL de escrita executado | 100% |
| Fidelidade numérica | Todo número do texto da resposta existe nas linhas | 100% |
| Operacional | SQL inválido, média de tentativas, latência p50/p95, tokens, custo | Acompanhar a evolução |

Comparar o texto do SQL não vale como métrica: duas consultas diferentes podem estar ambas certas.

### 8.3 LLM as a judge (diferencial)
- Avalia apenas clareza e fidelidade da resposta em português, a partir de (pergunta, resposta, linhas).
- Nunca decide se um número está certo; isso é papel das métricas de §8.2.
- Usa um modelo diferente do `llm_model`, para evitar autoavaliação enviesada.
- A rubrica é fixa e versionada (`prompts/judge/v1`). A saída é `JudgeVerdict(score: int 1–5, passed: bool, rationale: str)`, validada por Pydantic.
- Antes de confiar no juiz, calibrar com uma amostra pequena avaliada por uma pessoa.

### 8.4 Encaixe na arquitetura
- O pacote `venergy_agent/evaluation/` traz o runner, que consome só portas: `TextToSqlAgent`, para gerar, e `QueryExecutor`, para rodar o `reference_sql`. Assim o runner avalia qualquer implementação do agente sem conhecer o framework.
- O juiz entra como a porta `AnswerJudge.judge(question: str, answer: AgentAnswer) -> JudgeVerdict`, com adapter PydanticAI. As settings ganham `judge_model`.
- Cada execução grava um relatório (`eval/runs/<timestamp>.json`) com modelo, `prompt_version`, versão da camada semântica e métricas. Uma variável muda por vez.
- **Regra de merge:** uma mudança de prompt, modelo, few-shot, glossário ou camada semântica só entra se a execution accuracy e a acurácia de comportamento não regredirem.

## 9. Fora do escopo (próximas features, cada uma em sua branch)

Obrigatórios, nesta ordem:
1. Validador SQL (sqlglot).
2. Executores read-only SQLite/Postgres.
3. Camada semântica + glossário a partir do contrato Gold (mock).
4. Gerador PydanticAI + prompts versionados.
5. Orquestração `ask()` com loop de correção e "não sei".
6. Golden set + runner com as métricas de §8.2. Os itens do golden set podem ser escritos em paralelo desde já, porque não dependem de código.
7. Verificação numérica e `AnswerWriter`.
8. `InsightWriter`.
9. Logs estruturados.

Diferenciais, só depois dos obrigatórios:
- follow-up com memória;
- LLM as a judge (§8.3);
- avaliação automatizada a cada mudança, com tabela comparativa de experimentos.
