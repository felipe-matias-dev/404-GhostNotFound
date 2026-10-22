# Decisões e suposições

Registro das decisões tomadas pelo time onde os requisitos do case não eram explícitos. Alimenta a seção de suposições do README.

| Data | Decisão | Motivo | Quem |
|---|---|---|---|
| 19/10/2026 | DEC-001: arquivos de origem em `v_energy.default.landing`; `bronze` só com tabelas | Separa arquivos imutáveis de tabelas recriáveis | Arthur |
| 19/10/2026 | Frontend com TanStack Start em modo SPA (React + TypeScript + Vite) | O gerador já integra Router, Query, Form, Table, devtools e React Compiler; SSR desligado porque o FastAPI é o único backend | João Euclides |
| 19/10/2026 | Autenticação e perfis ficam no FastAPI; better-auth removido do frontend | Pensei em usar BetterAuth, porém, permissão precisa ser checada onde estão os dados, melhor evitar um segundo backend em Node com sessões que o FastAPI não valida | João Euclides |
| 19/10/2026 | Em dev, o Vite encaminha `/api/*` para o FastAPI removendo o prefixo; base da API configurável por `VITE_API_URL` | Evita CORS no desenvolvimento e não exige prefixo `/api` nas rotas do backend; endereço do backend ainda não definido | João Euclides |
| 19/10/2026 | Frontend em camadas por feature (`features/<feature>` com `api.ts`, `hooks`, `pages`; `routes/` só define rotas) | Times e agentes seguem a mesma organização; regras em `frontend/README.md` e `frontend/AGENTS.md` | João Euclides |
| 19/10/2026 | Cálculos de negócio (DEC/FEC, efeito-preço × efeito-volume) ficam na camada Gold/backend; o frontend só exibe | Uma única fonte dos números para portal e agente de IA | João Euclides |
| 19/10/2026 | Valores exibidos (R$, kWh, %, competência, datas) formatados só por `frontend/src/lib/format.ts` | Mesmo número com o mesmo formato em todas as telas | João Euclides |
| 19/10/2026 | DEC-002: banco local PostgreSQL em Docker, com schemas `gold` e `app` | Usuário somente leitura nativo para o agente; recarga da Gold não apaga as ordens de inspeção | Time |
| 19/10/2026 | DEC-003: walking skeleton com amostra sintética da Gold | Integração entre camadas testada desde o início, sem depender do dataset confidencial | Time |
| 19/10/2026 | DEC-004 (proposta): Gold entregue em CSV, um arquivo por tabela, em `data/gold/` | Um único caminho de carga, validado contra o contrato, para amostra e Gold real | Felipe |
| 19/10/2026 | DEC-005: contrato API → frontend em `contracts/openapi.json`, gerado pelo FastAPI; client com `openapi-typescript` + `openapi-fetch` | O front quebra na compilação quando o contrato muda; a mudança de contrato aparece no diff do PR | João Euclides |
| 19/10/2026 | DEC-006: `docker compose up` sobe banco, API e Vite em modo de desenvolvimento | Um comando roda o portal em qualquer máquina; deploy em nuvem está fora do escopo | João Euclides |
| 19/10/2026 | DEC-007: qualidade garantida por pre-commit local e pelo mesmo conjunto de checagens no CI | Código formatado e contrato em dia sem depender de lembrar; o CI barra quem pula o hook | João Euclides |
| 19/10/2026 | DEC-008: Bronze com auditoria básica (full refresh, tudo string, `ingestion_timestamp` e `source_file`) | Dados o mais próximos da origem; rastreabilidade sem log próprio de ingestão | Alisson |
| 20/10/2026 | DEC-009: ordens de inspeção em `app.ordem_inspecao` + `app.ordem_evento`, sem FK para a Gold, com máquina de estados e no máximo uma OI ativa por UC | O trabalho de campo sobrevive a cada recarga da Gold; o resultado registrado mede se a fila de suspeitas acerta | Felipe |
| 20/10/2026 | DEC-010: energia e dinheiro como `numeric` no banco e número no JSON da API | Somas em SQL sem resíduo de arredondamento; o frontend recebe número, sem converter texto | Felipe |

## DEC-001 · Localização dos arquivos de origem (landing)

- **Data:** 19/10/2026 · **Área:** Dados · **Autor:** Arthur
- **Decisão:** os arquivos brutos ficam no volume `v_energy.default.landing`
  (`/Volumes/v_energy/default/landing/`). O schema `v_energy.bronze` contém
  apenas tabelas Delta.
