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
| 19/10/2026 | DEC-005: Bronze com auditoria básica (full refresh, tudo string, `ingestion_timestamp` e `source_file`) | Dados o mais próximos da origem; rastreabilidade sem log próprio de ingestão | Alisson |

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
- **Em aberto:** confirmar com a organização se a Gold agregada pode ir para o
  repositório público. Até lá, não é versionada.

## DEC-005 · Contrato da Bronze (auditoria básica)

- **Data:** 19/10/2026 · **Área:** Dados · **Autor:** Alisson
- **Decisão:** uma tabela Delta por fonte lógica em `v_energy.bronze.<fonte>`,
  com o nome da fonte em snake_case, sem prefixo (ex.: `unidades_consumidoras`).
  Colunas originais, com os nomes originais e do tipo string, mais
  `source_file` (de `_metadata.file_path`) e `ingestion_timestamp`.
- **Carga:** batch, full refresh, `overwrite` do Delta com um único overwrite por
  tabela. Reexecutar sobre os mesmos arquivos não duplica nem perde linhas.
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
