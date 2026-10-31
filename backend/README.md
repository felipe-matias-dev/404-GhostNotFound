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

Só quer o portal no ar? `docker compose up` sobe banco, API e frontend juntos: ver o
[README da raiz](../README.md#como-executar-localmente). Os passos abaixo rodam a API
direto na máquina, que é o caminho para desenvolver e rodar os testes.

Primeiro o banco, na **raiz do repositório**:

```bash
# 1. Cria o .env do banco (no PowerShell: Copy-Item .env.example .env)
cp .env.example .env

# 2. Sobe só o PostgreSQL e espera ele ficar pronto (a API roda na sua máquina, na 8000)
docker compose up -d --wait db
```

Depois a API, dentro da pasta **`backend/`**:

```bash
# 3. Instala as dependências (na .venv da raiz, compartilhada com o agente: DEC-017)
uv sync

# 4. Cria o .env da API (no PowerShell: Copy-Item .env.example .env)
cp .env.example .env

# 5. Gera a amostra sintética da Gold em data/gold/
uv run python -m venergy_api.amostra

# 6. Carrega os CSVs de data/gold/ no schema gold do banco
uv run python -m venergy_api.carga

# 7. Cria os 5 usuários de demonstração do login (senha em VENERGY_API_SENHA_DEMO)
uv run python -m venergy_api.usuarios

# 8. Sobe a API em http://127.0.0.1:8000 (Ctrl+C para parar)
uv run uvicorn venergy_api.main:create_app --factory --reload --reload-dir src
```

O `--reload` reinicia a API quando o código muda; o `--reload-dir src` limita isso ao
código, para que mudanças em `.venv` (como logo após o `uv sync`) não a reiniciem.

Se você mudar senha ou porta no `.env` da raiz, ajuste também a URL no `.env` de `backend/`.

A documentação interativa fica em http://127.0.0.1:8000/docs. Quase toda rota exige login
([DEC-049](../docs/decisoes.md)): faça `POST /auth/login` com um dos usuários abaixo e o
navegador guarda o cookie de sessão, que vale para as demais chamadas do `/docs`. Para
conferir, busque a UC `0003` em `GET /unidades-consumidoras/{cod_uc}`.

| Login | Perfil | Pode além de ler os dados e perguntar ao agente |
|---|---|---|
| `henrique` | `diretoria` | só leitura |
| `camila` | `atendimento` | só leitura |
| `rafael` | `perdas` | gerar e atualizar ordens de inspeção |
| `beatriz` | `operacao` | só leitura |
| `patricia` | `ti` | ler a auditoria do agente |

A senha é a de `VENERGY_API_SENHA_DEMO` (a mesma para todos). Quem tem um `.env` antigo precisa
acrescentar `VENERGY_API_JWT_SECRET` (mínimo de 32 caracteres) e `VENERGY_API_SENHA_DEMO`: veja o `.env.example`.

## Rotas

| Rota | O que faz |
|---|---|
| `GET /health` | `200` se a API alcança o banco, `503` se não alcança. Não exige login |
| `POST /auth/login` | Confere `{"login": "...", "senha": "..."}` e grava o cookie `venergy_sessao` (`HttpOnly`, `SameSite=Lax`, 8 horas). `401` com a mesma mensagem para login inexistente e senha errada |
| `GET /auth/me` | Quem está logado (`login`, `nome`, `perfil`): o portal chama ao abrir para montar o menu. `401` sem sessão |
| `POST /auth/logout` | Apaga o cookie de sessão. `204`, com ou sem sessão |
| `GET /unidades-consumidoras/{cod_uc}` | Resumo de uma unidade consumidora, ou `404` se ela não existir |
| `GET /unidades-consumidoras/{cod_uc}/visao-360` | A unidade consumidora numa tela só: cadastro e painel solar, consumo dos 12 meses até a última competência da Gold contra o ano anterior (com `tendencia`: `subiu`, `estavel`, `caiu` ou `sem_comparacao`, faixa de ±10%), `variacao_conta` (a diferença da conta contra o mesmo mês do ano anterior, em R$, dividida em `consumo`, `tarifa`, `bandeira` e `tributos`, cuja soma é a `diferenca`, com os dias de cada conta em `dias_faturados` e `dias_faturados_comparada`, só informativos; vazia sem uma das duas contas, [DEC-057](../docs/decisoes.md)), faturas não pagas, medidor, interrupções, chamados e inspeções ([DEC-044](../docs/decisoes.md)). `404` se a unidade não existir |
| `GET /indicadores/comparacao` | Indicadores e variações entre dois períodos, para a empresa ou recorte de município, bairro e classe ([DEC-041](../docs/decisoes.md)) |
| `GET /indicadores/janelas` | Indicadores em janelas consecutivas de competências completas, para a empresa ou recorte de município, bairro e classe ([DEC-041](../docs/decisoes.md)) |
| `GET /receita/mensal?inicio=&fim=` | KPIs de cada competência (`gold_kpis_mensais`), do mês mais antigo ao mais recente, com recorte opcional (`AAAA-MM`, inclusivo) |
| `GET /receita/comparacao` | kWh e receita de dois períodos (`base_inicio`, `base_fim`, `atual_inicio`, `atual_fim`) e a variação, com filtros opcionais de `municipio`, `bairro` e `classe` |
| `GET /receita/decomposicao/periodos` | Os pares de períodos (`periodo_base`, `periodo_atual`, no formato `AAAA-MM/AAAA-MM`) que a Gold gravou na decomposição: o que o seletor da tela pode oferecer ([DEC-028](../docs/decisoes.md)) |
| `GET /receita/decomposicao?periodo_base=&periodo_atual=&municipio=&bairro=&classe=` | Efeitos preço (com tarifa e bandeira), volume e mix de um par de períodos, que é obrigatório (`422` sem ele ou fora do formato). Sem filtro, uma linha por município; com `municipio`, por bairro; com `municipio` e `bairro`, por classe. `classe` filtra em qualquer nível, e `bairro` sem `municipio` dá `422`. Ordenada da maior queda para a maior alta |
| `GET /continuidade/alimentadores/mensal?inicio=&fim=&cod_alimentador=` | DEC e FEC de cada alimentador por competência, como a Gold calculou; `cod_alimentador` se repete para escolher alguns |
| `GET /continuidade/alimentadores/ranking?inicio=&fim=&criterio=` | Os alimentadores do pior para o melhor num período obrigatório, por `dec` (padrão) ou `fec`. DEC do período = soma das horas ÷ média mensal das UCs atendidas, e `n_meses` diz quantos meses entraram na média ([DEC-033](../docs/decisoes.md)) |
| `GET /continuidade/recortes?inicio=&fim=&criterio=&municipio=&bairro=&classe=` | DEC e FEC do nível abaixo do filtro, do pior para o melhor: sem filtro, por município; com `municipio`, por bairro; com `municipio` e `bairro`, por alimentador. `classe` filtra em qualquer nível, e `bairro` sem `municipio` dá `422` |
| `GET /fila-suspeitas` | Fila paginada e filtrada antes da paginação por `sem_ordem_ativa`, queda, medidor eletromecânico e leituras estimadas. Leituras estimadas aceitam limites entre 25 e 100%, pois a Gold não informa os valores inferiores; motivos ausentes ou não reconhecidos ficam fora da faixa. Limites inválidos ou invertidos retornam `422` com lista de erros de validação. `ordenar_por` e `direcao` controlam a ordenação global |
| `POST /ordens-inspecao` | Só o perfil `perdas` (`403` para os outros). Gera uma ordem de inspeção por UC (`{"cod_ucs": [...]}`), tudo ou nada: `404` se uma UC não existir, `409` se já tiver ordem ativa |
| `GET /ordens-inspecao?status=` | Lista as ordens, das mais recentes para as mais antigas, opcionalmente por status |
| `GET /ordens-inspecao/{id}` | Uma ordem com o histórico de mudanças de status |
| `PATCH /ordens-inspecao/{id}` | Só o perfil `perdas`. Muda o status (`EM_CAMPO`, `GERADA` na volta de campo, `CONCLUIDA` com `resultado`, `CANCELADA`), com `observacao` opcional: `409` se a mudança não for permitida |
| `POST /ai/ask` | Pergunta ao agente de IA (`{"question": "...", "session_id": "..."}`) e devolve a resposta com o `audit_id` do registro gravado em `app.ai_auditoria`. Todo status é gravado, e se a gravação falhar a resposta não sai (`500`). Sem a chave do Gemini, `503` ([DEC-034](../docs/decisoes.md)) |
| `GET /ai/audit/{id}` | Só o perfil `ti` (`403` para os outros). A auditoria de uma resposta: pergunta, SQL executado, views, linhas, modelo, versão do prompt, latência e horário. `404` se não existir |
| `GET /receita/insight?periodo_base=&periodo_atual=&municipio=&bairro=&classe=` | Um insight de IA sobre a ponte de receita do recorte da tela (2 a 4 frases), com as `metricas` que sustentam cada número do texto. Os filtros são os de `/receita/decomposicao`. `texto` vem vazio quando o agente descarta a narração (número fora das métricas) ou o provedor falha: a tela aparece sem insight. O mesmo recorte não paga o modelo duas vezes (cache em memória pelo conteúdo das métricas). `503` sem a chave do Gemini ([DEC-040](../docs/decisoes.md)) |

Com filtro de segmento, a receita e o kWh são somados da fatura de cada UC. DEC e FEC só
existem no total da empresa e por alimentador, porque não dá para somá-los por bairro
([DEC-021](../docs/decisoes.md#dec-021--recortes-de-receita-somados-no-backend-decfec-só-no-total)).

As regras das ordens (status, resultado, uma ordem ativa por UC) estão na
[DEC-009](../docs/decisoes.md#dec-009--modelo-das-ordens-de-inspeção). As tabelas do schema
`app` são criadas pela carga (passo 6), que nunca apaga o que está nelas. Quem já tinha o banco
antes da [DEC-050](../docs/decisoes.md#dec-050--autoria-nos-eventos-das-ordens-de-inspeção) só
precisa reiniciar a API: a subida, assim como a carga, acrescenta a coluna `autor_login` ao
histórico das ordens sem apagar nenhuma.

## Contrato OpenAPI

O frontend gera o client a partir do OpenAPI da API, versionado em
[`contracts/openapi.json`](../contracts/openapi.json). Mudou uma rota, um parâmetro ou um
schema de resposta? Exporte o contrato e commite junto com a mudança:

```bash
uv run python -m venergy_api.openapi
```

O export não precisa de banco nem de `.env`. O hook de pre-commit e o CI rodam esse comando
e falham se o arquivo commitado estiver desatualizado. Declare em `responses=` os erros que
a rota devolve (ex.: `404` com `ErroSchema`), para que o frontend também receba o erro tipado.

## Dados: amostra e Gold real

A API não sabe se os dados são de amostra ou reais: os dois chegam pelo mesmo caminho
(CSV em `data/gold/` → carga → banco).

- **Amostra:** 8 unidades consumidoras e 24 meses (2024 e 2025) com valores inventados,
  gerados pelo passo 5. Nada vem do dataset da V-Energy, que é confidencial.
- **Gold real:** coloque os CSVs exportados do Databricks em `data/gold/`, um arquivo
  por tabela, e rode a carga (passo 6) de novo.

A carga espera um CSV para cada tabela do contrato da Gold
([`contracts/gold_schema.yaml`](../contracts/gold_schema.yaml), versão 0.3), 12 ao todo:

| Arquivo | Uma linha por |
|---|---|
| `gold_dim_uc.csv` | unidade consumidora |
| `gold_fato_faturamento_mensal.csv` | unidade consumidora × competência (uma fatura) |
| `gold_receita_decomposicao.csv` | par de períodos × município × bairro × classe × GD |
| `gold_kpis_mensais.csv` | competência (total da empresa) |
| `gold_kpis_segmento_mensal.csv` | competência × município × bairro × classe do cadastro × GD × alimentador × tipo de medidor |
| `gold_reconciliacao_faturamento.csv` | competência |
| `gold_continuidade_alimentador_mensal.csv` | alimentador × competência |
| `gold_fila_suspeitas.csv` | unidade consumidora suspeita |
| `gold_interrupcoes_uc.csv` | ocorrência (UC 360) |
| `gold_atendimentos_uc.csv` | chamado (UC 360) |
| `gold_medidor_uc.csv` | unidade consumidora com medidor (UC 360) |
| `gold_inspecoes_uc.csv` | inspeção de campo |

O backend acompanha o contrato no mesmo PR em que ele muda
([DEC-014](../docs/decisoes.md#dec-014--o-backend-espelha-o-contrato-da-gold)).

A carga valida cada linha contra o contrato (`src/venergy_api/schemas.py`). Se um
arquivo estiver fora do formato, ela é cancelada, informa a linha e a coluna com
problema e mantém os dados anteriores. Ela lê cada CSV aos poucos e grava de 10 mil em
10 mil linhas, então a memória não depende do tamanho da Gold: com ~4 milhões de linhas o
pico foi de ~110 MB e a carga levou uns 7 minutos
([DEC-038](../docs/decisoes.md#dec-038--carga-da-gold-em-lotes-com-uma-rodada-de-conferência-antes-de-gravar)).
Antes de gravar, uma primeira rodada confere todos os arquivos sem guardar nada: o arquivo
ruim falha cedo, sem apagar a Gold anterior. A cada execução, ela recria as tabelas da Gold:
coluna nova no contrato entra sem apagar nada à mão. Na mesma transação, ela também
recria as views `sem_*` do agente de IA a partir de `ai-agent/semantic/views.sql`; se esse
arquivo não bater com a Gold, a carga é cancelada e o banco fica como estava. O gerador da
amostra nunca sobrescreve um CSV existente sem `--force`.

O teste `tests/test_contrato_gold.py` compara o contrato com os modelos e os schemas do
backend. Mudou o YAML? Ele aponta o que o backend precisa acompanhar.

`data/` fica na raiz do repositório e está no `.gitignore`: nenhum dado é versionado.

## Banco

O `docker compose` cria, na primeira subida (`infra/postgres/init/01-init.sh`):

| O quê | Para quê |
|---|---|
| Schema `gold` | Tabelas da Gold e views `sem_*` do agente, recriadas a cada carga |
| Schema `app` | Dados criados no portal (ordens de inspeção). A carga nunca apaga uma linha dele |
| Usuário `venergy` | Usado pela API: lê e escreve |
| Usuário `venergy_agent` | Usado pelo agente de IA: só `SELECT` no schema `gold`, sem acesso a `app` |
| Banco `venergy_test` | Mesma estrutura, usado só pelos testes |

O agente de IA conecta com
`postgresql+psycopg://venergy_agent:<AGENT_DB_PASSWORD>@127.0.0.1:5433/venergy`.

Para recriar o banco do zero (apaga todos os dados): `docker compose down -v` e depois
`docker compose up -d --wait db`.

## Configuração

Variáveis lidas do `.env` (veja `.env.example`):

| Variável | Para quê |
|---|---|
| `VENERGY_API_DATABASE_URL` | Endereço do banco. Obrigatória |
| `VENERGY_API_GOLD_DIR` | Pasta dos CSVs da Gold. Obrigatória |
| `VENERGY_API_CORS_ORIGINS` | Endereços do frontend autorizados a chamar a API pelo navegador. Padrão: `["http://localhost:3000"]` |

Os caminhos são relativos à pasta `backend/`, de onde os comandos rodam.

## Testes e qualidade

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

Os testes rodam no banco `venergy_test` (precisam do `docker compose up -d --wait db`) e não
dependem do `.env` nem dos dados de desenvolvimento. Quem mudou senha ou porta define
`VENERGY_API_TEST_DATABASE_URL` e `VENERGY_API_TEST_AGENT_DATABASE_URL`.

## Estrutura

```
src/venergy_api/
├── main.py       # cria o app: CORS e rotas
├── config.py     # configurações lidas do .env
├── database.py   # conexão com o banco e sessão por requisição
├── models.py     # tabelas do banco
├── ordens.py     # regras das ordens de inspeção (máquina de estados), sem banco
├── schemas.py    # contrato dos dados: validação da carga e formato das respostas
├── carga.py      # CSVs da Gold → banco
├── estrutura_app.py  # colunas novas do schema app, na carga e na subida, sem apagar dado
├── amostra.py    # gerador da amostra sintética
├── openapi.py    # export do contrato para contracts/openapi.json
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
| A carga é cancelada com "arquivo não encontrado" ou "colunas faltando" | A amostra em `data/gold/` é de uma versão anterior do contrato: `uv run python -m venergy_api.amostra --force` |
| A carga é cancelada com "as views do agente não batem com a Gold" | O `ai-agent/semantic/views.sql` cita coluna que o contrato não tem mais: avise o time de GenAI para regerar o arquivo |
| A carga com a Gold real leva alguns minutos e não imprime nada até acabar | É o esperado: ~4 milhões de linhas levam uns 7 minutos ([DEC-038](../docs/decisoes.md)). Não interrompa: se parar no meio, a transação desfaz tudo e o banco fica como estava |
| A carga é cancelada com "o arquivo mudou durante a carga" | O CSV foi trocado entre a conferência e a gravação. Rode a carga de novo |
| Testes param com "Banco de testes indisponível" | O banco não está no ar: `docker compose up -d --wait db` |
| A API não sobe: porta 8000 em uso | A API do `docker compose` está no ar: `docker compose stop api web` |
| Testes param com "Usuário do agente não conecta" | O banco foi criado antes do script de inicialização atual: `docker compose down -v` |

As decisões por trás desta estrutura estão em [docs/decisoes.md](../docs/decisoes.md)
(DEC-002 a DEC-004, DEC-010 e DEC-014).