- **Motivo:** separar arquivos imutáveis de tabelas recriáveis. Com o volume
  dentro de `bronze`, um `DROP SCHEMA bronze CASCADE` apagaria os originais.
- **Regras:** o pipeline nunca escreve nem apaga nada em `landing`. O caminho
  é parametrizado por widget no notebook `Landing_to_Bronze`.

## DEC-002 · Banco local PostgreSQL

- **Data:** 19/10/2026 · **Área:** Portal, Dados e IA · **Autor:** Time (ADR-01
  do planejamento)
- **Decisão:** o banco local é um PostgreSQL 17 em Docker (`docker-compose.yml`
  na raiz). O banco `venergy` tem dois schemas: `gold`, recarregável a partir dos
  CSVs, e `app`, com os dados criados no portal (ordens de inspeção). O backend
  acessa o banco pelo SQLAlchemy 2.0 com o driver psycopg.
- **Motivo:** o Postgres tem usuários com permissão própria, então o agente de IA
  ganha um usuário que só lê, exigido por Segurança da Informação. A separação
  `gold`/`app` impede que a recarga da Gold apague o trabalho da equipe de perdas.
- **Alternativa descartada:** SQLite, que dispensa instalação, mas não tem
  usuários nem schemas: o somente leitura do agente dependeria só de uma opção
  na conexão.
- **Regras:**
  - O agente conecta com o usuário `venergy_agent`: `SELECT` apenas no schema
    `gold`, transações somente leitura por padrão e nenhum acesso a `app`.
    Coberto por `backend/tests/test_agent_role.py`.
  - O backend usa o usuário `venergy`, que lê e escreve.
  - Os testes rodam no banco `venergy_test`, no mesmo container, e nunca tocam
    os dados de desenvolvimento.
  - O banco escuta só em `127.0.0.1`, na porta 5433 por padrão, para não colidir
    com um PostgreSQL já instalado. As URLs usam `127.0.0.1`, e não `localhost`:
    no Windows, `localhost` tenta IPv6 primeiro e a conexão fica pendurada.

## DEC-003 · Walking skeleton com amostra sintética

- **Data:** 19/10/2026 · **Área:** Todas · **Autor:** Time
- **Decisão:** o time constrói primeiro a menor versão do sistema que funciona de
  ponta a ponta (Gold → banco → API → tela → agente) e depois evolui cada camada.
  Enquanto a Gold não existe, o backend usa uma amostra sintética gerada por
  `uv run python -m venergy_api.amostra`: 8 unidades consumidoras com valores
  inventados, nenhum vindo do dataset.
- **Motivo:** os problemas mais caros estão na integração entre camadas (formato
  da Gold, CORS, entrada do agente no FastAPI), e o prazo não permite
  descobri-los só na semana da entrega. A amostra também permite que qualquer
  pessoa, inclusive a banca, rode o sistema sem o dataset confidencial.
- **Regras:** a amostra é montada pelo mesmo schema que valida a Gold, então
  não pode sair do contrato. O gerador nunca sobrescreve um CSV existente sem
  `--force`, para não trocar a Gold real por dados inventados.

## DEC-004 · Entrega da Gold em `data/gold/` (proposta)

- **Data:** 19/10/2026 · **Área:** Portal e Dados · **Autor:** Felipe
- **Status:** proposta do Portal, a validar com o time de Dados no card
  "Contrato da Gold".
- **Decisão:** a Gold chega ao banco local como CSV, um arquivo por tabela com o
  nome da tabela (`gold_dim_uc.csv`), em UTF-8, separado por vírgula, com
  cabeçalho e booleanos como `true`/`false`. Os arquivos ficam em `data/gold/`,
  fora do Git, e são carregados no schema `gold` do banco por
  `uv run python -m venergy_api.carga`.
- **Motivo:** amostra e Gold real percorrem o mesmo caminho, então trocar uma
  pela outra não muda código.
- **Regras:** a carga valida todas as linhas contra o contrato
  (`backend/src/venergy_api/schemas.py`) antes de gravar e substitui as tabelas
  numa única transação. Um arquivo fora do contrato cancela a carga e mantém os
  dados anteriores. Nem os dados brutos nem os CSVs da Gold são versionados.
