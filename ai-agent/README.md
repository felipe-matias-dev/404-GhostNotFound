# Agente de IA

Agente Text-to-SQL em Python, integrado ao backend FastAPI, consultando o banco local alimentado pelas tabelas Gold. Também gera os insights exibidos nas telas do portal.

Já existem os contratos de domínio, as portas, a configuração, o validador SQL, o executor somente leitura e o gerador de SQL. A camada semântica e a orquestração da pergunta (`ask()`) entram em seguida. O spec completo está em [docs/specs/2026-10-19-architecture-design.md](docs/specs/2026-10-19-architecture-design.md), e o guia de boas práticas em [docs/contexto-agente-text-to-sql.md](docs/contexto-agente-text-to-sql.md).

## Arquitetura

Hexagonal, em três camadas:

- `domain/`: modelos imutáveis (perguntas, rascunhos de SQL, camada semântica, respostas). Não importa nada do projeto e não faz I/O.
- `application/`: portas (`typing.Protocol`) que os adapters implementam. Importa só `domain`.
- `infrastructure/`: adapters das portas: validador SQL (`sqlglot`), executor somente leitura (Postgres) e gerador de SQL (PydanticAI, com Gemini direto ou OpenRouter).

Os prompts ficam versionados em `prompts/vN/` (`system.md` e `correction.md`). A versão em uso vem de `VENERGY_AGENT_PROMPT_VERSION`; mudar o prompt é criar uma versão nova e medir no golden set, nunca editar a anterior.

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
3. Não ative cobrança no projeto: ele fica no Free Tier. Os limites do projeto aparecem em *Rate limit*, no AI Studio.

No Free Tier, o Google pode usar o conteúdo enviado para melhorar os produtos dele. Com a amostra sintética não há problema; com a Gold real, use uma chave paga ou fornecida pela organização.

O OpenRouter continua disponível pelo prefixo `openrouter:` (veja `.env.example`). Os testes não usam nenhuma chave: o modelo é simulado.
