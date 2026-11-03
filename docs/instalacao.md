# Instalação e operação local

O projeto é dockerizado: banco, API e portal sobem juntos pelo Docker Compose, sem instalar
Python, Node nem PostgreSQL na máquina. Para trazer os dados reais, veja
[dos arquivos brutos ao portal](dados-brutos.md).

## O que instalar

| Ferramenta | Precisa? | Para quê |
|---|---|---|
| Docker com Compose v2 | Sim | Sobe banco, API e portal. No Linux, o Docker Engine com o plugin `docker compose`; no macOS e no Windows, o Docker Desktop |
| Chave do Gemini | Só para o agente | Chat e insights de IA. Sem ela, o resto funciona |
| Workspace do Databricks | Só para os dados reais | Processar os arquivos brutos ([guia](dados-brutos.md)). Sem ele, use a amostra sintética |
| `make` | Não | Atalhos para os comandos deste guia e do CI ([abaixo](#atalhos-com-make)) |
| `uv` (Python 3.12+) e Node 22.12+ | Não | Rodar API, agente ou portal direto na máquina, rodar os testes e instalar os hooks ([fora do Docker](#fora-do-docker)) |

Os comandos abaixo são para um shell POSIX (bash ou zsh, no Linux, no macOS ou no WSL). No
PowerShell, troque o `cp` por `Copy-Item` e o `mkdir -p` por `mkdir`; os comandos `docker` são
os mesmos.

## Subir o ambiente

Na raiz do repositório:

```bash
# 1. Cria o .env com senhas e portas. Sem ele, o docker compose não sobe.
cp .env.example .env
mkdir -p data/gold

# 2. Sobe banco, API e frontend e espera ficarem prontos (a 1ª vez constrói as imagens)
docker compose up -d --wait

# 3. Gera a amostra sintética da Gold e carrega no banco
docker compose run --rm api python -m venergy_api.amostra
docker compose run --rm api python -m venergy_api.carga

# 4. Cria os 5 usuários de demonstração do login (ou: make users)
docker compose run --rm api python -m venergy_api.usuarios
```

| O quê | Onde |
|---|---|
| Portal | http://localhost:3000 |
| API e documentação interativa | http://127.0.0.1:8000/docs |
| Banco | `127.0.0.1:5433`, usuário `venergy` |

O passo `mkdir` cria a pasta da Gold com o seu usuário. Sem ele, no Linux, o Docker a cria
como root e o gerador da amostra não consegue gravar.

As portas vêm do `.env` (`POSTGRES_PORT`, `API_PORT`, `WEB_PORT`). O banco usa a 5433 para
não colidir com um PostgreSQL já instalado, e todos os serviços escutam só em `127.0.0.1`.

## Logins de demonstração

Use um destes logins com a senha `SENHA_DEMO` do `.env` (a mesma para todos, só para rodar
localmente). Quem já tinha um `.env` antes do login precisa acrescentar `JWT_SECRET` e
`SENHA_DEMO`: o `.env.example` mostra como, e sem `JWT_SECRET` o `docker compose` para com
essa mensagem.

| Login | Perfil | Além de ler os dados |
|---|---|---|
| `henrique` | diretoria | só leitura |
| `camila` | atendimento | só leitura |
| `rafael` | perdas | gera e atualiza ordens de inspeção |
| `beatriz` | operação | só leitura |
| `patricia` | TI | lê a auditoria do agente |

Permissões, cookie e limite de tentativas:
[DEC-049](decisoes.md#dec-049--login-com-cookie-httponly-e-perfis-por-cargo) e
[DEC-065](decisoes.md#dec-065--limite-de-tentativas-de-login-por-login-e-endereço).

## Agente de IA

O agente precisa de `GOOGLE_API_KEY` no `.env` (chave do Gemini, uma por pessoa). Sem ela,
tudo sobe, mas `POST /ai/ask` responde `503`. Cada resposta fica em `app.ai_auditoria` e se lê
em `GET /ai/audit/{id}` ([DEC-034](decisoes.md#dec-034--auditoria-do-agente-de-ia-gravação-leitura-e-subida-sem-a-chave)).

Modelos reserva (`GEMINI_FALLBACK_MODEL`) e a chave do OpenRouter são opcionais; o
`.env.example` explica cada variável. Como o agente funciona: [agente de IA](agente-ia.md).

## Dia a dia

O código de `backend/src` e `frontend/src` é montado nos containers: API e portal
recarregam a cada mudança. Mudou dependência (`pyproject.toml`, `package.json`) ou
`vite.config.ts`? Rode `docker compose up -d --build`.

| Comando | Para quê |
|---|---|
| `docker compose logs -f api web` | Acompanhar os logs |
| `docker compose down` | Parar tudo (os dados do banco ficam) |
| `docker compose down -v` | Parar e apagar o banco (refaz o script de `infra/postgres/init`) |
| `docker compose run --rm api python -m venergy_api.amostra --force` | Regravar a amostra sintética por cima de `data/gold/` |

## Atalhos com `make`

O `Makefile` da raiz só chama os comandos deste guia e do CI, para quem prefere um comando
curto. Não é obrigatório: tudo funciona com os comandos `docker compose` acima.

```bash
make           # lista os alvos
make up        # sobe banco, API e portal
make sample    # gera a amostra sintética
make load      # carrega data/gold/ no banco
make users     # cria os logins de demonstração
make down      # derruba os containers
make setup     # instala as dependências locais e os hooks de commit
make test      # testes do backend e do agente (sobe o banco antes)
make ci        # roda local o mesmo que o CI: lint, testes e build do frontend
```

| Alvos | Além do `make`, precisam de |
|---|---|
| `up`, `db`, `sample`, `load`, `users` | Docker e `uv`: antes de subir, o `make` copia os `.env` que faltam com um script Python rodado pelo `uv`, sem nunca sobrescrever |
| `down` | Docker |
| `setup`, `openapi` | `uv` e Node |
| `test`, `eval` | `uv` e Docker (sobem o banco antes) |
| `lint`, `eval-compare` | `uv` |
| `frontend-check` | Node |
| `ci` | `uv`, Node e Docker |

As receitas usam só `uv`, `npm` e `docker`, sem comandos de shell de um sistema específico.
O `make` costuma vir instalado no Linux e no macOS (no macOS, com as Command Line Tools do
Xcode).

<details>
<summary>Instalar o <code>make</code> no Windows</summary>

Instale uma vez com **um** destes:

```bash
winget install ezwinports.make
```

```bash
choco install make
```

```bash
scoop install make
```

</details>

## Observabilidade (opcional)

Cada requisição pode virar um trace do OpenTelemetry, com a rota, as consultas ao Postgres e
as chamadas ao Gemini, cada uma com a sua duração ([DEC-068](decisoes.md#dec-068--rastreamento-das-requisições-com-opentelemetry)). Desligado por
padrão: o passo a passo acima não precisa disso.

```bash
# 1. No .env: RASTREAMENTO_ENDPOINT=http://jaeger:4318/v1/traces
# 2. Sobe o ambiente com o Jaeger
docker compose --profile observabilidade up -d --wait
```

Abra http://localhost:16686, escolha o serviço `venergy-api` e clique em **Find Traces**. Para
achar uma pergunta da auditoria do agente, busque pela tag `venergy.ai.request_id=<request_id>`.
O Jaeger guarda os traces em memória: reiniciar o container apaga todos.

## Fora do Docker

Para desenvolver, rodar os testes ou depurar, API, agente e portal também rodam direto na
máquina. O banco continua no Docker: `docker compose up -d --wait db` (ou `make db`).

| Parte | Ferramenta | Como |
|---|---|---|
| API e agente de IA | [`uv`](https://docs.astral.sh/uv/) com Python 3.12+ | Backend e agente são um workspace do uv com um único `uv.lock` na raiz ([DEC-017](decisoes.md#dec-017--workspace-do-uv-com-um-único-uvlock)). Passo a passo em [backend/README.md](../backend/README.md) e [ai-agent/README.md](../ai-agent/README.md) |
| Portal | Node 22.12+ (ou 20.19+) e `npm` | `npm ci` e `npm run dev` em `frontend/`, com a API no ar. Ver [frontend/README.md](../frontend/README.md) |
| Hooks de commit e CI local | `uv` e Node | `make setup` uma vez; `make ci` antes do PR. Ver [contribuindo](contribuindo.md) |

Rodando fora do Docker, cada módulo lê o próprio `.env` (`backend/.env`, `ai-agent/.env`,
`frontend/.env`), criados a partir dos `.env.example` de cada pasta. Mudou a senha ou a porta
do banco no `.env` da raiz? Ajuste também as URLs nesses arquivos.

## Problemas comuns

| Sintoma | Causa e solução |
|---|---|
| `defina POSTGRES_PASSWORD no .env da raiz` (ou `JWT_SECRET`) | Falta o `.env` ou a variável nele: copie do `.env.example` |
| A amostra não grava em `data/gold/` (Linux) | A pasta foi criada pelo Docker como root: `sudo chown -R $USER data` ou apague e rode o `mkdir` |
| `Carga cancelada, banco não foi alterado. arquivo não encontrado` | Faltou um dos 12 CSVs em `data/gold/`: gere a amostra ou baixe a Gold de novo |
| `POST /ai/ask` responde `503` | `GOOGLE_API_KEY` vazia no `.env`; preencha e rode `docker compose up -d` |
| O login responde `429` | Cinco senhas erradas em 15 minutos; espere o tempo indicado |
| A porta 5433, 8000 ou 3000 já está em uso | Troque `POSTGRES_PORT`, `API_PORT` ou `WEB_PORT` no `.env` |
| A senha do banco quebra a conexão | Use só letras, números e hífen: `@ : / #` quebram a URL de conexão |