- **Célula vazia (20/10/2026):** célula vazia no CSV é nulo, nunca zero ou texto
  vazio, como no rascunho do contrato da Gold (PR #10). Zero é um fato ("não
  consumiu", "não pagou"); vazio é falta de informação, e tratar um como o outro
  levaria uma unidade consumidora inocente para a fila de perdas. Em coluna
  obrigatória, a célula vazia cancela a carga.
- **Em aberto:** confirmar com a organização se a Gold agregada pode ir para o
  repositório público. Até lá, não é versionada.

## DEC-005 · Contrato OpenAPI entre API e frontend

- **Data:** 19/10/2026 · **Área:** Portal · **Autor:** João Euclides
- **Decisão:** o OpenAPI que o FastAPI gera das rotas e schemas é exportado para
  `contracts/openapi.json` (`uv run python -m venergy_api.openapi`) e versionado. O
  frontend gera dele os tipos (`npm run gen:api` → `src/lib/api-schema.gen.ts`, com
  `openapi-typescript`) e chama a API pelo client tipado `api` de `src/lib/api.ts`
  (`openapi-fetch`).
- **Motivo:** rota, parâmetro ou campo renomeado no backend vira erro de compilação
  no frontend, e não tela quebrada em produção. Com o arquivo versionado, o front gera
  os tipos sem subir a API, e o revisor vê a mudança de contrato no PR.
- **Alternativa descartada:** `@hey-api/openapi-ts`, que gera funções e hooks do
  TanStack Query, mas nomeia as funções pelo `operationId` (o FastAPI gera
  `get_unidade_consumidora_unidades_consumidoras__cod_uc__get`) e gera código de
  runtime. O `openapi-fetch` só tipa pela rota e pesa cerca de 6 kB.
- **Regras:**
  - Rotas declaram em `responses=` os erros que devolvem (ex.: `404` com
    `ErroSchema`), para o erro também chegar tipado.
  - Arquivos gerados não são editados à mão. O pre-commit e o CI regeneram os dois e
    falham se o resultado não estiver commitado.
  - O `openapi-typescript` declara suporte só ao TypeScript 5; o `overrides` do
    `package.json` o faz usar o TypeScript 6 do projeto. Rever quando sair versão
    compatível.

## DEC-006 · Ambiente de desenvolvimento em Docker

- **Data:** 19/10/2026 · **Área:** Portal · **Autor:** João Euclides
- **Decisão:** o `docker-compose.yml` da raiz sobe `db` (PostgreSQL), `api`
  (uvicorn com `--reload`) e `web` (Vite), com o código montado da máquina para
  recarregar a cada mudança. Quem prefere rodar API e frontend fora do Docker sobe só
  o banco: `docker compose up -d --wait db`.
- **Motivo:** história V2-12 ("subir banco, backend e frontend com um comando"),
  inclusive para quem é de Dados ou IA e não tem Python e Node configurados. Deploy em
  nuvem é Won't no planejamento, então não há imagem de produção (build estático,
  nginx).
- **Regras:**
  - O navegador fala só com o Vite, que encaminha `/api/*` para o serviço `api`:
    sem CORS, igual ao desenvolvimento fora do Docker.
  - Portas só em `127.0.0.1`, configuráveis no `.env` da raiz (`API_PORT`,
    `WEB_PORT`, `POSTGRES_PORT`).
  - Os containers rodam sem root (UID 1000). Só `src/` de cada serviço é montado da
    máquina: dependências (`.venv`, `node_modules`) são as da imagem, com binários para
    Linux, e mudança em `pyproject.toml`, `package.json` ou `vite.config.ts` pede
    `docker compose up -d --build`. Montar a pasta inteira exigiria um volume para o
    `node_modules`, que o Docker cria como root na máquina e quebra o `npm ci` local.
  - A detecção de mudanças usa varredura (`WATCHFILES_FORCE_POLLING`,
    `CHOKIDAR_USEPOLLING`), porque eventos de arquivo não atravessam o volume no
    Docker Desktop do Windows.

## DEC-007 · Hooks de pre-commit e CI

- **Data:** 19/10/2026 · **Área:** Todas · **Autor:** João Euclides
- **Decisão:** `.pre-commit-config.yaml` na raiz, instalado com
  `uvx pre-commit install`, e um workflow do GitHub Actions (`.github/workflows/ci.yml`)
  que roda os mesmos hooks, o pytest do backend, a checagem de tipos e o build do
  frontend e o build das imagens Docker em todo PR.
