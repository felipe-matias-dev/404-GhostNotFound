# Agente de IA

Agente Text-to-SQL em Python, integrado ao backend FastAPI, consultando o banco local alimentado pelas tabelas Gold. Também gera os insights exibidos nas telas do portal.

Esta etapa cobre só o esqueleto: contratos de domínio, portas e configuração. Os adapters (LLM, validador, banco e camada semântica) entram em seguida. O spec completo está em [docs/specs/2026-10-19-architecture-design.md](docs/specs/2026-10-19-architecture-design.md).

## Arquitetura

Hexagonal, em três camadas:

- `domain/`: modelos imutáveis (perguntas, rascunhos de SQL, camada semântica, respostas). Não importa nada do projeto e não faz I/O.
- `application/`: portas (`typing.Protocol`) que os adapters implementam. Importa só `domain`.
- `infrastructure/`: adapters das portas. Ainda vazio.

## Como rodar

Dentro de `ai-agent/`:

```bash
uv sync
cp .env.example .env   # preencha a chave do OpenRouter e a URL do banco
uv run pytest
uv run ruff check . && uv run ruff format --check .
```

As configurações são lidas de variáveis com prefixo `VENERGY_AGENT_` (ou do `.env`), conforme `src/venergy_agent/config.py`. O `.env` não vai para o Git.
