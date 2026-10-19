# Backend

API do portal V-Energy Grid 360 em FastAPI (Python). Lê as tabelas Gold de um
PostgreSQL local, que é carregado a partir de CSVs.

## Pré-requisitos

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) aberto, para o banco.
- Python 3.12 ou mais novo.
- [uv](https://docs.astral.sh/uv/), que instala as dependências nas versões exatas do `uv.lock`:
  - Windows (PowerShell): `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`
  - macOS/Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh`

## Como rodar

Primeiro o banco, na **raiz do repositório**:

```bash
# 1. Cria o .env do banco (no PowerShell: Copy-Item .env.example .env)
cp .env.example .env

# 2. Sobe o PostgreSQL e espera ele ficar pronto
docker compose up -d --wait
```

Depois a API, dentro da pasta **`backend/`**:

```bash
# 3. Instala as dependências
uv sync

# 4. Cria o .env da API (no PowerShell: Copy-Item .env.example .env)
cp .env.example .env

# 5. Gera a amostra sintética da Gold em data/gold/
uv run python -m venergy_api.amostra

# 6. Carrega os CSVs de data/gold/ no schema gold do banco
uv run python -m venergy_api.carga

# 7. Sobe a API em http://127.0.0.1:8000
uv run uvicorn venergy_api.main:create_app --factory --reload
```

Se você mudar senha ou porta no `.env` da raiz, ajuste também a URL no `.env` de `backend/`.

A documentação interativa fica em http://127.0.0.1:8000/docs. Para conferir, busque
a UC `0003` em `GET /unidades-consumidoras/{cod_uc}`.

## Rotas

| Rota | O que faz |
|---|---|
| `GET /health` | `200` se a API alcança o banco, `503` se não alcança |
| `GET /unidades-consumidoras/{cod_uc}` | Resumo de uma unidade consumidora, ou `404` se ela não existir |

## Dados: amostra e Gold real

A API não sabe se os dados são de amostra ou reais: os dois chegam pelo mesmo caminho
(CSV em `data/gold/` → carga → banco).

- **Amostra:** 8 unidades consumidoras com valores inventados, geradas pelo passo 5.
  Nada vem do dataset da V-Energy, que é confidencial.
- **Gold real:** coloque os CSVs exportados do Databricks em `data/gold/`, um arquivo
  por tabela (`gold_dim_uc.csv`), e rode a carga (passo 6) de novo.

A carga valida cada linha contra o contrato (`src/venergy_api/schemas.py`). Se um
arquivo estiver fora do formato, ela é cancelada, informa a linha e a coluna com
problema e mantém os dados anteriores. O gerador da amostra nunca sobrescreve um CSV
existente sem `--force`.

`data/` fica na raiz do repositório e está no `.gitignore`: nenhum dado é versionado.

## Banco

O `docker compose` cria, na primeira subida (`infra/postgres/init/01-init.sh`):

| O quê | Para quê |
|---|---|
| Schema `gold` | Tabelas da Gold, recarregadas a partir dos CSVs |
| Schema `app` | Dados criados no portal (ordens de inspeção). A carga nunca toca nele |
| Usuário `venergy` | Usado pela API: lê e escreve |
| Usuário `venergy_agent` | Usado pelo agente de IA: só `SELECT` no schema `gold`, sem acesso a `app` |
| Banco `venergy_test` | Mesma estrutura, usado só pelos testes |

O agente de IA conecta com
`postgresql+psycopg://venergy_agent:<AGENT_DB_PASSWORD>@127.0.0.1:5433/venergy`.

Para recriar o banco do zero (apaga todos os dados): `docker compose down -v` e depois
`docker compose up -d --wait`.

## Configuração

Variáveis lidas do `.env` (veja `.env.example`):

| Variável | Para quê |
|---|---|
| `VENERGY_API_DATABASE_URL` | Endereço do banco. Obrigatória |
| `VENERGY_API_GOLD_DIR` | Pasta dos CSVs da Gold. Obrigatória |
| `VENERGY_API_CORS_ORIGINS` | Endereços do frontend autorizados a chamar a API pelo navegador. Padrão: `["http://localhost:5173"]` |

Os caminhos são relativos à pasta `backend/`, de onde os comandos rodam.

## Testes e qualidade

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

Os testes rodam no banco `venergy_test` (precisam do `docker compose up`) e não
dependem do `.env` nem dos dados de desenvolvimento. Quem mudou senha ou porta define
`VENERGY_API_TEST_DATABASE_URL` e `VENERGY_API_TEST_AGENT_DATABASE_URL`.

## Estrutura

```
src/venergy_api/
├── main.py       # cria o app: CORS e rotas
├── config.py     # configurações lidas do .env
├── database.py   # conexão com o banco e sessão por requisição
├── models.py     # tabelas do banco
├── schemas.py    # contrato dos dados: validação da carga e formato das respostas
├── carga.py      # CSVs da Gold → banco
├── amostra.py    # gerador da amostra sintética
└── routers/      # rotas, um arquivo por domínio
tests/            # pytest
```

## Problemas comuns

| Sintoma | Causa provável |
|---|---|
| `docker compose` reclama de `POSTGRES_PASSWORD` | Falta o `.env` da raiz (passo 1) |
| A API não sobe e reclama de `database_url` ou `gold_dir` | Falta o `.env` de `backend/` (passo 4) |
| `/health` responde `503` | O banco está parado (`docker compose ps`) ou a URL no `.env` de `backend/` está errada |
| A busca de UC responde `500` | A carga ainda não rodou (passos 5 e 6) |
| Testes param com "Banco de testes indisponível" | O banco não está no ar: `docker compose up -d --wait` |
| Testes param com "Usuário do agente não conecta" | O banco foi criado antes do script de inicialização atual: `docker compose down -v` |

As decisões por trás desta estrutura estão em [docs/decisoes.md](../docs/decisoes.md)
(DEC-002 a DEC-004).