- **Hooks:** higiene de arquivos (espaços, fim de linha LF, YAML/TOML/JSON válidos,
  conflitos, arquivos grandes, chaves privadas), gitleaks (segredos), ruff (Python),
  Biome (frontend) e o contrato OpenAPI (DEC-005). Mensagens de commit não são
  validadas por hook: o padrão Conventional Commits segue como convenção do time.
- **Motivo:** o `pre-commit` gerencia hooks de Python, Node e binários num lugar só;
  o husky só atende Node. O hook pode ser pulado com `--no-verify`, então o CI é o
  portão que vale.
- **Regras:**
  - Biome e geradores do contrato rodam com as versões do projeto (`npm ci` em
    `frontend/`, `uv` no backend). O ruff do hook tem a mesma versão do
    `backend/uv.lock`; ao atualizar um, atualize o outro.
  - O ruff roda só em `.py`: notebooks do Databricks usam `spark` e `dbutils` sem
    import, e os blocos de código dos `.md` não devem ser reformatados.
  - Nenhum hook modifica notebooks (`.ipynb`): eles são editados e versionados pelo
    Databricks, e reescrevê-los localmente (saídas, fim de arquivo) geraria conflito na
    sincronização. Por isso não há nbstripout; limpar as saídas antes do commit é
    responsabilidade de quem exporta. Hooks só de checagem (JSON válido, segredos)
    continuam valendo para eles.
  - `.gitattributes` força LF em todo arquivo de texto, menos nos notebooks;
    `.editorconfig` alinha os editores com os formatadores.

## DEC-008 · Contrato da Bronze (auditoria básica)

- **Data:** 19/10/2026 · **Área:** Dados · **Autor:** Alisson
- **Decisão:** cada fonte lógica gera ao menos uma tabela Delta em
  `v_energy.bronze.<fonte>`, com o nome em snake_case e sem prefixo (ex.:
  `unidades_consumidoras`). Uma fonte pode gerar mais de uma tabela quando seus
  componentes têm estruturas próprias: `inspecoes.xlsx` gera uma tabela por aba
  (`inspecoes_ago_set`, `inspecoes_out_nov` e `inspecoes_dez`), e `leituras/` reúne
  seus arquivos anuais em uma só.
  Colunas originais, com os nomes originais e do tipo string, mais
  `source_file` (de `_metadata.file_path`) e `ingestion_timestamp`.
- **Carga:** batch, full refresh, `overwrite` do Delta com um único overwrite por
  tabela. Reexecutar sobre os mesmos arquivos não duplica nem perde linhas.
- **Execução:** um único notebook com uma seção por fonte; `Run All` processa todas em
  sequência. O widget `gravar` (padrão `nao`) é o único interruptor de escrita: sem ele,
  o notebook só valida e confere tabelas existentes. Uma fonte com falha é marcada e não
  é gravada, e o resumo final falha se houver fonte com falha, pendente ou sem
  idempotência comprovada. As opções de leitura ficam no código da fonte, versionadas,
  e são impressas a cada execução.
- **Formatos:** CSV com `FAILFAST` e tudo string. Uma pasta com vários CSVs (`leituras/`)
  vira uma tabela só se todos os arquivos tiverem o mesmo conjunto de colunas, unidos por
  nome. JSON preserva structs e arrays, com valores primitivos como string
  (`primitivesAsString`), conferido contra uma releitura independente do arquivo. XLSX é
  lido com o leitor nativo `format("excel")` do Databricks, uma tabela por aba, e conferido
  célula a célula contra a leitura do XML da planilha; divergência reprova a aba.
- **Sem:** limpeza, deduplicação, tipagem, regras de negócio, `ingestion_log`,
  snapshots ou histórico próprio. Isso fica para a Silver.
- **Validação antes de gravar:** o arquivo existe, o cabeçalho foi lido sem
  ambiguidade, a leitura usa `FAILFAST` (linha malformada interrompe a carga) e
  `source_file` está consistente. Se algo falhar, a tabela anterior não é tocada.
- **Histórico:** o `DESCRIBE HISTORY` e o time travel do Delta são recursos
  complementares, com retenção limitada (log de 30 dias e `VACUUM` de 7 dias por
  padrão). Não são a trilha permanente de auditoria.
