# Backend

API do portal V-Energy Grid 360 em FastAPI (Python). Lê as tabelas Gold de um banco
SQLite local, que é carregado a partir de CSVs.

## Pré-requisitos

- Python 3.12 ou mais novo.
- [uv](https://docs.astral.sh/uv/), que instala as dependências nas versões exatas do `uv.lock`:
  - Windows (PowerShell): `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`
  - macOS/Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh`

## Como rodar

Todos os comandos rodam dentro da pasta `backend/`.

```bash
# 1. Instala as dependências
uv sync

# 2. Cria o arquivo de configuração (no PowerShell: Copy-Item .env.example .env)
cp .env.example .env

# 3. Gera a amostra sintética da Gold em data/gold/
uv run python -m venergy_api.amostra

# 4. Carrega os CSVs de data/gold/ no banco data/venergy.db
uv run python -m venergy_api.carga

# 5. Sobe a API em http://127.0.0.1:8000
uv run uvicorn venergy_api.main:create_app --factory --reload
```

A documentação interativa fica em http://127.0.0.1:8000/docs. Para conferir, busque
a UC `0003` em `GET /unidades-consumidoras/{uc_id}`.

## Rotas

| Rota | O que faz |
|---|---|
| `GET /health` | `200` se a API alcança o banco, `503` se não alcança |
| `GET /unidades-consumidoras/{uc_id}` | Resumo de uma unidade consumidora, ou `404` se ela não existir |

## Dados: amostra e Gold real

A API não sabe se os dados são de amostra ou reais: os dois chegam pelo mesmo caminho
(CSV em `data/gold/` → carga → banco).

- **Amostra:** 8 unidades consumidoras com valores inventados, geradas pelo passo 3.
  Nada vem do dataset da V-Energy, que é confidencial.
- **Gold real:** coloque os CSVs exportados do Databricks em `data/gold/`, um arquivo
  por tabela (`uc_resumo.csv`), e rode a carga (passo 4) de novo.

A carga valida cada linha contra o contrato (`src/venergy_api/schemas.py`). Se um
arquivo estiver fora do formato, ela é cancelada, informa a linha e a coluna com
problema e mantém os dados anteriores. O gerador da amostra nunca sobrescreve um CSV
existente sem `--force`.

`data/` fica na raiz do repositório e está no `.gitignore`: nenhum dado é versionado.

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

Os testes usam um SQLite temporário e não dependem do `.env` nem dos dados locais.

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
| A API não sobe e reclama de `database_url` ou `gold_dir` | Falta o `.env` (passo 2) |
| `/health` responde `503` | O caminho do banco no `.env` está errado, ou os comandos não rodaram de dentro de `backend/` |
| A busca de UC responde `500` | A carga ainda não rodou (passos 3 e 4) |

As decisões por trás desta estrutura estão em [docs/decisoes.md](../docs/decisoes.md)
(DEC-002 a DEC-004).
