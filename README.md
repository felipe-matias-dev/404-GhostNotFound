# V-Energy Grid 360 — Time 404-GhostNotFound

Plataforma de visão 360 da V-Energy (Rocket Lab 2026.2 · Visagio): pipeline de dados no Databricks, portal web e agente de IA, mais o diagnóstico da variação de receita.

## Estrutura

| Pasta | Conteúdo |
|---|---|
| [`data-engineering/`](data-engineering/) | Notebooks Bronze → Silver → Gold + `.yaml` do Workflow |
| [`backend/`](backend/) | API do portal (FastAPI) |
| [`frontend/`](frontend/) | Aplicação web (React + TypeScript + Vite) |
| [`ai-agent/`](ai-agent/) | Agente Text-to-SQL e insights de IA |
| [`docs/`](docs/) | Diagnóstico da receita, dicionário de dados e decisões |

## Time

| Frente | Integrantes |
|---|---|
| Engenharia de Dados | Arthur Oliveira, Alysson, Gabriel |
| Portal Web | Felipe Matias, João Euclides |
| Inteligência Artificial | Luis Felipe Perylo, Lucas Mendes |

## Visão geral e decisões de arquitetura

_TODO_

## Como executar localmente

_TODO: passo a passo dos módulos de dados, frontend e agente._

### Banco de dados

Requer [Docker Desktop](https://www.docker.com/products/docker-desktop/) aberto. Na raiz:

```bash
# 1. Cria o .env com as senhas do banco. Sem ele, o docker compose não sobe.
cp .env.example .env                       # no PowerShell: Copy-Item .env.example .env

# 2. Sobe o PostgreSQL e espera ele ficar pronto
docker compose up -d --wait
```

### Backend

Requer Python 3.12+ e [uv](https://docs.astral.sh/uv/). Dentro da pasta `backend/`:

```bash
# 3. Instala as dependências
uv sync

# 4. Cria o .env da API
cp .env.example .env                       # no PowerShell: Copy-Item .env.example .env

# 5. Gera a amostra sintética da Gold e carrega no banco
uv run python -m venergy_api.amostra
uv run python -m venergy_api.carga

# 6. (Opcional) Roda os testes
uv run pytest

# 7. Sobe a API em http://127.0.0.1:8000 (Ctrl+C para parar)
uv run uvicorn venergy_api.main:create_app --factory --reload --reload-dir src
```

A API sobe em http://127.0.0.1:8000, com documentação em `/docs`. Detalhes, testes e
como usar a Gold real em vez da amostra: [backend/README.md](backend/README.md).

## Execução do Workflow no Databricks

_TODO: print da execução bem-sucedida._

## Dicionário de dados e diagnóstico da receita

- [Dicionário de dados](docs/dicionario-de-dados.md)
- [Diagnóstico da receita](docs/diagnostico-receita.md)

## Suposições

Ver [docs/decisoes.md](docs/decisoes.md).