- **Limitações conhecidas:** o Spark lê campo vazio sem aspas como `NULL`, então
  "vazio" e "nulo" não se distinguem na Bronze. A contagem de linhas físicas é só
  uma conferência auxiliar, porque campos entre aspas podem conter quebras de
  linha.
- **Evidências:** os resultados da validação (contagens, colunas, estatísticas) são
  documentados à parte, em relatório privado fora do repositório, porque o dataset é
  confidencial. Não há tabelas adicionais de auditoria, e os notebooks são
  versionados sem outputs.

## DEC-009 · Modelo das ordens de inspeção

- **Data:** 20/10/2026 · **Área:** Portal · **Autor:** Felipe
- **Contexto:** o gerente de perdas gera ordens de inspeção (OIs) a partir da fila de
  suspeitas, acompanha o status, registra o resultado de campo e cancela as que deixam
  de fazer sentido. É o único dado do sistema digitado no portal.
- **Decisão:** duas tabelas no schema `app`: `ordem_inspecao` (uma linha por OI) e
  `ordem_evento` (uma linha por mudança de status, com status anterior, novo, horário e
  observação). Rotas em `/ordens-inspecao`: `POST` (lote), `GET` (lista e detalhe) e
  `PATCH` (mudança de status, inclusive cancelar).
- **Regras:**
  - Status `GERADA → EM_CAMPO → CONCLUIDA`, ou `CANCELADA` a partir dos dois primeiros.
    `CONCLUIDA` e `CANCELADA` são finais: para voltar ao imóvel, gera-se uma OI nova e o
    histórico mostra as duas visitas. Transição fora do mapa devolve `409`. A regra fica
    num módulo sem banco (`backend/src/venergy_api/ordens.py`), testado à parte.
  - Concluir exige resultado (`IRREGULAR_CONFIRMADA`, `REGULAR` ou `NAO_REALIZADA`), e
    só a conclusão aceita resultado; o contrário devolve `422`. `NAO_REALIZADA` é a
    equipe que foi e não conseguiu vistoriar; cancelar é a visita que deixou de ser
    necessária. Separar os dois mostra quantos dias de campo se perdem por falta de acesso.
  - No máximo uma OI ativa (`GERADA` ou `EM_CAMPO`) por UC, garantida por índice único
    parcial no banco, e não só por checagem no Python, que deixaria passar duas
    requisições simultâneas. A API checa antes para devolver um `409` que cita as UCs.
  - A geração em lote é tudo ou nada: uma UC inexistente (`404`) ou já com OI ativa
    (`409`) cancela o lote inteiro.
  - O `PATCH` trava a linha da OI (`SELECT ... FOR UPDATE`) até o commit, para que duas
    mudanças simultâneas não passem as duas pela validação do status atual.
  - `DELETE` não existe nem é liberado no CORS: OI se cancela, não se apaga.
- **Por que sem FK para `gold.gold_dim_uc`:** a carga da Gold apaga e reinsere as UCs a
  cada execução. Com FK, a carga falharia (FK simples) ou apagaria as OIs junto
  (`ON DELETE CASCADE`). A existência da UC é validada pela API na criação, e a OI
  continua como histórico mesmo se a UC sair da Gold depois.
- **Status e resultado como VARCHAR com CHECK**, e não como ENUM nativo do Postgres: sem
  ferramenta de migração, acrescentar um valor a um ENUM nativo exige `ALTER TYPE` manual.
- **Criação das tabelas:** pelo `create_all` que a carga da Gold já executa
  (`uv run python -m venergy_api.carga`); o `DELETE` da carga só passa pelas tabelas da
  Gold. Criar no startup da API foi descartado porque derrubaria a API com o banco fora
  do ar, quando o esperado é o `/health` responder `503`. Alembic foi descartado por ser
  desproporcional a duas tabelas, a duas semanas da entrega.
- **Alternativas descartadas:** endpoints de ação (`/cancelar`, `/concluir`), que
  multiplicam rotas e espalham a validação; e paginação na listagem, desnecessária
  para a escala de cerca de 200 inspeções por mês.
- **Limitações:** a OI valida a UC contra `gold_dim_uc`, porque a fila de suspeitas
  (`gold_fila_suspeitas`) ainda não existe; quando existir, a tela da fila só passa a
  enviar os `cod_uc` escolhidos, sem mudança no backend. Não há registro de quem fez
  cada mudança, porque o portal ainda não tem login. Alterar colunas exige recriar as
  tabelas do `app`, já que não há migrações.

