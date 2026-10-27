# Decisões e suposições

Registro das decisões tomadas pelo time onde os requisitos do case não eram explícitos. Alimenta a seção de suposições do README.

| Data | Decisão | Motivo | Quem |
|---|---|---|---|
| 19/10/2026 | DEC-001: arquivos de origem em `v_energy.default.landing`; `bronze` só com tabelas | Separa arquivos imutáveis de tabelas recriáveis | Arthur |
| 19/10/2026 | Frontend com TanStack Start em modo SPA (React + TypeScript + Vite) | O gerador já integra Router, Query, Form, Table, devtools e React Compiler; SSR desligado porque o FastAPI é o único backend | João Euclides |
| 19/10/2026 | Autenticação e perfis ficam no FastAPI; better-auth removido do frontend | Pensei em usar BetterAuth, porém, permissão precisa ser checada onde estão os dados, melhor evitar um segundo backend em Node com sessões que o FastAPI não valida | João Euclides |
| 19/10/2026 | Em dev, o Vite encaminha `/api/*` para o FastAPI removendo o prefixo; base da API configurável por `VITE_API_URL` | Evita CORS no desenvolvimento e não exige prefixo `/api` nas rotas do backend; endereço do backend ainda não definido | João Euclides |
| 19/10/2026 | Frontend em camadas por feature (`features/<feature>` com `api.ts`, `hooks`, `pages`; `routes/` só define rotas) | Times e agentes seguem a mesma organização; regras em `frontend/README.md` e `frontend/CLAUDE.md` | João Euclides |
| 19/10/2026 | Cálculos de negócio (DEC/FEC, efeito-preço × efeito-volume) ficam na camada Gold/backend; o frontend só exibe | Uma única fonte dos números para portal e agente de IA | João Euclides |
| 19/10/2026 | Valores exibidos (R$, kWh, %, competência, datas) formatados só por `frontend/src/lib/format.ts` | Mesmo número com o mesmo formato em todas as telas | João Euclides |
| 19/10/2026 | DEC-002: banco local PostgreSQL em Docker, com schemas `gold` e `app` | Usuário somente leitura nativo para o agente; recarga da Gold não apaga as ordens de inspeção | Time |
| 19/10/2026 | DEC-003: walking skeleton com amostra sintética da Gold | Integração entre camadas testada desde o início, sem depender do dataset confidencial | Time |
| 19/10/2026 | DEC-004: Gold entregue em CSV, um arquivo por tabela, em `data/gold/` | Um único caminho de carga, validado contra o contrato, para amostra e Gold real | Felipe |
| 19/10/2026 | DEC-005: contrato API → frontend em `contracts/openapi.json`, gerado pelo FastAPI; client com `openapi-typescript` + `openapi-fetch` | O front quebra na compilação quando o contrato muda; a mudança de contrato aparece no diff do PR | João Euclides |
| 19/10/2026 | DEC-006: `docker compose up` sobe banco, API e Vite em modo de desenvolvimento | Um comando roda o portal em qualquer máquina; deploy em nuvem está fora do escopo | João Euclides |
| 19/10/2026 | DEC-007: qualidade garantida por pre-commit local e pelo mesmo conjunto de checagens no CI | Código formatado e contrato em dia sem depender de lembrar; o CI barra quem pula o hook | João Euclides |
| 19/10/2026 | DEC-008: Bronze com auditoria básica (full refresh, tudo string, `ingestion_timestamp` e `source_file`) | Dados o mais próximos da origem; rastreabilidade sem log próprio de ingestão | Alisson |
| 20/10/2026 | DEC-009: ordens de inspeção em `app.ordem_inspecao` + `app.ordem_evento`, sem FK para a Gold, com máquina de estados e no máximo uma OI ativa por UC | O trabalho de campo sobrevive a cada recarga da Gold; o resultado registrado mede se a fila de suspeitas acerta | Felipe |
| 20/10/2026 | DEC-010: energia e dinheiro como `numeric` no banco e número no JSON da API | Somas em SQL sem resíduo de arredondamento; o frontend recebe número, sem converter texto | Felipe |
| 20/10/2026 | DEC-011: contrato da Gold com `competencia` em texto (`AAAA-MM`) e três cópias independentes de Silver → Gold | Texto preserva o formato em CSV e em todas as camadas; três cópias comparadas dão uma Gold mais sólida | Alisson |
| 21/10/2026 | DEC-012: tokens do frontend vêm do design system da marca VE-360 (paleta OKLCH a partir de #f2c94c, neutros `graphite`, Inter Tight + Söhne Breit + JetBrains Mono); escalas padrão do Tailwind removidas | Uma única fonte de cor, tipo, raio e sombra; utilitário fora do sistema não gera CSS | João Euclides |
| 21/10/2026 | DEC-013: componentes base trazidos do shadcn/ui no estilo `base-nova` (Base UI) e do interior.dev para `frontend/src/components/ui/`, adaptados aos tokens; nenhuma biblioteca de componentes como dependência | O código fica no repositório e segue os tokens da marca; uma única base de primitivas (Base UI, sem Radix) | João Euclides |
| 21/10/2026 | DEC-014: o backend espelha o contrato da Gold (6 de 9 tabelas), conferido por teste no CI; a carga recria as tabelas da Gold | Divergência entre contrato e backend aparece no CI, e não na carga da Gold real; coluna nova no contrato entra sem apagar tabela à mão | Felipe |
| 21/10/2026 | DEC-015 (proposta): o plano gratuito do Gemini recebe só a amostra sintética; a Gold real só vai com chave paga ou fornecida pela organização | No Free Tier o Google pode usar o conteúdo enviado, e o dataset é confidencial | GenAI |
| 21/10/2026 | DEC-016 (proposta): a `prompts/v1/` recebe a delimitação do SQL anterior e das linhas de exemplo sem virar `prompts/v2/`, só nesta mudança, antes de a v1 chegar à `main` | O golden set ainda não rodou com dados; criar a v2 mudaria o `prompt_version` da auditoria sem ganho real | GenAI |
| 22/10/2026 | DEC-017: backend e agente formam um workspace do uv, com um único `uv.lock` na raiz | Com o `/ai`, a API instala o agente; uma resolução só garante que o que é testado é o que roda | Luis Felipe |
| 22/10/2026 | DEC-018: a camada semântica monta relações entre views só pelas chaves estrangeiras do contrato e pelas chaves de entidade (`cod_uc`, `cod_alimentador`) | Juntar views só pelo período gera produto cartesiano | Lucas |
| 22/10/2026 | DEC-019 (reservada): verificação numérica da narrativa do agente, registrada no PR #36 | Número já citado na spec e em `ai-agent/docs/architecture.md`; a seção entra com o PR | Lucas |
| 22/10/2026 | DEC-020: o `AgentAnswer` ganha `status` (`answered`, `unknown`, `clarify`, `refused`, `failed`), `truncated`, `refused_reason`, `model` e `latency_ms`, com invariantes por status | O portal distingue resposta, "não sei", esclarecimento e falha; a auditoria guarda modelo e latência | Lucas |
| 22/10/2026 | DEC-021: com filtro de município, bairro ou classe, a receita e o kWh são somados no backend a partir da fato e do cadastro; DEC e FEC ficam no total da empresa e por alimentador | Receita e kWh se somam; somar DEC de alimentadores por bairro daria um número errado | Felipe |
| 21/10/2026 | DEC-022: o agente só lê colunas não sensíveis das tabelas liberadas no contrato, e "receita" sem qualificador é a receita faturada | Dado pessoal e texto livre ficam fora do agente; uma definição única de receita evita respostas divergentes | Alisson |
| 22/10/2026 | DEC-023: receita da Gold em três medidas (total, energia e tributos), com a energia como base provisória do PVM; consumo médio nulo sem leitura; `potencia_kwp`; reconciliação do faturamento e da energia | Nenhum valor descartado sem explicação; os números da diretoria podem ser conciliados com os da Gold | Alisson |
| 22/10/2026 | DEC-024: resultados agregados necessários para sustentar uma hipótese podem ir ao repositório; identificação de pessoas e de UCs e dado de LGPD ficam mascarados; linha a linha, amostras e outputs nunca sobem | O diagnóstico precisa mostrar a evidência, mas o dataset é confidencial e há dado pessoal | Alisson |
| 23/10/2026 | DEC-025 (proposta): mapa da RMR com a malha municipal 2025 e a malha de bairros do Censo 2022 do IBGE, os 15 municípios da LC estadual 382/2018, e município e bairro da Gold casados com os do mapa pelo nome normalizado | O mapa vira o seletor principal de município e bairro sem mudar o contrato da Gold; o que está na Gold é clicável, o resto aparece apagado | João Euclides |
| 23/10/2026 | DEC-026: ações das OIs na tela de perdas (enviar a campo, concluir, cancelar, histórico, gerar) com Kanban das ativas e troca Kanban ⇄ tabela lembrada no navegador | O gerente acompanha e move as OIs sem sair da tela; o backend continua sendo o dono da máquina de estados | João Euclides |
| 24/10/2026 | DEC-027: contrato da Gold v0.3: tabelas da UC 360 com colunas e chave, `gold_inspecoes_uc`, GD e ligação na dimensão, leitura, medidor e bandeira no fato, alimentador e tipo de medidor na chave dos recortes, componentes de faturas e leituras | Responder a UC 360, as hipóteses H1, H2 e H5 e filtrar qualquer período por alimentador, medidor e inadimplência | Alisson |
| 24/10/2026 | DEC-028: a decomposição grava todos os pares de mesmos meses em anos diferentes; pares de trechos diferentes ficam para o backend, se necessário | Gravar todas as combinações passaria de 1 bilhão de linhas; os totais de qualquer período já saem da soma dos meses | Alisson |
| 24/10/2026 | DEC-029: método do efeito bandeira: acréscimo fixo por kWh por bandeira, conferido no dado | Fecha a pendência da DEC-023 com uma regra verificável e exata | Alisson |
| 24/10/2026 | DEC-030: regras aplicadas na Gold: `n_uc` de UCs faturadas (PRODIST), ocorrências antes da ligação fora (OCO-04), potência em Wp convertida, vazio × zero nos recortes, fila de suspeitas calibrada e medida na data das inspeções | Denominador do DEC/FEC como no PRODIST e fila explicável e medida; revisada com a comparação das cópias | Alisson |
| 26/10/2026 | DEC-031: a API lista os pares de períodos da decomposição e passa a exigir o par; API 0.5.0 | A Gold grava centenas de pares (DEC-028): sem o par, a resposta somaria períodos que não se comparam, e o seletor precisa saber quais existem | Felipe |
| 24/10/2026 | DEC-032 (proposta): DEC e FEC de um período de vários meses somam os valores mensais, nunca a média | Indicador de continuidade é acumulado; a média dos meses subestima o período e o agente alternava entre as duas formas | Luis Felipe |
| 26/10/2026 | DEC-033: DEC e FEC de um período saem da soma dos componentes ÷ média mensal de UCs, no backend, com rotas por alimentador, ranking e recortes; fila de suspeitas paginada com a ordem de inspeção ativa; API 0.6.0 | DEC e FEC não se somam nem se tiram a média entre recortes; a fila mostra quais UCs já têm ordem, para a tela não oferecer o que daria 409 | Felipe |

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

## DEC-004 · Entrega da Gold em `data/gold/`

- **Data:** 19/10/2026 · **Área:** Portal e Dados · **Autor:** Felipe
- **Status:** adotada. Proposta do Portal, confirmada pelo time de Dados na revisão do contrato da Gold
  (PR #10), com o formato de CSV acima.
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
- **Gold agregada no repositório:** os CSVs da Gold continuam fora do Git. O agregado necessário
  para sustentar uma hipótese do diagnóstico pode ir em texto, como a [DEC-024](#dec-024--o-que-pode-subir-ao-repositório-público) define.

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
  - A imagem da API é construída com contexto na raiz e instala o agente de IA pelo
    workspace do uv (DEC-017); o compose monta `backend/src` e `ai-agent/src`.

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
    `uv.lock` da raiz (DEC-017); ao atualizar um, atualize o outro.
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
  versionados sem outputs. A [DEC-024](#dec-024--o-que-pode-subir-ao-repositório-público) substitui
  em parte esta regra: o agregado necessário a uma hipótese pode subir; identificação e dado de
  LGPD ficam mascarados; linhas, amostras e outputs nunca sobem.

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
- **Atualização (21/10/2026):** desde a DEC-014, a própria carga recria as tabelas da Gold,
  e o `DROP TABLE` manual deixou de ser necessário.

## DEC-011 · Convenções do contrato da Gold

- **Data:** 20/10/2026 · **Área:** Dados, Portal e IA · **Autor:** Alisson
- **Contexto:** `contracts/gold_schema.yaml` (v0.1) é a fonte de verdade sobre tabelas e
  colunas da Gold. Web e GenAI trabalham contra ele; os tipos são os do PostgreSQL (DEC-002).
- **Decisão:**
  - `competencia` é texto no formato `AAAA-MM`, em todas as tabelas e no CSV.
  - Energia e dinheiro seguem a DEC-010: `numeric` no banco, com a escala do contrato.
  - Dados faz três cópias independentes da transformação Silver → Gold (Alisson, Arthur e
    Gabriel), todas contra o contrato, e as compara antes de definir a Gold exportada.
    Não há ordem nem dono único: cada um faz a sua versão por conta própria, e o time compara os
    pontos fortes e fracos de cada uma para montar uma versão final mais concisa.
- **Motivo:** o formato texto não depende de interpretação de data entre CSV, Delta e
  PostgreSQL; comparar três cópias independentes expõe erro de tratamento que uma só
  não mostraria.
- **Regras relacionadas** (detalhes no contrato): chaves estrangeiras são lógicas, checadas
  no Data Quality e sem constraint no banco; colunas de lista vão numa célula do CSV,
  separadas por `;`; `tarifa_media` é nula quando `kwh_faturado = 0`.

## DEC-014 · O backend espelha o contrato da Gold

- **Data:** 21/10/2026 · **Área:** Portal · **Autor:** Felipe
- **Contexto:** o contrato da Gold (`contracts/gold_schema.yaml`, v0.1.0, PR #10) tem 9
  tabelas, e o backend só modelava a `gold_dim_uc`. Sem as outras, não havia como fazer
  os endpoints de KPIs, receita, DEC/FEC e fila de suspeitas.
- **Decisão:**
  - O backend implementa toda coluna do contrato com o nome, o tipo, a nulidade e a chave
    do YAML, inclusive as marcadas `a_confirmar`. O teste
    `backend/tests/test_contrato_gold.py` roda no CI e compara o YAML com os modelos (nome,
    tipo no banco, nulidade e chave) e com os schemas da carga (nome, tipo Python, nulidade
    e valores permitidos).
  - Entram 6 das 9 tabelas. `gold_interrupcoes_uc`, `gold_atendimentos_uc` e
    `gold_medidor_uc` ficam de fora enquanto a chave estiver `a_confirmar` no contrato
    (dependem da Silver); o mesmo teste falha quando o contrato definir a chave de uma delas.
  - A carga recria as tabelas da Gold (`DROP` e `CREATE`) na mesma transação em que grava
    os dados, em vez de só apagar as linhas. O schema `app` não é tocado. O `DROP` é sem
    `CASCADE`, de propósito: um objeto que dependa de uma tabela da Gold e que ninguém
    previu faz a carga falhar sem alterar nada, em vez de sumir em silêncio. As views
    `sem_*` do agente são tratadas à parte (atualização de 23/10/2026, abaixo).
  - Colunas `text[]` do contrato viram `ARRAY(Text)` no banco; no CSV, os itens vão numa
    célula só, separados por `;`, e a carga recusa item vazio.
  - Mudança no contrato e no backend entram no mesmo PR: quem muda o YAML recebe, no próprio
    PR, o commit que ajusta o backend. Assim a `main` nunca fica com o teste do contrato
    vermelho, nem com contrato e backend dizendo coisas diferentes.
- **Motivo:** quando o time de dados muda o contrato, o CI aponta o que o backend precisa
  acompanhar, antes de a Gold real falhar na carga. Sem migrações, o `create_all` não
  acrescenta coluna em tabela existente; recriar a Gold, que é recarregável, faz a coluna
  nova entrar na próxima carga. A permissão de leitura do agente vem do `ALTER DEFAULT
  PRIVILEGES` do schema `gold` e vale para a tabela recriada (testado em
  `backend/tests/test_agent_role.py`).
- **Atualização (23/10/2026, D7 da spec do agente):** a carga passou a recriar as views
  `sem_*`, na mesma transação, com o usuário dono:
  - antes do `drop_all`, apaga toda view `sem_*` do schema `gold` **lendo o catálogo do
    banco** (`pg_views`), e não a lista de nomes do `ai-agent/semantic/views.sql`: uma view
    que o GenAI renomeou ou tirou do arquivo continuaria presa à tabela e quebraria a carga;
  - depois do `create_all` e dos `INSERT`, executa o `views.sql` inteiro;
  - se o arquivo citar coluna ou tabela que a Gold não tem mais, a carga é cancelada com
    "as views do agente não batem com a Gold" e nada muda (Gold e views anteriores
    ficam). Ignorar a view quebrada deixaria o agente sem consulta, sem aviso;
  - arquivo ausente cancela a carga antes de tocar no banco;
  - o `views.sql` é lido por caminho fixo a partir da raiz do repositório, sem variável
    de ambiente, e o backend não importa nada de `venergy_agent`.
  - Alternativa descartada: `DROP ... CASCADE`, que apagaria as views em silêncio.
  - Testes: `test_carga.py` (views criadas, recarga com views no lugar, view antiga
    removida, views incompatíveis) e `test_agent_role.py` (o agente lê e não escreve
    pelas views depois da recarga).
- **Alternativas descartadas:** gerar os modelos a partir do YAML, difícil de revisar e de
  explicar; Alembic para a Gold, que seria migração para um dado descartável; modelar as 3
  tabelas pendentes com colunas inventadas; implementar só as colunas `confirmada` e
  `proposta`, que tiraria da `gold_receita_decomposicao` colunas da chave e da conta; e
  `TRUNCATE` + insert em vez de recriar as tabelas (sugerido na revisão do PR #17), que
  preservaria as views, mas voltaria a exigir apagar tabela à mão a cada coluna nova.
- **Confirmado com Dados** (revisão do PR #17, 21/10/2026; entra no contrato v0.2):
  - `horas_interrompidas` é a soma das durações das ocorrências das UCs do alimentador no
    mês, em UC·h; `n_interrupcoes` é o número de ocorrências; `n_uc` são as UCs atendidas
    pelo alimentador (cadastro), e não só as afetadas. Ocorrência que vira o mês entra no
    mês da abertura. DEC e FEC da empresa são os totais sobre o total de UCs atendidas,
    como na amostra.
  - A checagem `efeito_preco + efeito_volume + efeito_mix = receita_atual - receita_base`
    tem tolerância absoluta de R$ 0,02 por linha (só o arredondamento dos três efeitos):
    porcentagem não serve quando a variação é perto de zero. A checagem é do Data Quality,
    e não da carga. Na Gold real o mix é calculado, e não resíduo.
  - `score_suspeita` passa a ser a posição no ranking (inteiro, 1 = mais suspeita), e não
    uma nota de 0 a 1 (decidido na daily de 21/10). Primeiro caso da regra do mesmo PR:
    o ajuste do backend vai no PR da v0.2.
- **Limitações e pendências:**
  - A amostra (`backend/src/venergy_api/amostra.py`) usa fórmulas sintéticas. Nela, os KPIs
    são a soma do faturamento (conferido em teste, depois da carga) e o `efeito_mix` é o
    resíduo do arredondamento, porque cada segmento tem uma UC; a fórmula oficial da
    decomposição é do Diagnóstico.
  - O agente lê todas as tabelas do schema `gold`, inclusive `gold_fila_suspeitas`. O
    roadmap v0.2 do contrato prevê tirá-la do agente por padrão; como (views `sem_*`) está
    em aberto com GenAI.

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

## DEC-017 · Workspace do uv com um único `uv.lock`

- **Data:** 22/10/2026 · **Área:** Portal e GenAI · **Autor:** Luis Felipe (decidido na daily de 21/10; issue #18)
- **Decisão:** `pyproject.toml` na raiz com `[tool.uv.workspace] members = ["backend", "ai-agent"]`,
  um único `uv.lock` e uma única `.venv` na raiz. O backend depende de `venergy-agent` com
  `{ workspace = true }` e importa só a porta `TextToSqlAgent` do agente.
- **Motivo:** com o endpoint `/ai` (G1-09), a API instala o agente. Com um lock por módulo, as
  dependências do agente seriam resolvidas duas vezes, e o CI testaria o agente com versões
  diferentes das que rodam na API. Uma resolução só garante que o que é testado é o que roda.
- **Alternativa descartada:** um lock por módulo com dependência por caminho
  (`venergy-agent = { path = "../ai-agent" }`). A autonomia de versões, que era a vantagem,
  deixa de existir quando a API instala o agente, e o trabalho no Docker é o mesmo.
- **Consequências:**
  - As versões ficam acopladas. O cliente do Gemini (`google-genai`) exige `websockets<17`, então
    a API passou de `websockets` 17.2 para 16.1.1. Na migração, nenhuma outra versão do agente mudou;
    no backend, só `httpx2` e `httpcore2` (de testes) foram de 2.14 para 2.16.
  - PRs de times diferentes que mexem em dependências disputam o mesmo `uv.lock`. Em conflito,
    mantenha os `pyproject.toml` dos dois lados e rode `uv lock` na raiz.
  - A imagem da API é construída com contexto na raiz (`backend/Dockerfile`), com um
    `.dockerignore` que só deixa entrar `backend/`, `ai-agent/`, `contracts/` e os arquivos do
    workspace: nada de dataset, `.env` ou `.venv`.
- **Regras:**
  - `uv sync --all-packages` na raiz instala tudo (`make setup`). `uv run` dentro de `backend/`
    ou de `ai-agent/` continua funcionando e usa o lock da raiz.
  - Dependência nova: `uv add` dentro da pasta do pacote que a usa; o `uv.lock` atualizado é
    o da raiz.
  - O ambiente é a `.venv` da raiz. As antigas `backend/.venv` e `ai-agent/.venv` podem ser
    apagadas, e o interpretador do editor passa a ser `.venv/bin/python` na raiz.
  - O serviço `api` recebe `VENERGY_AGENT_DATABASE_URL` (usuário `venergy_agent`) e
    `VENERGY_AGENT_GOOGLE_API_KEY`, que vem de `GOOGLE_API_KEY` no `.env` da raiz. A chave é
    opcional até o `/ai` existir e nunca entra em camada da imagem.

## DEC-018 · Relações entre views só por chave

- **Data:** 22/10/2026 · **Área:** GenAI · **Autor:** Lucas · **Atualizada:** 23/10/2026, Luis Felipe
- **Status:** aceita. O contrato v0.2.0 (PR #23) adotou a mesma regra em `relations`.
- **Decisão:** a camada semântica monta relações entre views só pelas chaves estrangeiras do contrato e pelas chaves de entidade (`cod_uc` e `cod_alimentador`). `competencia`, `municipio` e `bairro` não viram relação.
- **Motivo:** a spec (§5, item 5) manda montar relações a partir de `foreign_keys` e `shared_keys`. Juntar duas views só pelo período gera produto cartesiano, e o modelo tende a fazer essa junção quando a relação existe.
- **Consequência:** `sem_faturamento_mensal` liga a `sem_uc` por `cod_uc`, e `sem_uc` liga a `sem_continuidade_alimentador_mensal` por `cod_alimentador`.
- **Decomposição (23/10/2026):** `sem_receita_decomposicao` entra sem relação com outras views. A junção composta com `gold_dim_uc` (município, bairro, classe e GD) continua `a_confirmar` no contrato e repetiria cada efeito uma vez por UC do recorte. As perguntas de recorte se respondem filtrando a própria view.

## DEC-019 · Verificação numérica da narrativa

- **Data:** 22/10/2026 · **Área:** GenAI · **Autor:** Lucas · **Atualizada:** 23/10/2026, Luis Felipe
- **Status:** aceita.
- **Decisão:** a narrativa em linguagem natural só é aceita se cada número dela existir nas linhas que o redator recebeu ou no total de linhas. Números que aparecem só na pergunta ou nas suposições não contam. Se a verificação falhar, ou o redator der erro, a resposta volta ao texto determinístico.
- **Leitura dos números (decidido em 23/10/2026, PR #36):**
  - O texto é lido só em pt-BR: ponto separa milhar, vírgula separa decimal.
  - Os valores do banco são lidos no próprio tipo: `Decimal`, `int` e `float` pelo valor, e datas e textos sem letras (por exemplo `2025-03`) pelos números que contêm. Texto com letras não é fonte de número: o 7 do código `AL-07` não valida uma narrativa que diga "7" (Lucas, PR #36). Valores negativos contam pela magnitude ("queda de 10,5 mil" vale para `-10.5`).
  - A proposta inicial aceitava pt-BR e en ao mesmo tempo. Aí `1.234` valia como 1234 e como 1,234, e um número errado podia passar na verificação.
  - **Consequência aceita:** um número no formato en é rejeitado mesmo que exista nas linhas. `152.4` no texto é lido como 1524 e derruba a narrativa, ainda que `152.4` esteja no resultado. É o lado seguro: o usuário vê o texto determinístico, nunca um número mal lido.
  - Um trecho que não forma número em pt-BR (por exemplo `1,2,3` ou `01,02,03`) conta como número não verificado. A narrativa cai no texto determinístico, e a resposta continua `answered`: a verificação nunca levanta erro.
- **Insight (item 9):** o `InsightWriter` usa a mesma verificação. A fonte dos números são os valores do JSON de métricas da tela, inclusive os aninhados, e não as chaves: um número que só aparece numa chave (`receita_2024`) não valida o texto. Um insight com número fora do JSON, em formato en (por exemplo `1234.5` copiado do JSON) ou ilegível vira `None`, e a tela aparece sem insight. O prompt `prompts/insight/v1` pede o formato brasileiro. O período da tela vai dentro do JSON como valor (por exemplo `"periodo": "2025-01/2025-03"`), e não só no título: no teste com o modelo real (24/10/2026), o texto que citava "2025" a partir do título caía na verificação.
- **Motivo:** o `CLAUDE.md` do agente diz que todo número da resposta vem das linhas retornadas, e a spec (§8, item 8) exige que um número inexistente nas linhas derrube a narrativa.
- **Consequência:** uma narrativa que cite um ano ou um limite da pergunta ("acima de 300 kWh") cai no texto determinístico quando o número não está nas linhas. O prompt do redator (`prompts/answer/v1`) pede para não repetir esses números e para escrever no formato brasileiro. A verificação fica em `domain/numbers.py` (`unsupported_numbers`) e serve à narrativa e ao insight.

## DEC-020 · Contrato `AgentAnswer` com status (aceita)

- **Data:** 22/10/2026 · **Área:** GenAI e Backend (V1) · **Autor:** Lucas
- **Status:** aceita pelo V1 (revisão do PR #21, com as respostas abaixo). Mesclada com o PR #21; as invariantes de texto em branco e de `truncated` entraram pelo PR #29.
- **Decisão:** o `AgentAnswer` ganha `status` (`answered`, `unknown`, `clarify`, `refused`, `failed`), `truncated`, `refused_reason`, `model` e `latency_ms`. Nenhum campo existente é removido. As invariantes por status estão na spec §4 e têm teste no código.
- **Motivo:** o backend vai expor `POST /ai/ask` e `GET /ai/audit/{id}` (spec §10, D3). Sem `status`, o portal não distingue resposta, "não sei", pedido de esclarecimento e falha técnica, e a auditoria não guarda o modelo que respondeu nem a latência (G1-06). A spec (§4) manda combinar mudanças desse contrato com o V1 antes de implementar.
- **Consequência:** a spec §4 e o `answer.py` são a referência. Regras que o V1 não discutiu diretamente, mas que decorrem do contrato e foram pedidas na revisão do PR #21 (PR #29): `row_count >= 0`; texto em branco recusado em todo campo de texto; `truncated` exige linhas.
- **Respondido pelo V1 (PR #21):** (1) status em inglês, e o portal traduz; (2) sim, o último SQL vai em `failed`, para auditoria; (3) `refused_reason` e `answer` podem repetir o texto; (4) o agente mede a latência do `ask()` e o backend mede a requisição, e os dois vão para a auditoria; (5) campo novo é mudança menor da API; campo removido ou renomeado precisa ser combinado antes.

## DEC-021 · Recortes de receita somados no backend; DEC/FEC só no total

- **Data:** 22/10/2026 · **Área:** Portal · **Autor:** Felipe · **Atualizada:** 22/10/2026,
  com a revisão do João no PR #22 e o contrato v0.2 (PR #23)
- **Contexto:** o V1-05 pede KPIs e receita com filtros de período, município, bairro e
  classe. A `gold_kpis_mensais` tem uma linha por competência, sem esses recortes, e a
  `gold_receita_decomposicao` traz o PVM no menor recorte (município × bairro × classe).
- **Decisão:**
  - `GET /receita/mensal` devolve a `gold_kpis_mensais` como está, com recorte opcional de
    `inicio` e `fim` (`AAAA-MM`, inclusivos).
  - `GET /receita/comparacao`:
    - recebe dois períodos e, opcionalmente, o segmento;
    - soma em SQL o kWh e a receita da `gold_fato_faturamento_mensal`, com o município, o
      bairro e a classe vindos da `gold_dim_uc`;
    - a variação absoluta e a percentual são calculadas no backend. A percentual fica nula
      quando a base é zero.
  - `GET /receita/decomposicao`:
    - soma os efeitos preço, volume e mix que a Gold já calculou, no nível abaixo do filtro:
      município, depois bairro, depois classe;
    - desde o contrato v0.2, devolve também o efeito preço dividido em `efeito_tarifa` e
      `efeito_bandeira`, e soma juntas as linhas com e sem GD do mesmo segmento;
    - não refaz o PVM;
    - separa cada par de períodos;
    - ordena da maior queda para a maior alta.
  - DEC, FEC, chamados e satisfação não têm recorte por segmento: continuam só no total da
    empresa (`/receita/mensal`) e, por alimentador, na tela de continuidade.
  - `bairro` sem `municipio` é recusado com 422, nas duas rotas que aceitam esse filtro.
- **Motivo:**
  - Receita e kWh são aditivos: o total de um bairro é a soma das faturas das UCs dele. Somar
    não é fórmula de negócio, e é feito em `numeric`, então bate centavo por centavo com a
    `gold_kpis_mensais`. Os testes conferem isso com a amostra carregada.
  - Os efeitos do PVM também se somam entre segmentos, e a soma mantém o `check` do contrato
    (preço + volume + mix = variação) dentro da tolerância de arredondamento. O teste confere
    isso em todos os níveis.
  - DEC e FEC são médias ponderadas pelas UCs atendidas, calculadas por alimentador, e um
    alimentador atende vários bairros. Nenhuma soma ou média dos alimentadores dá o DEC de um
    bairro. Mostrar um número errado é pior do que não mostrar.
  - O mesmo nome de bairro pode existir em dois municípios, e somar os dois daria um recorte
    que ninguém pediu.
- **Alternativas descartadas:**
  - Pedir ao time de Dados um grão novo na `gold_kpis_mensais`, com município, bairro e
    classe: travaria o V1-05 à espera do contrato v0.2. Continua possível como evolução, se a
    diretoria precisar de DEC/FEC por bairro calculado na Gold.
  - Recalcular o PVM em cada nível do drill-down: seria uma segunda fórmula no backend, que
    poderia divergir da Gold e do diagnóstico.
  - Três rotas, uma por nível: o breadcrumb da tela só acrescenta filtros, e uma rota mantém
    um schema só no client.
- **Desempenho (aceite "< 1 s"):**
  - Medido com dados sintéticos no volume da base real: 45.200 UCs × 24 meses, ou seja,
    1.084.800 linhas na fato.
  - O pior caso foi a comparação da empresa inteira, com mediana de 224 ms e máximo de
    260 ms. Com filtro de bairro, 23 ms. A decomposição e a série mensal ficaram abaixo de
    12 ms.
  - Nenhum índice novo. A consulta com filtro usa a chave primária da fato
    (`cod_uc, competencia`), e um índice na `gold_dim_uc` só deixaria a carga mais lenta.
- **Limitações conhecidas** (apontadas pelo João na revisão do PR #22):
  - A tolerância do contrato é de R$ 0,02 por linha em preço + volume + mix = variação, e ela
    se acumula com o número de linhas somadas. Com a Gold real, a ponte de um município pode
    não fechar no centavo; a diferença é arredondamento, e não erro.
  - Os recortes da comparação usam o cadastro atual da UC: a `gold_dim_uc` tem uma linha por
    UC. Os meses passados de uma UC que mudou de classe ou de bairro caem no recorte atual.
- **Consequências:**
  - O contrato v0.2 confirmou o formato do período (`AAAA-MM/AAAA-MM`) e trouxe a
    `gold_kpis_segmento_mensal` (DEC-023), com componentes somáveis por mês, município,
    bairro, classe e GD. Ela resolve as duas limitações acima e permite DEC/FEC por recorte,
    calculado sobre os componentes. Trocar o `/receita/comparacao` para essa tabela e liberar
    DEC/FEC por recorte é uma tarefa própria, que revisa esta decisão.
  - O agente de IA, se responder sobre receita de um segmento, precisa somar a mesma fato com
    a mesma dimensão para bater com a tela.
  - **Atualização (26/10/2026):** DEC e FEC passam a ter recorte por município, bairro, alimentador e
    classe, calculados sobre os componentes da `gold_kpis_segmento_mensal` (DEC-033). A troca do
    `/receita/comparacao` para essa tabela continua pendente.

## DEC-022 · Regras do agente sobre a Gold e decisões da daily de 21/10

- **Data:** 21/10/2026 · **Área:** Dados e IA · **Autor:** Alisson
- **Contexto:** a revisão do GenAI no contrato da Gold (PR #10) pediu regras claras sobre o
  que o agente pode ler e sobre o significado de "receita" quando a pergunta não qualifica.
- **Decisão:**
  - As views `sem_*` do agente usam só as tabelas com `agente` em `consumers` e só as
    colunas com status `confirmada` ou `proposta` e `sensitive` diferente de `true`.
  - `gold_fila_suspeitas` fica fora do agente por padrão, por ser uma lista de suspeitos.
  - "Receita" sem qualificador é `receita_faturada`. O agente declara essa suposição na
    resposta.
  - `gold_receita_decomposicao` guarda qualquer par de períodos (faixas de meses), não só
    primeiros e últimos 12 meses, para comparar também os mesmos meses em anos diferentes.
  - `score_suspeita` é a posição no ranking (1 = mais suspeita), e não uma nota.
  - Dado pessoal (nome e documento do titular) só entra na Gold mascarado, com `sensitive: true`;
    o dado original não chega às tabelas Gold.
- **Motivo:** dado pessoal e texto livre de chamado são o principal risco de vazamento e
  de prompt injection; uma definição única de receita evita que portal e agente mostrem
  números diferentes para a mesma pergunta.
- **Onde está:** `contracts/gold_schema.yaml` (`conventions.agent`, `sensitive` e
  `consumers`), versão 0.2.0.

## DEC-023 · Medidas de receita, reconciliação e ajustes de colunas da Gold

- **Data:** 22/10/2026 · **Área:** Dados · **Autor:** Alisson
- **Status:** decidido no time de Dados; a base oficial da receita do PVM só é confirmada depois da
  reconciliação.
- **Contexto:** a Silver de faturas traz o valor da energia, os tributos e o valor total da fatura
  (total = energia + tributos), e o glossário do projeto define a receita faturada como o valor
  emitido na fatura. Faltava dizer qual valor sustenta o PVM e a tarifa média, e como tratar as
  faturas de UCs fora do cadastro.
- **Decisão:**
  - A Gold guarda as três medidas, sem descartar nenhuma: `receita_faturada` (total, com
    tributos), `receita_energia` (sem tributos) e `tributos`, em `gold_fato_faturamento_mensal`;
    `receita_energia` também entra em `gold_kpis_mensais`.
  - Provisoriamente, `receita_energia` é a base do PVM (`receita_base` e `receita_atual`) e da
    `tarifa_media`: tributos não são receita da distribuidora na decomposição de preço.
  - A base oficial só é confirmada depois de uma reconciliação e de um teste declarado: medir qual
    definição (com ou sem tributos) reproduz a variação citada pela diretoria e registrar o
    resultado como hipótese testada, sem ajustar números para coincidir com o case.
  - **Reconciliação (aprovada):** `gold_reconciliacao_faturamento`, uma linha por competência, é a ponte do
    número bruto até o usado nos indicadores. Receita: total de todas as faturas, parcela das UCs fora do
    cadastro, receita das UCs do cadastro, tributos e receita de energia. Energia: consumo apurado nas
    leituras, correção das trocas de medidor, correção do sinal invertido e energia faturada final. As
    faturas órfãs ficam fora do fato por UC, mas nunca são descartadas: aparecem aqui. Responde à banca
    qual receita é considerada, quanto vem de faturas sem cadastro e de onde vem a diferença entre a
    receita da diretoria e a nossa (tributos, órfãs ou período). Validações permanentes: total = cadastro
    + órfãs, cadastro = energia + tributos, energia final = leitura + correções, e tudo bate com a soma
    do fato por competência. Entra no agente.
  - **Documento repetido (UC-12):** `flag_documento_repetido` existe só na Silver de
    `unidades_consumidoras`. A Gold não traz essa coluna (nem `gold_dim_uc`): a flag entra como
    filtro na construção da Gold, não como atributo. Confirmado por Arthur (Dados) em 23/10/2026.
    As UCs com documento repetido **não** contam no `n_uc`: o PRODIST (Módulo 8) define o denominador
    do DEC/FEC como as UCs faturadas do conjunto no período, e essas UCs nunca são faturadas (não têm
    medidor, leitura, fatura nem ocorrência; a Gold confere). Por isso o `n_uc` passa a ser o de UCs
    com fatura na competência, o que também tira os meses de ligação antes da primeira fatura. Elas
    ficam na `gold_dim_uc`, sem `consumo_medio_kwh_12m`. Proposta do Arthur na revisão deste PR.
  - **`possui_gd` na decomposição:** é o estado no último mês do período atual e vale para a UC nos
    dois períodos. A UC que conectou a GD entre eles fica no grupo com GD de ambos os lados, porque o
    PVM compara linhas de mesma chave e o efeito GD precisa ser a queda de volume das mesmas UCs. É o
    mesmo grupo do diagnóstico (as UCs da tabela de GD, todas conectadas depois do início de P1), então
    os números do diagnóstico não mudam. Em `gold_kpis_segmento_mensal` continua por competência, a
    partir do mês da conexão; por isso as duas tabelas podem diferir no período base.
  - `consumo_medio_kwh_12m` passa a aceitar nulo: há UCs do cadastro sem nenhuma leitura, e sem
    leitura não há média. Zero seria inventar dado.
  - `potencia_kw` passa a ser `potencia_kwp`, em kWp: a origem só traz potência de pico, e kW
    é outra grandeza. A referência a kW vinha só da documentação escrita antes de ver os dados.
  - A bandeira é convertida na Gold para o formato do contrato (`verde`, `vermelha_p1`...).
  - **Classe (opção B):** `classe` continua com B1, B2, B3 e A4, como o glossário do case define
    "classe de consumo", e que backend e agente já usam. Entra `classe_cadastro` em `gold_dim_uc`,
    com as 5 classes do cadastro (Residencial, Comercial, Industrial, Rural, Poder Público), para
    separar Comercial de Poder Público, que dividem o B3. A decomposição continua por `classe`.
  - O diagnóstico do PR #19 mostra que a variação da receita é a mesma com e sem tributos, então a
    escolha da base muda os valores absolutos, mas não a variação. A base continua sendo a energia,
    pela definição, e não pelo ajuste ao número da diretoria.
- **Regra de `kwh_faturado` (validada contra a fatura):**
  - A fatura não traz kWh, mas é o que foi cobrado. O kWh implícito dela (energia da fatura dividida
    pela tarifa mediana do subgrupo na competência, calculada só com leituras limpas) serviu de
    referência para testar cada regra.
  - Todo caso que precisa de correção tem consumo negativo. Se há medidor instalado na competência
    (troca de medidor), `kwh_faturado` = leitura atual; se não há (sinal invertido), valor absoluto.
    Consumo não negativo: o consumo da leitura.
  - Resultado do teste: nos casos sinalizados, a leitura atual reproduziu a fatura em todas as
    trocas de medidor, e o valor absoluto reproduziu os de sinal invertido; o consumo bruto não
    reproduziu nenhum. A coluna `origem_kwh` registra qual regra valeu em cada linha, e
    `kwh_leitura` guarda o consumo original.
  - Origem da hipótese: diagnóstico do PR #19. A regra passa a valer por ter sido validada nos dados,
    e não pela autoria.
  - **Geração distribuída:** o consumo da leitura já é líquido de GD, como o case descreve. Teste: nas
    UCs com GD, a queda do consumo médio depois da conexão (até 12 meses de cada lado, mínimo 6)
    dividida pela energia injetada média mensal tem mediana próxima de 1, e todas ficam entre 0,7 e
    1,3. Isso vale também para as UCs com potência anômala: a anomalia está na potência, e não na
    energia injetada. Portanto `kwh_faturado` não precisa de correção por GD.
- **Efeito bandeira e efeito GD na decomposição:** em `gold_receita_decomposicao`, `efeito_preco`
  passa a ser a soma de `efeito_tarifa` (reajuste da tarifa base) e `efeito_bandeira` (acréscimo da
  bandeira tarifária), e `possui_gd` entra no grão. O efeito GD é o efeito volume das linhas com
  `possui_gd = true`, sem coluna de efeito própria. Motivo: o diagnóstico do PR #19 mostra que a
  bandeira e a GD explicam boa parte da variação, e o portal precisa mostrá-las separadas.
- **KPIs por recorte:** nova `gold_kpis_segmento_mensal`, com grão mês × município × bairro × classe
  × geração própria (`possui_gd`, por competência),
  que guarda componentes somáveis (UCs, kWh, receitas, horas e interrupções, chamados, soma e
  contagem das notas) e não os índices. O portal soma os componentes do filtro da diretoria e
  calcula DEC, FEC e satisfação no final, e assim bairro, município e empresa ficam consistentes.
  `gold_kpis_mensais` continua como total da empresa; a soma da nova por mês tem que bater com ela
  e com a continuidade por alimentador (validações da Gold). Motivo: o filtro da diretoria por
  município, bairro e classe e a separação de KPI por recorte, pedidos no grupo. DEC e FEC por
  recorte saem das ocorrências por UC (no case, cada ocorrência é uma UC interrompida).
  Período: qualquer intervalo é a soma das competências escolhidas. `n_uc` é um estoque, então para
  vários meses o DEC e o FEC usam a média mensal de `n_uc`. O agente e o portal podem cruzar tempo,
  território, classe e GD sobre as mesmas colunas.
- **Situação da fatura na UC 360 (sugestão do João Euclides, PR #23):** `gold_fato_faturamento_mensal`
  ganha `data_vencimento`, `data_pagamento`, `status_pagamento` e `dias_em_atraso`, sem tabela nova. Uma
  UC tem uma única fatura por competência (conferido: nenhum par UC × mês com mais de uma fatura), então
  o grão do fato já é o da fatura. O status tem quatro valores (`paga`, `paga_com_atraso`, `em_aberto` e
  `em_atraso`) e é calculado na Gold, e não no backend, contra uma data de corte: a maior data presente
  nas faturas, já que o dado é uma extração única. No dataset do case todas as faturas não pagas estão em
  atraso (a data de corte é posterior a todos os vencimentos); `em_aberto` passa a existir quando a Gold
  receber dados novos.
- **Titular na UC 360:** o case pede que a tela mostre "quem é o cliente", e a Gold traz só
  `titular_mascarado` (iniciais) e `documento_mascarado` (3 últimos dígitos), ambos `sensitive`,
  que substituem `cod_cliente`. Não há código de cliente na origem, e o teste do cadastro mostrou que
  cada titular tem uma UC só, exceto um documento de preenchimento repetido num grupo de UCs
  cadastradas sem nenhum medidor (verificado: o grupo é exatamente o das UCs sem medidor, e o documento
  não é nulo). Ligar UCs do mesmo titular não traria nada ao case. O mascaramento
  acontece na criação da Gold, e o original não chega às tabelas.
- **Colunas confirmadas e removida:** `periodo_base` e `periodo_atual` ficam como texto `AAAA-MM/AAAA-MM`
  (qualquer par de períodos), e `receita_base` e `receita_atual` mantêm o nome; os quatro passam a
  `proposta`. `subgrupo` sai de `gold_dim_uc`: guardava os mesmos valores de `classe` (B1, B2, B3 e A4)
  e não é usado pelo agente nem pelo portal. A Silver continua com `subgrupo_tarifario`.
- **Atendimento:** `n_chamados`, `soma_notas`, `n_notas` e `satisfacao_media` passam de `a_confirmar`
  para `proposta`: a Silver de atendimentos já existe (ATD-01 a ATD-03). O chamado conta pelo mês de
  abertura, a nota vai de 1 a 5, e o chamado sem nota fica fora da média.
- **Motivo:** cada número do portal e do agente precisa ser rastreável até a origem. Com as três
  medidas e a reconciliação, a diferença entre a receita da diretoria e a calculada pelo time pode
  ser explicada parcela por parcela (tributos, faturas órfãs, período).
- **Pendências:** definir e validar o método do cálculo do efeito bandeira. Os dois grupos de leitura negativa foram testados e são exclusivos e completos: cada leitura
  negativa cai em exatamente uma das duas regras.
- **Impacto:** muda colunas, nome e nulidade no contrato (`contracts/gold_schema.yaml`, v0.2). Pela
  DEC-014, o ajuste do backend vai no mesmo PR, e o GenAI é avisado (camada semântica, PR #20).

## DEC-024 · O que pode subir ao repositório público

- **Data:** 22/10/2026 · **Área:** Dados, Portal e IA · **Autor:** Alisson (decidido na daily de 22/10)
- **Contexto:** o dataset do case é confidencial e o repositório é público. Até aqui a regra era não
  publicar nada derivado do dataset (DEC-008). O diagnóstico da receita precisa mostrar a evidência
  de cada hipótese, e isso exige números.
- **Decisão:**
  - **Pode subir:** resultado agregado necessário para confirmar ou refutar uma hipótese ou para
    sustentar uma recomendação: contagens, percentuais, valores em R$ e GWh, tarifas médias por
    classe, nomes de município, de bairro e de alimentador quando forem parte da evidência.
  - **Fica mascarado:** tudo o que identifica uma pessoa ou uma UC individual, e qualquer dado
    relacionado à LGPD: nome e documento do titular, endereço completo, CEP, coordenadas, `cod_uc`,
    `cod_cliente`, protocolo de atendimento, telefone e e-mail. Quando precisar aparecer, entra
    mascarado (como já está no contrato da Gold: coluna `sensitive`, sem o dado original).
  - **Nunca sobe:** registro linha a linha, amostra de linhas, CSVs, arquivos do dataset e outputs de
    notebook (o notebook é versionado sem outputs). Credenciais e tokens também não.
  - **Recorte que identifica um cliente individual:** não publicar agregado cujo recorte aponte para
    um cliente só, como uma indústria isolada, uma UC única de uma classe ou um grupo tão pequeno que
    permita saber quem é. Nesses casos, agrupar num "outros" mantendo o total. Não há número mínimo
    fixo: vale o critério de identificar ou não um cliente.
  - **Achado individual:** nada que ligue uma irregularidade, fraude ou inadimplência a uma UC, a um
    titular ou a um endereço. Em texto público, "irregularidade confirmada" (e não "fraude"), porque a
    inspeção não distingue furto, fraude e erro.
  - Todo documento público com números deve dizer, no topo, que segue esta decisão.
- **Motivo:** o diagnóstico precisa de evidência para ser defensável diante da diretoria, e o
  agregado necessário à hipótese não identifica ninguém. O risco real está na identificação e em
  achados atribuíveis a um indivíduo.
- **Substitui em parte:** a regra de "nenhum número do dataset" da DEC-008 (evidências em relatório
  privado) e a pergunta em aberto da DEC-004 sobre a Gold agregada no repositório: o agregado
  necessário à hipótese pode subir; os CSVs da Gold continuam fora do Git.
- **Em aberto:** confirmar com a Visagio que resultados agregados do diagnóstico podem ser públicos
  (o case marca os materiais como confidenciais e pede um repositório público).

## DEC-025 · Mapa da RMR como seletor de município e bairro (proposta)

- **Data:** 23/10/2026 · **Área:** Portal · **Autor:** João Euclides
- **Status:** proposta, a confirmar com Dados (lista de municípios da Gold).
- **Contexto:** o log de qualidade registra "14 municípios da RMR" em `unidades_consumidoras`, sem listar quais. A RMR oficial tem 15 desde a LC estadual 382/2018, que incluiu Goiana. As regiões geográficas do IBGE não coincidem com a RMR: a Imediata de Recife inclui Paudalho e Fernando de Noronha e deixa Goiana de fora.
- **Decisão:**
  - geometria da Malha Municipal 2025 do IBGE (`PE_Municipios_2025`), filtrada pelos 15 códigos IBGE da RMR, projetada em UTM 25S e simplificada; os municípios vizinhos entram só como contorno de contexto;
  - bairros da malha de bairros do Censo 2022 (`PE_bairros_CD2022`), na mesma projeção: 315 bairros em 12 municípios. Goiana, Ilha de Itamaracá e Moreno não têm bairros na malha do IBGE e ficam só com a tabela e o menu;
  - os arquivos gerados (`frontend/src/components/ui/region-map/rmr.gen.ts`, ~20 KB, e `rmr-bairros.gen.ts`, ~140 KB, ~47 KB com gzip, baixado só quando um município é escolhido) são versionados; os shapefiles não. Regerar: `npm run gen:mapa -- <pasta do PE_Municipios_AAAA> <pasta do PE_bairros_CD2022>`;
  - a Gold não tem código IBGE: município e bairro da Gold casam com os do mapa pelo nome sem acento, caixa e espaço extra. O que não casa aparece apagado e sem link no mapa, mas continua na tabela e no menu do topo.
  - cor do mapa pela variação da receita sobre a receita base do próprio segmento, em escala contínua: abaixo de 0,5% é neutro, e a cor (vermelho para queda, verde para alta, misturados à superfície) e o brilho do contorno crescem até saturar em 10%. A fração é calculada no frontend só para a cor; nenhum número novo é exibido (o hover mostra a variação em R$ da API).
- **Motivo:** o mapa funciona com 14 ou 15 municípios sem mudar o contrato; as malhas são públicas e não são dado do case.
- **Em aberto:** (1) Dados confirmar os 14 nomes de município da Gold e conferir os bairros contra a malha do IBGE (bairro vem do cadastro, em texto livre); (2) avaliar `cod_municipio_ibge` e `cod_bairro_ibge` (`CD_BAIRRO`) na `gold_dim_uc` para casar por código; (3) o bairro do IBGE é agregado de setores censitários e pode não coincidir com o limite oficial da prefeitura; (4) se a variação percentual for exibida, ela passa a vir da API (`variacao_receita_pct` em `/receita/decomposicao`), como já vem em `/receita/comparacao`.

## DEC-026 · Ações das OIs, Kanban e troca de visão na tela de perdas

- **Data:** 23/10/2026 · **Área:** Portal · **Autor:** João Euclides
- **Contexto:** o backend já expõe `PATCH`, `GET /{id}` (histórico) e `POST` das ordens de inspeção (DEC-009), mas a tela de perdas só listava as OIs.
- **Decisão:**
  - a tela mostra só os botões das transições permitidas, a partir de uma cópia das `TRANSICOES` do backend (`ACOES_POR_STATUS` em `features/perdas/conversions.ts`). A cópia serve só para exibir: quem decide é o backend, que responde 409 a uma transição inválida, e a tela mostra a mensagem dele;
  - enviar a campo é sem formulário (a observação é opcional e a OI ainda pode ser cancelada), mas o PATCH só sai depois de 6 s: um aviso embaixo da tela oferece "Desfazer" e "Enviar agora", e o tempo para enquanto o ponteiro ou o foco estão no aviso. É o único desfazer: o backend continua sem a volta Em campo → Gerada (DEC-009), e Concluída e Cancelada continuam finais. Sair da tela envia na hora o que estava agendado; fechar a aba pede confirmação do navegador;
  - concluir e cancelar abrem um modal (Modal do interior.dev): concluir pede o resultado, cancelar pede segurar o botão (HoldToConfirm), porque não tem volta. O histórico, que é consulta, abre no painel lateral (Sheet);
  - Kanban e tabela ocupam a largura toda da tela, sem a descrição da tela no topo (o layout da tela de perdas será ajustado quando a fila de suspeitas entrar); o Kanban também estica até o fim da altura. Cada ação tem a cor do status a que leva (enviar = info, concluir = success, cancelar = danger);
  - Kanban com as ativas (Gerada, Em campo) completas e as finalizadas (Concluída, Cancelada) limitadas às últimas N por `atualizada_em`, com N pela altura da viewport: 3 abaixo de 900 px (notebook), 5 até 1299 px (PC 1080p), 8 a partir de 1300 px (desktop grande). "Ver todas" leva à tabela filtrada pelo status;
  - cada cartão tem botões de ação; arrastar entre colunas (HTML5 Drag and Drop, sem biblioteca) é só atalho para a mesma ação;
  - a visão (Kanban ou tabela) é preferência do usuário, não filtro: fica no `localStorage` (`perdas:visao-ordens`, padrão Kanban), não na URL. Abaixo de 48rem a tela mostra sempre a tabela em cards, sem mexer na preferência salva;
  - gerar OIs por códigos de UC digitados (repetidos ignorados, até 200 por pedido), enquanto não existe endpoint da fila de suspeitas;
  - Vitest no frontend só para funções puras (`src/**/__tests__/*.test.ts`, sem DOM).
- **Motivo:** cobre o ciclo de vida da OI sem regra de negócio nova no frontend; o Kanban dá a visão do trabalho em andamento sem a lista de finalizadas crescer sem limite.
- **Em aberto:** (1) gerar a partir da fila de suspeitas quando houver `GET` da `gold_fila_suspeitas`; (2) autoria das mudanças no histórico quando houver autenticação.

## DEC-027 · Contrato da Gold v0.3: UC 360, inspeções e recortes completos

- **Data:** 24/10/2026 · **Área:** Dados, Portal e IA · **Autor:** Alisson
- **Status:** proposta; pela DEC-014, o backend entra no mesmo PR, e o GenAI é avisado (camada semântica).
- **Contexto:** o check da Gold contra os consumidores mostrou lacunas: a UC 360 não tinha medidor, interrupções nem chamados
  (as tabelas estavam sem colunas); H1 não comparava a UC antes e depois da conexão da GD; H2 não tinha a taxa de irregularidade
  das inspeções por recorte; H5 não tinha leituras estimadas nem tipo de medidor; o portal não cruzava alimentador com bairro e
  classe nem tinha inadimplência por recorte.
- **Decisão:**
  - `gold_dim_uc` ganha `data_ligacao`, `data_conexao_gd`, `modalidade_gd` e `energia_injetada_kwh_mes`.
  - `gold_fato_faturamento_mensal` ganha `receita_bandeira`, `tipo_leitura`, `tipo_medidor` (o medidor da leitura) e
    `dias_faturados` (dias desde a leitura anterior, para o insight de conta alta).
  - `gold_kpis_segmento_mensal` ganha `cod_alimentador` e `tipo_medidor` na chave (medidor vigente no mês, pela instalação e
    retirada; `sem_medidor` quando não há) e os componentes `receita_bandeira`, `n_faturas`, `n_faturas_nao_pagas`,
    `valor_nao_pago`, `n_faturas_pagas_com_atraso`, `soma_dias_em_atraso`, `n_leituras` e `n_leituras_estimadas`. Cada bairro é
    atendido por 1 ou 2 alimentadores, então a chave nova quase não aumenta a tabela (cerca de 3% a mais de recortes).
  - A situação da fatura nos recortes é a da data de corte, e não a do mês da fatura: numa competência antiga, "não paga" quer
    dizer "daquele mês e ainda sem pagamento hoje". Está escrito nas colunas para o portal e o agente não lerem errado.
  - Tabelas da UC 360: `gold_interrupcoes_uc` (1 linha por ocorrência), `gold_atendimentos_uc` (1 linha por chamado, sem o
    histórico de texto livre, que é sensível) e `gold_medidor_uc` (medidor vigente, idade e trocas).
  - `gold_inspecoes_uc` nova (1 linha por inspeção, sem o nome do inspetor), fora do agente, como a fila de suspeitas.
  - Tipo `timestamp` no contrato, para a hora de abertura das ocorrências e dos chamados.
- **Limites:** "medidor sem manutenção" não é respondível, porque a data de manutenção vem vazia na origem (MED-06). As faturas de
  UCs fora do cadastro (cerca de 1,5% da receita) só existem por competência na reconciliação: sem cadastro, não há município,
  bairro nem classe para cruzar.
- **Impacto:** muda colunas e chaves. Backend (modelos, schemas, amostra, `test_contrato_gold.py`, OpenAPI e cliente) no mesmo PR;
  views `sem_*` e golden set no GenAI.

## DEC-028 · Pares de períodos da decomposição e o que fica para o backend

- **Data:** 24/10/2026 · **Área:** Dados e Portal · **Autor:** Alisson
- **Contexto:** o portal precisa comparar qualquer período (ex.: jan–abr de um ano contra o outro, jan–fev, 12 meses contra 12
  meses). Totais e comparações já saem da soma dos meses em `gold_kpis_segmento_mensal`. A decomposição (preço, volume, mix e
  bandeira) não: o efeito preço usa o preço do período base e o mix usa o peso das classes no período inteiro, então ela não se
  soma mês a mês e cada par precisa ser calculado inteiro.
- **Decisão:**
  - `gold_receita_decomposicao` grava todos os pares de **mesmos meses em anos diferentes** com dado nos dois lados: cada mês de
    início, cada duração de 1 a 12 meses e cada par de anos. Com 48 competências, são algumas centenas de pares e cerca de
    1 milhão de linhas. Inclui o par da pergunta da diretoria (os 12 primeiros meses contra os 12 últimos).
  - Pares de **trechos diferentes** (ex.: jan–abr de um ano contra mar–jun de outro) **não** são gravados: todas as combinações de
    intervalos passariam de 1 bilhão de linhas (milhares de pares só entre intervalos do mesmo tamanho), com CSV de dezenas de GB,
    carga de horas e quase nenhuma consulta. Comparar trechos diferentes também distorce pela sazonalidade.
  - Se o portal precisar desses pares, o **backend calcula na hora**, com a mesma fórmula, a partir de
    `gold_fato_faturamento_mensal` (que agora traz `receita_bandeira`), da dimensão e da data de conexão da GD. Um teste garante
    que, nos pares gravados, o backend dá o mesmo resultado da Gold. Cálculo de negócio no backend é permitido pelo projeto.
  - O agente fica com os pares gravados: ele lê métricas, não recalcula.
  - Período sem dado (antes de jul/2022) não tem decomposição em nenhum caso; a tela mostra "sem dados".
- **Impacto no portal:** o seletor da decomposição oferece os pares que existem (lista de pares ou mesmo trecho em dois anos); o
  seletor de totais continua livre.

## DEC-029 · Método do efeito bandeira

- **Data:** 24/10/2026 · **Área:** Dados · **Autor:** Alisson
- **Contexto:** a DEC-023 separou `efeito_preco` em `efeito_tarifa` e `efeito_bandeira`, mas deixou o método pendente.
- **Conferência no dado:** a tarifa efetiva de cada mês (energia da fatura ÷ kWh, com leituras limpas) é a tarifa base da classe
  mais um acréscimo por kWh que depende só da bandeira e é igual em todas as classes. Sem o acréscimo, a tarifa base fica
  constante dentro de cada ciclo de reajuste (maio), em todas as classes; a única mudança fora de maio é no B1, em jan/2026.
- **Decisão:**
  - Acréscimo por kWh: verde 0; amarela 0,01885; vermelha P1 0,04463; vermelha P2 0,07877 (R$/kWh).
  - `receita_bandeira = kwh_faturado × acréscimo`; receita pela tarifa base = `receita_energia − receita_bandeira`.
  - Na decomposição, com `P0 = R0/Q0`, `pb0` a tarifa base média do período base e `β0 = P0 − pb0`:
    `efeito_tarifa = (Rb1 − Q1·pb0) − (Rb0 − Q0·pb0)` e `efeito_bandeira = (B1 − Q1·β0) − (B0 − Q0·β0)`, onde `Rb` é a receita
    pela tarifa base e `B` a receita de bandeira. Com volume e mix, os quatro efeitos somam exatamente `R1 − R0`.
- **Conferência:** no par da pergunta da diretoria, a variação, o efeito mix e o efeito bandeira reproduzem o diagnóstico.
- **Tolerância (revisão do #43, Arthur):** a checagem preço + volume + mix = variação soma quatro parcelas arredondadas ao
  centavo (tarifa, bandeira, volume e mix), e não três. O pior caso é exatamente R$ 0,02, e com double a trava pode falhar
  por acaso numa recarga. A tolerância passa a R$ 0,025 por linha, no contrato e na trava da Gold.

## DEC-030 · Regras aplicadas na Gold: UCs, ocorrências, GD e fila de suspeitas

- **Data:** 24/10/2026, revisada em 26/10/2026 com a comparação das cópias do Alisson e do Arthur · **Área:** Dados · **Autor:** Alisson
- **Status:** as duas cópias batem tabela por tabela; falta a cópia do Gabriel para fechar a versão oficial (DEC-011).
- **Decisão:**
  - **`n_uc`:** UCs **faturadas** na competência, como no PRODIST (denominador do DEC/FEC = UCs faturadas do conjunto). Ficam fora
    as UCs da UC-12, que nunca são faturadas, e os meses de ligação antes da primeira fatura. A base dos recortes e da continuidade
    tem as UCs ligadas com fatura ou com algum evento no mês; as poucas interrupções e chamados em mês sem fatura continuam no
    numerador, e a Gold informa quantos são.
  - **Ocorrências antes da ligação (OCO-04):** há ocorrências registradas antes do mês de ligação da UC. Ficam fora da Gold (DEC/FEC,
    recortes e UC 360), porque a UC ainda não existia; a Silver mantém a linha, e a Gold confere que Gold + excluídas = Silver.
  - **Potência anômala da GD (GD-02):** o registro é convertido de Wp para kWp (÷ 1000) **quando o dado confirma**: o valor
    convertido cai na faixa das UCs com GD normais, e a energia injetada por kWp também. Quase todos os registros anômalos passam;
    os poucos que não passam (energia injetada por kWp muito acima de qualquer UC normal) ficam vazios, porque a origem não diz qual
    é a potência. A Gold informa quantos foram convertidos e quantos ficaram vazios. (Antes: todos nulos.)
  - **Vazio e zero nos recortes:** `receita_arrecadada` fica vazia quando o recorte não tem fatura na competência, e é zero quando há
    fatura e nada foi pago; `soma_notas` fica vazia quando nenhum chamado foi avaliado. Não arrecadar e não ter fatura são coisas
    diferentes para o agente. Na fatura (fato), a não paga continua com zero.
  - **Fila de suspeitas:**
    - **Quem entra:** UCs sem GD, com medidor, com pelo menos 6 meses em cada janela e queda de 15% ou mais no consumo médio
      (`kwh_faturado`) das 12 últimas competências contra as 12 anteriores.
    - **Quem sai:** UCs com irregularidade confirmada (já regularizadas) e UCs inspecionadas sem irregularidade nos 12 meses antes
      do fim dos dados. Uma UC inspecionada sem irregularidade há mais tempo pode voltar à fila.
    - **Ordem:** pontos (queda de 30% ou mais: 3; de 15% a 30%: 1; medidor eletromecânico: 1; 25% ou mais de leituras estimadas: 1)
      e depois o kWh a recuperar (`kwh_recuperavel_est` = média anterior − média recente).
    - **Validação:** nas UCs inspecionadas, a regra é medida com a janela na **data de cada inspeção** (as 12 competências antes dela
      contra as 12 anteriores), que é o que a equipe via ao decidir; a janela atual inclui meses depois da regularização. Precisão e
      cobertura saem a cada carga.
    - **Volume:** a regra é precisa, mas conservadora: a fila fica menor que a capacidade de inspeção de um mês. Ganhar volume
      (entrada mais solta ou outro sinal) fica para uma próxima calibração, medida do mesmo jeito.
  - **Outras escolhas da cópia:** `receita_arrecadada` é zero na fatura não paga (como na amostra do backend); consumo médio na
    janela das 12 últimas competências; titular por iniciais e documento com os 3 últimos dígitos.

## DEC-031 · Rota de pares da decomposição e par de períodos obrigatório

- **Data:** 26/10/2026 · **Área:** Portal · **Autor:** Felipe
- **Contexto:** a DEC-028 faz a Gold gravar todos os pares de mesmos meses em anos diferentes (cerca de 666 pares). Até a v0.2, a
  Gold trazia um par só, e `GET /receita/decomposicao` aceitava o par como filtro opcional e somava o que houvesse.
- **Decisão:**
  - `GET /receita/decomposicao/periodos` devolve os pares gravados (`SELECT DISTINCT`), em ordem. É o que o seletor da tela
    oferece, como o Alisson pediu no PR #43.
  - `GET /receita/decomposicao` passa a exigir `periodo_base` e `periodo_atual`, no formato `AAAA-MM/AAAA-MM`; sem eles, ou fora
    do formato, a resposta é `422`.
  - Versão da API 0.5.0: o par obrigatório quebra quem chamava sem ele, e na série 0.x quem sobe é o número do meio.
- **Alternativa descartada:** manter o par opcional. Sem par, a resposta seria uma linha por município de cada um dos pares
  (666 vezes o número de municípios), e a tela não saberia qual mostrar. A tela de receita (`decomposicao-table`, `mapa-recorte` e
  `recorte-trilha`) passou a pedir o par e o escolhe pela rota `/receita/decomposicao/periodos`: abre na janela de 12 meses com o
  período atual mais recente e oferece só os pares gravados.
- **Limite:** a rota só conhece os pares gravados. Pares de trechos diferentes (DEC-028) continuam fora, e entram só se o portal
  precisar deles.
- **Amostra:** o gerador grava os 78 pares de mesmos meses entre 2024 e 2025, para o seletor ter o que mostrar.

## DEC-032 · DEC e FEC de um período somam os mensais (proposta)

- **Data:** 24/10/2026 · **Área:** GenAI e Dados · **Autor:** Luis Felipe
- **Status:** proposta. Precisa da aprovação de Dados (o contrato da Gold) e de GenAI (a camada semântica). Pedido de revisão do Lucas no PR #41.
- **Contexto:** a camada semântica não dizia como agregar DEC e FEC de vários meses. Nas rodadas de avaliação do PR #41, o agente usou ora a soma, ora a média dos valores mensais da mesma view, para a mesma pergunta (G020: DEC do AL-07 no semestre).
- **Decisão proposta:**
  - DEC e FEC são indicadores acumulados: o valor de um semestre ou de um ano é a soma dos valores mensais prontos (`sum(dec)`, `sum(fec)`), nunca a média.
  - Para um recorte de `gold_kpis_segmento_mensal`, continua a fórmula dos componentes do contrato: horas e interrupções somadas ÷ média mensal de UCs.
  - As duas formas dão o mesmo número quando o `n_uc` não muda no período.
- **Motivo:** a média dos meses subestima o indicador do período. Uma regra explícita tira a ambiguidade, que hoje o modelo resolve sozinho, de um jeito diferente a cada execução.
- **Consequência:** a regra está na camada semântica 0.3.3 e na referência do G020 (golden set 0.4.0). Se Dados preferir outra definição, por exemplo a ANEEL com o número de UCs no fim do período, mudam a regra, a referência e esta DEC.
- **Em aberto:** confirmar a definição com Dados. Para o FEC, a mesma regra vale com `n_interrupcoes`.

## DEC-033 · DEC e FEC por período e recorte, e a fila de suspeitas paginada

- **Data:** 26/10/2026 · **Área:** Portal · **Autor:** Felipe · **Revisa:** DEC-021 (DEC e FEC só no total)
- **Contexto:** o V1-07 pede as rotas das telas de DEC/FEC (a Beatriz quer os piores alimentadores e regiões para a manutenção
  preventiva) e da fila de perdas (o Rafael quer a fila da mais para a menos promissora, com o motivo e a energia a recuperar, e gera as
  ordens de inspeção a partir dela). Com a `gold_kpis_segmento_mensal` da v0.3 (alimentador na chave), DEC e FEC passam a poder ser
  calculados por recorte.
- **Decisão:**
  - `GET /continuidade/alimentadores/mensal`: a série de DEC e FEC por alimentador, como a Gold calculou (sem recalcular), com
    `inicio`, `fim` e `cod_alimentador` (repetível) opcionais.
  - `GET /continuidade/alimentadores/ranking`: os alimentadores do pior para o melhor num período obrigatório, pelo `criterio`
    `dec` (padrão) ou `fec`.
  - `GET /continuidade/recortes`: DEC e FEC do nível abaixo do filtro, como na decomposição: por município, por bairro de um
    município ou por alimentador de um bairro. `classe` filtra em qualquer nível, e `bairro` sem `municipio` dá `422`.
  - `GET /fila-suspeitas`: a fila por posição no ranking (`score_suspeita`, 1 = mais suspeita), paginada (`pagina`, `tamanho` até 200),
    com `motivos`, `kwh_recuperavel_est` e `ordem_ativa` (a ordem de inspeção gerada ou em campo da UC, se houver).
    `sem_ordem_ativa=true` esconde as UCs que já têm ordem, e o `total` acompanha o filtro.
  - Versão da API 0.6.0.
- **Regra do período** (a do contrato e a da camada semântica do agente): `DEC = Σ horas_interrompidas ÷ média mensal de n_uc`
  e `FEC = Σ n_interrupcoes ÷ média mensal de n_uc`, com a média igual a `Σ n_uc ÷ n_meses`. A conta fica no SQL do backend, num
  único helper usado pelo ranking e pelos recortes; o frontend só exibe. Num mês, o resultado é o `dec` e o `fec` da Gold.
  - **Divisor:** `n_meses` é o número de competências com dado dentro do período, contado na tabela inteira (e não no recorte),
    e a resposta o devolve. Um recorte sem linha num mês conta zero UC nesse mês. Enquanto a Gold cobre o período, o número é o do
    agente; num período que passa do fim dos dados, o DEC não sai subestimado.
  - **Sem divisor:** sem UC atendida no período, `dec` e `fec` são nulos, e o recorte vai para o fim da lista.
- **Motivo:**
  - O DEC é uma média ponderada pelas UCs atendidas: a média dos DEC mensais, ou dos DEC dos alimentadores de um bairro, dá peso
    igual a bases de tamanhos diferentes. Somar os componentes e dividir no fim fecha com o total da empresa (teste com a amostra).
  - O último nível do drill-down é o alimentador, e não a classe: a manutenção preventiva age no circuito, e a Beatriz vê o bairro
    pior e, dentro dele, qual alimentador atacar. O breadcrumb é o da decomposição, e a tela reaproveita a trilha.
  - `ordem_ativa` na fila evita o `409` do `POST /ordens-inspecao`: o Rafael vê "já em campo" antes de clicar, e o filtro traz na
    primeira página o que ainda dá para mandar a campo. O índice único parcial (uma OI ativa por UC) garante que a junção não duplica
    linhas.
- **Alternativas descartadas:**
  - Dividir pelos meses do período pedido, ao pé da letra da camada semântica: um período além dos dados mostraria o DEC menor do
    que é, sem aviso. O GenAI foi avisado para alinhar a regra do agente.
  - Parâmetro livre `agrupar_por`: um bairro sem município é ambíguo (o nome repete entre municípios), e o schema divergiria da
    decomposição.
  - Paginação por cursor: a tela precisa do total e de pular de página, e o OFFSET sobre 45 mil linhas custa pouco. Total em
    cabeçalho: o client gerado não tipa cabeçalho.
  - A tela cruzar a fila com `GET /ordens-inspecao`: a regra ficaria no frontend e a paginação quebraria.
  - Retirar da fila as UCs com ordem: o Rafael perderia a visão completa do ranking.
- **Desempenho (aceite "< 1 s"):** medido com dados sintéticos no pior caso (500 alimentadores × 24 meses, 288 mil linhas de segmentos,
  45.200 suspeitas e 200 ordens ativas), 30 chamadas por rota, pelo `TestClient`:

  | Rota | Mediana | Máximo |
  |---|---|---|
  | Série de um alimentador, 24 meses | 8,5 ms | 51 ms |
  | Série de todos (12.000 linhas) | 206 ms | 265 ms |
  | Ranking dos 500 alimentadores, 24 meses | 21 ms | 28 ms |
  | Recortes por município, 24 meses | 78 ms | 90 ms |
  | Recortes por bairro / por alimentador | 68 ms / 66 ms | 75 ms / 75 ms |
  | Fila, página 1 / última página de 200 | 27 ms / 46 ms | 33 ms / 82 ms |
  | Fila sem ordem ativa | 31 ms | 90 ms |

  Nenhum índice novo. O mais lento é a série completa, e o tempo é da serialização das 12.000 linhas; a tela pede um alimentador
  ou um período.
- **Limitações conhecidas:**
  - O `n_uc` vem como a Gold grava. A discussão do PR #42 sobre excluir do `n_uc` as UCs que nunca são faturadas (UC-12, PRODIST)
    muda o valor gravado, e não a conta da API.
  - `/receita/comparacao` ainda soma a fato com o cadastro atual da UC (DEC-021). Trocá-lo pela `gold_kpis_segmento_mensal` continua
    sendo uma tarefa própria.
- **Consequências:** a DEC-021 deixa de valer na frase "DEC, FEC… não têm recorte por segmento": desde esta decisão eles têm, calculados
  sobre os componentes. O agente continua somando os mesmos componentes, então portal e agente dão o mesmo número.
