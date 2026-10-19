# V-Energy Grid 360 (404-GhostNotFound)

Plataforma da distribuidora V-Energy: pipeline de dados (Databricks), portal web (FastAPI + React) e agente Text-to-SQL. Contexto completo em `README.md`, `docs/decisoes.md`, `ai-agent/docs/specs/` e `ai-agent/docs/plans/`.

## Estrutura

- `data-engineering/`: notebooks Bronze, Silver e Gold e o Workflow (Databricks).
- `backend/`: API FastAPI (`src/venergy_api`), com SQLAlchemy 2.0 e psycopg.
- `frontend/`: React + TypeScript (Vite). Ver `frontend/AGENTS.md` e `frontend/README.md`.
- `ai-agent/`: agente Text-to-SQL (`src/venergy_agent`). Ainda sem código: o trabalho segue o spec e o plano em `ai-agent/docs/`.
- `infra/postgres/init/`: script que cria os schemas `gold` e `app` e o usuário somente leitura do agente.
- `docs/`: decisões, dicionário de dados e diagnóstico da receita.

## Comandos

Backend (rodar dentro de `backend/`):
- `uv run python -m venergy_api.amostra`: gera a amostra sintética em `data/gold/` (use `--force` só para sobrescrever).
- `uv run python -m venergy_api.carga`: carrega os CSVs da Gold no banco local.
- `uv run pytest` e `uv run ruff check`.

Banco local (na raiz): `docker compose up -d`. Precisa do `.env` copiado de `.env.example`.

## Regras do projeto

- **Dataset nunca vai para o repositório.** Os arquivos brutos e os CSVs da Gold ficam em `data/`, que está no `.gitignore`. Nada de `*.csv`, `*.xlsx` ou `*.zip` versionado.
- **Decisões vão para `docs/decisoes.md`** (formato DEC-NNN). Toda suposição feita onde o case não é explícito entra lá e no README.
- **Commits** no padrão Conventional Commits (`feat:`, `fix:`, `docs:`, `chore:`, `test:`, `refactor:`). Uma branch por tarefa, PR revisado por outra pessoa antes da `main`.
- **Não faça commit, push nem abra PR sem pedido explícito.**
- **Linguagem:** código e nomes técnicos em inglês quando o módulo pedir (o `ai-agent` segue o plano); documentação e textos para a banca em português. Os nomes de tabelas, colunas e métricas seguem a linguagem ubíqua do planejamento (`gold_dim_uc`, `cod_uc`, `competencia` YYYY-MM).
- **Cálculos de negócio** (DEC/FEC, efeito preço × volume) ficam na Gold e no backend. O frontend só exibe. O agente lê essas métricas, não as recalcula.

## Agente Text-to-SQL

- Usa o usuário `venergy_agent`, que só lê o schema `gold` e nunca acessa `app`. Nunca use as credenciais do backend no agente.
- O agente consulta só as views `sem_*` (allowlist). Toda consulta passa pelo validador antes de executar.
- Requisito central: se não souber, diz que não sabe. Resposta inventada é falha crítica.
- Todo número na resposta vem do resultado de uma consulta. O LLM não faz aritmética.
- Mudança de prompt, modelo ou camada semântica só entra se o golden set não regredir.
- Guia de boas práticas: `contexto-agente-text-to-sql.md` (na pasta de contexto do projeto).

## Ordens de inspeção e schemas

- `gold.*` é recarregável e é sobrescrito pela carga. `app.*` (ordens de inspeção) nunca é tocado por ela.
