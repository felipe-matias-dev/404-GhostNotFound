# Agente de IA

Agente Text-to-SQL em Python, integrado ao backend FastAPI, consultando o banco local alimentado pelas tabelas Gold. Também gera os insights exibidos nas telas do portal.

Já existem os contratos de domínio, as portas, a configuração, o validador SQL, o executor somente leitura e o gerador de SQL. A camada semântica e a orquestração da pergunta (`ask()`) entram em seguida. O spec completo está em [docs/specs/2026-10-19-architecture-design.md](docs/specs/2026-10-19-architecture-design.md), e o guia de boas práticas em [docs/contexto-agente-text-to-sql.md](docs/contexto-agente-text-to-sql.md).

## Arquitetura

Hexagonal, em três camadas:

- `domain/`: modelos imutáveis (perguntas, rascunhos de SQL, camada semântica, respostas). Não importa nada do projeto e não faz I/O.
- `application/`: portas (`typing.Protocol`) que os adapters implementam. Importa só `domain`.
- `infrastructure/`: adapters das portas: validador SQL (`sqlglot`), executor somente leitura (Postgres) e gerador de SQL (PydanticAI, com Gemini direto ou OpenRouter).

Os prompts ficam versionados em `prompts/vN/` (`system.md` e `correction.md`). A versão em uso vem de `VENERGY_AGENT_PROMPT_VERSION`; mudar o prompt é criar uma versão nova e medir no golden set, nunca editar a anterior.

### Camada semântica

`semantic/semantic_layer.yaml` é do GenAI. Ele escolhe as views `sem_*`, as colunas, a descrição, o glossário, as regras e os exemplos. Cada view é validada contra [contracts/gold_schema.yaml](../contracts/gold_schema.yaml):

- a tabela e a coluna existem no contrato;
- a tabela tem `agente` em `consumers` (DEC-022);
- coluna marcada `a_confirmar` ou `sensitive: true` não entra;
- a chave primária da tabela está confirmada ou proposta e aparece na view.

As relações entre views saem das chaves estrangeiras e das chaves de entidade (`cod_uc`, `cod_alimentador`). Competência não vira relação, porque juntar só por período gera produto cartesiano (DEC-018).

Depois de mudar o YAML, regere o SQL das views:

```bash
uv run python -m venergy_agent.infrastructure.views_sql          # regera semantic/views.sql
uv run python -m venergy_agent.infrastructure.views_sql --check  # falha se estiver desatualizado
```

**Recarga da Gold (spec §10, D7):** a carga recria as tabelas, e isso falha enquanto houver view dependente. Antes de recarregar, apague as views `sem_*`, e aplique `semantic/views.sql` de novo depois da carga.

## Como rodar

Dentro de `ai-agent/`:

```bash
uv sync
cp .env.example .env   # preencha a sua chave do Gemini e a URL do banco
uv run pytest          # os testes de integração precisam do banco: docker compose up -d --wait db (na raiz)
uv run ruff check . && uv run ruff format --check .
```

As configurações são lidas de variáveis com prefixo `VENERGY_AGENT_` (ou do `.env`), conforme `src/venergy_agent/config.py`. O `.env` não vai para o Git.

## Chave do modelo

Cada integrante usa a própria chave, no próprio `ai-agent/.env` (fora do Git):

1. Entre em https://aistudio.google.com com a sua conta Google, vá em **Get API key** e crie uma chave.
2. Preencha `VENERGY_AGENT_GOOGLE_API_KEY` no `ai-agent/.env`. O modelo padrão já é `google-gla:gemini-3.1-flash-lite`.
3. Para a amostra sintética, mantenha o projeto no Free Tier, sem ativar cobrança. Os limites aparecem em *Rate limit*, no AI Studio.

No Free Tier, o Google pode usar o conteúdo enviado para melhorar os produtos dele. Por isso, o plano gratuito serve para a amostra sintética. Para a Gold real, a regra ainda não foi decidida pelo time: até decidir, não envie a Gold real pelo plano gratuito.

O OpenRouter continua disponível pelo prefixo `openrouter:` (veja `.env.example`). Os testes não usam nenhuma chave: o modelo é simulado.
