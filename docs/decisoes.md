# Decisões e suposições

Registro das decisões tomadas pelo time onde os requisitos do case não eram explícitos. Alimenta a seção de suposições do README.

| Data | Decisão | Motivo | Quem |
|---|---|---|---|
| 19/10/2026 | DEC-001: arquivos de origem em `v_energy.default.landing`; `bronze` só com tabelas | Separa arquivos imutáveis de tabelas recriáveis | Arthur |
| 19/10/2026 | DEC-002: banco local SQLite, acessado via SQLAlchemy | Roda no clone limpo sem instalar nada; modo somente leitura nativo para o agente | Felipe |
| 19/10/2026 | DEC-003: walking skeleton com amostra sintética da Gold | Integração entre camadas testada desde o início, sem depender do dataset confidencial | Time |
| 19/10/2026 | DEC-004 (proposta): Gold entregue em CSV, um arquivo por tabela, em `data/gold/` | Um único caminho de carga, validado contra o contrato, para amostra e Gold real | Felipe |

## DEC-001 · Localização dos arquivos de origem (landing)

- **Data:** 19/10/2026 · **Área:** Dados · **Autor:** Arthur
- **Decisão:** os arquivos brutos ficam no volume `v_energy.default.landing`
  (`/Volumes/v_energy/default/landing/`). O schema `v_energy.bronze` contém
  apenas tabelas Delta.
- **Motivo:** separar arquivos imutáveis de tabelas recriáveis. Com o volume
  dentro de `bronze`, um `DROP SCHEMA bronze CASCADE` apagaria os originais.
- **Regras:** o pipeline nunca escreve nem apaga nada em `landing`. O caminho
  é parametrizado por widget no notebook `landing_to_bronze`.

## DEC-002 · Banco local SQLite

- **Data:** 19/10/2026 · **Área:** Portal · **Autor:** Felipe
- **Decisão:** o banco local é um arquivo SQLite em `data/venergy.db`, na raiz do
  repositório e fora do Git. O backend acessa o banco pelo SQLAlchemy 2.0.
- **Motivo:** funciona a partir de um clone limpo sem instalar servidor de banco,
  a Gold é agregada e cabe bem num arquivo, e o SQLite oferece modo somente
  leitura nativo, usado pelo agente de IA.
- **Alternativa descartada:** PostgreSQL, que exigiria servidor ou Docker em
  cada máquina, inclusive na da banca.
- **Regras:** o backend lê e escreve (as ordens de inspeção vão precisar). O
  agente de IA conecta em modo somente leitura (`?mode=ro`). Trocar de banco
  exige só mudar `VENERGY_API_DATABASE_URL`, porque nenhuma consulta é escrita
  no dialeto do SQLite.

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
  nome da tabela (`uc_resumo.csv`), em UTF-8, separado por vírgula, com
  cabeçalho e booleanos como `true`/`false`. Os arquivos ficam em `data/gold/`,
  fora do Git, e são carregados por `uv run python -m venergy_api.carga`.
- **Motivo:** amostra e Gold real percorrem o mesmo caminho, então trocar uma
  pela outra não muda código.
- **Regras:** a carga valida todas as linhas contra o contrato
  (`backend/src/venergy_api/schemas.py`) antes de gravar e substitui as tabelas
  numa única transação. Um arquivo fora do contrato cancela a carga e mantém os
  dados anteriores. Nem os dados brutos nem os CSVs da Gold são versionados.
- **Em aberto:** confirmar com a organização se a Gold agregada pode ir para o
  repositório público. Até lá, não é versionada.