## DEC-010 · Energia e dinheiro como `numeric`, número na API

- **Data:** 20/10/2026 · **Área:** Portal · **Autor:** Felipe
- **Contexto:** o rascunho do contrato da Gold (PR #10) define energia como
  `numeric(16,3)` e dinheiro como `numeric(14,2)`; o backend gravava
  `consumo_medio_kwh_12m` como `float`.
- **Decisão:** no banco, `numeric` com a escala do contrato; na carga, `Decimal`; no JSON
  da API, número. O tipo `ExactNumber` (`backend/src/venergy_api/schemas.py`) faz a
  conversão só na saída e serve às próximas colunas de energia e dinheiro.
- **Motivo:** o agente de IA lê o banco direto e soma em SQL. Com `numeric`, somas sobre
  muitas linhas não acumulam resíduo nas casas decimais. Para exibir um valor por tela,
  a precisão de um número no JSON sobra.
- **Alcance:** isso evita ruído nas últimas casas, não diferenças de definição. Portal e
  agente mostram o mesmo número porque o cálculo é feito uma vez, na Gold, e os dois leem
  a mesma tabela (decisão de 19/10 sobre cálculos de negócio).
- **Alternativas descartadas:** `Decimal` também no JSON, que chega ao frontend como texto
  (`"152.400"`) e obrigaria toda tela a converter; e manter `float`, mudando o contrato,
  que levaria o resíduo de arredondamento para as somas do agente.
- **Limitações:** o `minimum: 0` some da documentação da resposta no OpenAPI, embora a
  carga continue recusando valor negativo. Sem migrações, um banco de desenvolvimento
  criado antes desta mudança mantém a coluna em `double precision` até a tabela ser
  recriada: `docker compose exec db psql -U venergy -d venergy -c "DROP TABLE
  gold.gold_dim_uc"` e, depois, a carga da Gold. Só a tabela da Gold é derrubada, e as
  ordens de inspeção do schema `app` ficam intactas.

## DEC-015 · Gold real e plano gratuito do Gemini (proposta)

- **Data:** 21/10/2026 · **Área:** GenAI e Dados · **Autor:** GenAI
- **Status:** proposta, a decidir na daily.
- **Decisão proposta:** o plano gratuito do Gemini (Free Tier) recebe só a amostra sintética. A Gold real só é enviada com chave paga ou fornecida pela organização.
- **Motivo:** no Free Tier, o Google pode usar o conteúdo enviado para melhorar os produtos dele. O dataset é confidencial e nunca vai para o repositório.
- **Estado atual:** o README orienta o uso do plano gratuito só para a amostra. O código ainda não verifica o tipo de chave, e o modelo padrão do quickstart é o Gemini direto, então nada impede quem segue o README de enviar a Gold real pelo plano gratuito.
- **Em aberto:** (1) confirmar se a Gold agregada entra no mesmo critério do dataset; (2) definir quem fornece a chave paga; (3) decidir se o código recusa a chave gratuita quando a configuração aponta para a Gold real.

## DEC-016 · Exceção de versionamento do prompt v1 (proposta)

- **Data:** 21/10/2026 · **Área:** GenAI · **Autor:** GenAI
- **Status:** proposta, a confirmar com o time.
- **Decisão proposta:** a `prompts/v1/` recebe a delimitação do SQL anterior e das linhas de exemplo (system.md e correction.md) sem virar `prompts/v2/`. Isso vale só para esta mudança, feita antes de a v1 chegar à `main`.
- **Motivo:** o `ai-agent/CLAUDE.md` pede uma versão nova para cada mudança de prompt, que só entra com golden set sem regressão. Hoje a v1 não está na `main` e o golden set ainda não foi executado com dados. Criar a v2 agora mudaria o `prompt_version` de auditoria sem ganho real.
- **Consequência:** o `prompt_version='v1'` gravado na auditoria passa a cobrir os dois prompts de correção. Quem olhar uma resposta antiga precisa saber que ela foi gerada antes da delimitação.
- **Em aberto:** (1) aceitar a exceção ou exigir a v2 antes do merge; (2) a partir de quando o golden set roda como portão para mudanças de prompt. Depois do primeiro merge na `main`, qualquer mudança de prompt vai para `prompts/v2/`.
