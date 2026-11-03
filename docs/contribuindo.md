# Contribuindo

## Estrutura do repositório

| Pasta | Conteúdo |
|---|---|
| [`data-engineering/`](../data-engineering/) | Notebooks Bronze → Silver → Gold e o `.yaml` do Workflow |
| [`backend/`](../backend/) | API do portal (FastAPI), carga da Gold e gerador da amostra sintética |
| [`frontend/`](../frontend/) | Aplicação web (React + TypeScript + Vite) |
| [`ai-agent/`](../ai-agent/) | Agente Text-to-SQL, camada semântica, insights de IA e suíte de avaliação |
| [`contracts/`](../contracts/) | Contrato da Gold (`gold_schema.yaml`) e da API (`openapi.json`) |
| [`infra/`](../infra/) | Script de criação dos schemas `gold` e `app` e do usuário somente leitura do agente |
| [`docs/`](README.md) | Documentação do projeto |

Cada módulo tem o próprio README com o desenvolvimento fora do Docker:
[backend](../backend/README.md), [frontend](../frontend/README.md),
[agente](../ai-agent/README.md) e [engenharia de dados](../data-engineering/README.md).

## Regras do time

- **O dataset nunca vai para o repositório.** Brutos e CSVs da Gold ficam em `data/`, fora do
  Git. Nada de `*.csv`, `*.xlsx` ou `*.zip` versionado.
- **Decisões vão para [`decisoes.md`](decisoes.md)** no formato `DEC-NNN`, com data, motivo,
  alternativa descartada e autor. Toda suposição feita onde o case não é explícito entra lá.
- **Commits** no padrão Conventional Commits (`feat:`, `fix:`, `docs:`, `chore:`, `test:`,
  `refactor:`). Uma branch por tarefa e PR revisado por outra pessoa antes da `main`.
- **Cálculos de negócio** (DEC/FEC, efeito preço × volume) ficam na Gold e no backend. O
  frontend só exibe, e o agente lê essas métricas em vez de recalculá-las.
- **Mudou uma tabela ou coluna da Gold?** Avise o time de IA no mesmo PR: a camada semântica e
  o golden set dependem dos nomes, tipos e valores.

## Hooks de pre-commit

Hooks formatam e checam cada commit: ruff (Python), Biome (frontend), segredos (gitleaks) e o
contrato OpenAPI entre backend e frontend. Notebooks nunca são modificados pelos hooks, para
não conflitar com o Databricks. Uma vez por clone, na raiz:

```bash
uv sync --all-packages && (cd frontend && npm ci)    # ferramentas usadas pelos hooks
uvx pre-commit install                               # requer uv
uvx pre-commit run --all-files                       # opcional: roda em tudo
```

Ou simplesmente `make setup`. Se um hook corrigir arquivos, o commit para: revise, rode
`git add` e faça o commit de novo.

## CI

O CI ([`.github/workflows/ci.yml`](../.github/workflows/ci.yml)) roda em todo PR e na `main`,
em 5 jobs. `make ci` roda o mesmo localmente.

| Job | O que faz |
|---|---|
| `hooks` | Os mesmos hooks do pre-commit, mais o gitleaks no histórico inteiro |
| `backend` | `pytest` contra um Postgres de verdade |
| `ai-agent` | `pytest` do agente, inclusive os testes de integração com o banco |
| `frontend` | Checagem de tipos, Vitest e build |
| `docker` | Build das imagens do `docker compose` |

## Contrato da API

O contrato fica em [`contracts/openapi.json`](../contracts/openapi.json), gerado pelo FastAPI.
O frontend gera dele um client tipado e quebra na compilação se a API mudar. Mudou uma rota?
Rode `make openapi`; detalhes em [frontend/README.md](../frontend/README.md#client-da-api).
