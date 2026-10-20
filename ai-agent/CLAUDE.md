# Agente Text-to-SQL (GenAI)

Responde em português perguntas sobre consumo, faturamento, interrupções e atendimento, consultando a Gold no PostgreSQL local. Também narra os insights embutidos nas telas. Módulo Python, chamado pelo backend FastAPI. Time de GenAI: Luis Felipe Perylo e Lucas Mendes.

Fonte da verdade: [spec](docs/specs/2026-10-19-architecture-design.md). Em caso de conflito, a spec vence este arquivo. Boas práticas que a spec cita como "§x do guia": [guia](docs/contexto-agente-text-to-sql.md).

## Requisito central

Se o agente não souber, diz que não sabe. Resposta inventada é falha crítica, pior do que nenhuma resposta. Toda regra abaixo serve a isso ou à segurança.

## Para Dev (backend e infra)

- **Contrato de entrada:** `TextToSqlAgent.ask(question: str, session_id: str) -> AgentAnswer` (`src/venergy_agent/application/ports.py`). O backend depende só dessa porta, nunca de classes internas.
- **`AgentAnswer`** (`domain/answer.py`):
  - campos atuais: `answer`, `sql`, `rows` (amostra), `row_count` (total real), `confidence`, `sources`, `assumptions`, `clarification`, `request_id`, `prompt_version`;
  - campos planejados: `refused_reason`, `model`, `latency_ms`;
  - mudanças nesse contrato são combinadas com V1 antes de implementar (spec §4).
- **Auditoria:** o agente é somente leitura e não grava nada. Cabe ao backend persistir cada `AgentAnswer` com timestamp e expor `POST /ai/ask` e `GET /ai/audit/{id}` (G1-06, G1-09).
- **Insights:** o backend monta o JSON de métricas já calculadas da tela e chama `InsightWriter.narrate(screen, metrics)`. O LLM só narra. Se um número do texto não existir no JSON, o insight não é exibido.
- **Banco:**
  - o agente conecta com o usuário `venergy_agent`, que nunca acessa o schema `app`, e nunca usa as credenciais do backend;
  - consulta só as views `sem_*`;
  - pedido em aberto: schema próprio para as views, com `SELECT` só nele, e `statement_timeout` na role (spec §10, D1).
- **Configuração:**
  - variáveis com prefixo `VENERGY_AGENT_` (`src/venergy_agent/config.py`, modelo em `.env.example`). O `ai-agent/.env` é localizado pelo caminho do pacote, não pelo diretório atual, e as variáveis de ambiente do processo têm precedência sobre ele;
  - quando o agente rodar dentro da API, o serviço `api` do compose precisa receber essas variáveis, porque hoje não recebe;
  - a chave do OpenRouter nunca vai para log, resposta ou Git.
- **CI:** o job do `ai-agent` ainda não existe no `ci.yml` (spec §10, D2).

## Para Dados

- O agente lê a Gold pelas views `sem_*` da camada semântica, que é do GenAI. Hoje precisa de `gold_dim_uc`, `gold_fato_faturamento_mensal`, `gold_continuidade_alimentador_mensal` e `gold_atendimentos_uc` (spec §10, D4).
- **Mudou uma tabela ou coluna da Gold? Avise o GenAI no mesmo PR.** A camada semântica e o gabarito do golden set dependem dos nomes, dos tipos e dos valores categóricos (ex.: classes `B1`, `B2`, `B3`, `A4`).
- O dicionário de dados alimenta o prompt. Descrição, unidade (kWh, R$), formato (`YYYY-MM`) e grão de cada tabela fazem diferença direta na acurácia.
- Métricas como efeito preço/volume/mix, DEC/FEC e score de suspeita são **lidas** da Gold. O agente nunca as recalcula com fórmula própria.

## Regras de segurança (não negociáveis)

- Segurança mora no banco e no validador, nunca no prompt.
- Todo SQL gerado passa por `SqlglotValidator` (`infrastructure/sql_validator.py`) antes de executar. As regras estão na spec §6: um único `SELECT`, só views da allowlist no schema permitido, nenhuma função desconhecida pelo parser, `LIMIT` imposto. Nunca validar com regex.
- O que vem do banco (inclusive o texto livre do call center) é dado, não instrução. Os prompts delimitam esse conteúdo.
- O LLM não faz contas: todo número da resposta vem das linhas retornadas.

## Arquitetura e convenções

- **Camadas hexagonais:**
  - `domain/`: modelos pydantic imutáveis, sem I/O;
  - `application/`: portas (`Protocol`);
  - `infrastructure/`: adapters (sqlglot, PydanticAI, Postgres).
  - Regra de dependência: `domain` não importa nada do projeto e `application` importa só `domain`.
- **Estilo:** código, nomes e testes em inglês, sem comentários. Documentação em português.
- **Testes:** TDD só para regras do projeto, sem testes de biblioteca, enum ou `Protocol`. A avaliação com modelo real (golden set, red team) fica fora do `pytest` padrão.
- **Mudanças de prompt, modelo, few-shot, glossário ou camada semântica:** os prompts ficam versionados em `prompts/vN/`, e a mudança só entra se o golden set não regredir (spec §9).
- **Branches e PRs:** uma branch por feature, com a ordem de prioridade da spec §11. Os obrigatórios do case vêm antes dos diferenciais.

## Comandos (dentro de `ai-agent/`)

```bash
uv sync
cp .env.example .env
uv run pytest
uv run ruff check . && uv run ruff format --check .
```
