# Agente Text-to-SQL (GenAI)

Responde em português perguntas sobre consumo, faturamento, interrupções e atendimento, consultando a Gold no PostgreSQL local. Também narra os insights embutidos nas telas. Módulo Python, chamado pelo backend FastAPI. Time de GenAI: Luis Felipe Perylo e Lucas Mendes.

Fonte da verdade: [spec](docs/specs/2026-10-19-architecture-design.md). Em caso de conflito, a spec vence este arquivo. Boas práticas que a spec cita como "§x do guia": [guia](docs/contexto-agente-text-to-sql.md).

## Requisito central

Se o agente não souber, diz que não sabe. Resposta inventada é falha crítica, pior do que nenhuma resposta. Toda regra abaixo serve a isso ou à segurança.

## Para Dev (backend e infra)

- **Contrato de entrada:** `TextToSqlAgent.ask(question: str, session_id: str) -> AgentAnswer` (`src/venergy_agent/application/ports.py`). O backend depende só dessa porta, nunca de classes internas.
- **`AgentAnswer`** (`domain/answer.py`):
  - campos: `answer`, `status` (`answered`, `unknown`, `clarify`, `refused`, `failed`), `sql`, `rows` (amostra), `row_count` (total real), `truncated`, `confidence`, `sources`, `assumptions`, `clarification`, `refused_reason`, `request_id`, `model`, `prompt_version`, `latency_ms`;
  - as invariantes por status estão na spec §4 e têm teste em `tests/unit/domain/test_answer.py`;
  - o `ask()` nunca levanta exceção: toda falha volta como `AgentAnswer` com `status`;
  - mudanças nesse contrato são combinadas com V1 antes de implementar (spec §4).
- **Auditoria:** o agente é somente leitura e não grava nada. Cabe ao backend persistir cada `AgentAnswer` com timestamp e expor `POST /ai/ask` e `GET /ai/audit/{id}` (G1-06, G1-09).
- **Insights:** o backend monta o JSON de métricas já calculadas da tela, chama `InsightWriter.narrate(screen, metrics)` e guarda o insight em cache por combinação de filtros (spec §10, D9). O LLM só narra. Se um número do texto não existir no JSON, o agente devolve `None` e a tela aparece sem insight.
- **Banco:**
  - o agente conecta com o usuário `venergy_agent`, que nunca acessa o schema `app`, e nunca usa as credenciais do backend;
  - consulta só as views `sem_*`;
  - pedido em aberto: schema próprio para as views, com `SELECT` só nele, e `statement_timeout` na role (spec §10, D1). Até lá, as views ficam no schema `gold`;
  - o SQL das views é gerado pelo GenAI em `ai-agent/semantic/views.sql` e aplicado pelo loader com o usuário dono (spec §10, D7).
- **Configuração:**
  - variáveis com prefixo `VENERGY_AGENT_` (`src/venergy_agent/config.py`, modelo em `.env.example`). O `ai-agent/.env` é localizado pelo caminho do pacote, não pelo diretório atual, e as variáveis de ambiente do processo têm precedência sobre ele;
  - dentro da API, o serviço `api` do compose recebe `VENERGY_AGENT_DATABASE_URL` e `VENERGY_AGENT_GOOGLE_API_KEY` (de `GOOGLE_API_KEY` no `.env` da raiz);
  - backend e agente formam um workspace do uv com um único `uv.lock` na raiz (DEC-017): dependência nova é `uv add` dentro de `ai-agent/`, e o lock atualizado é o da raiz;
  - cada integrante usa a própria chave do Gemini (`VENERGY_AGENT_GOOGLE_API_KEY`) ou do OpenRouter; nenhuma chave vai para log, resposta ou Git.
- **CI:** o job "Agente de IA (pytest)" do `ci.yml` roda os testes do agente, inclusive os de integração contra o Postgres do compose.

## Para Dados

- O agente lê a Gold pelas views `sem_*` da camada semântica, que é do GenAI. Quem escolhe tabelas e colunas é o arquivo `ai-agent/semantic/semantic_layer.yaml`, validado contra `contracts/gold_schema.yaml`; o campo `consumers` do contrato é informativo. Colunas `a_confirmar` ficam de fora.
- A primeira versão usa `gold_dim_uc`, `gold_fato_faturamento_mensal` e `gold_continuidade_alimentador_mensal`; `gold_receita_decomposicao` entra quando `periodo_base` e `periodo_atual` forem confirmados (spec §10, D4, e §11, item 5).
- Nenhum dado real da Gold vai para o prompt fixo: as linhas de exemplo são sintéticas, escritas pelo GenAI.
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
- **Mudanças de prompt, modelo, few-shot, glossário ou camada semântica:** os prompts ficam versionados em `prompts/vN/`; mudança de prompt vai para uma versão nova, e a partir da primeira execução do golden set nenhuma dessas mudanças entra se ele regredir (spec §9.5, DEC-016).
- **Branches e PRs:** uma branch e um plano (`docs/plans/`) por feature, na ordem de execução da spec §11 (5 → 2 → 6 → 7 → 8 → 9). Os obrigatórios do case vêm antes dos diferenciais.

## Comandos (dentro de `ai-agent/`)

```bash
uv sync
cp .env.example .env
uv run pytest
uv run ruff check . && uv run ruff format --check .
```
