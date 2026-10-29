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

Para fazer uma pergunta pelo terminal, com a chave do modelo no `.env` e as views `sem_*` aplicadas no banco:

```bash
uv run python -m venergy_agent "Quantas UCs existem em cada classe de consumo?"
```

O backend monta o agente com `venergy_agent.bootstrap.build_agent(AgentSettings())`, uma vez por processo: erro na camada semântica, no contrato ou no prompt falha na subida.

As configurações são lidas de variáveis com prefixo `VENERGY_AGENT_` (ou do `.env`), conforme `src/venergy_agent/config.py`. O `.env` não vai para o Git.

## Avaliação

O golden set (`eval/golden_set.yaml`) e o red team (`eval/red_team.yaml`) rodam com o modelo real. A avaliação é paga e lenta, e fica fora do `pytest`. Precisa do banco com a amostra carregada e das views `sem_*`, aplicadas pela carga do backend.

```bash
uv run python -m venergy_agent.evaluation                       # os dois conjuntos, na amostra
uv run python -m venergy_agent.evaluation --only red_team        # só o red team
uv run python -m venergy_agent.evaluation --sql-only             # sem o redator: menos cota
uv run python -m venergy_agent.evaluation --dataset gold_real    # Gold real (sempre só SQL)
```

Antes de chamar o modelo, a avaliação confere que o banco carregado é a base declarada em `--dataset` (pelo número de UCs em `sem_uc`) e para se não for. Com `--sql-only` o agente não monta o redator: nenhuma linha do banco vai ao modelo, e a fidelidade numérica fica fora. A Gold real roda sempre assim, e o relatório vai para `eval/runs_gold/`, fora do Git (issue #56, DEC-015). Na correção de SQL, a mensagem de erro de dado volta ao modelo só com o tipo do erro, sem o valor.

Cada execução grava `eval/runs/<data>.json`, com as métricas da spec §9.3, e imprime a tabela. A linha de base e os achados estão na spec §9.6. Mudanças de prompt, modelo, few-shot ou camada semântica só entram se a execution accuracy e a acurácia de status não regredirem (DEC-016).

### Antes de rodar a avaliação na amostra

Carregue a amostra sintética no banco local, a partir de `backend/` (com `VENERGY_API_DATABASE_URL` apontando para o banco e `VENERGY_API_GOLD_DIR` para `data/gold`):

```bash
uv run python -m venergy_api.amostra --force
uv run python -m venergy_api.carga
```

A carga recria as tabelas `gold_*` e aplica as views `sem_*` do arquivo `semantic/views.sql`, numa única transação.

### Erros do provedor (503 e 429)

O Gemini responde 503 (sobrecarga) ou 429 (limite de taxa) com frequência. Uma rodada só vale para a decisão se **não tiver nenhum** desses erros. Se tiver, descarte-a, guarde o log e rode de novo quando o serviço estiver estável. Um erro de provedor não é erro do agente, e não deve entrar nas métricas como se fosse.

### Gold real

Não está no Git. Os 12 CSVs ficam no Volume do Databricks (`/Volumes/v_energy/gold/csv`). Para a rodada da Gold real:

1. Baixe os CSVs para `data/gold/` na raiz do projeto (a pasta está no `.gitignore`).
2. Rode a carga com `VENERGY_API_GOLD_DIR` apontando para essa pasta, a partir de `backend/`: `uv run python -m venergy_api.carga`. Isso substitui a amostra no banco local.
3. Confirme que o banco é a Gold real: `sem_uc` tem bem mais de 1000 UCs.
4. Rode `uv run python -m venergy_agent.evaluation --dataset gold_real`.

Para voltar à amostra, rode de novo `venergy_api.amostra --force` e `venergy_api.carga`.

## Memória e orçamento por sessão

Follow-up ("e em Olinda?" depois de uma pergunta sobre Recife) e orçamento de tokens, ambos por `session_id` (G1-10, DEC-046).

| Variável | Para quê |
|---|---|
| `VENERGY_AGENT_HISTORY_TURNS` | Turnos anteriores da sessão que o gerador de SQL recebe. Padrão `3`, `0` desliga a memória |
| `VENERGY_AGENT_SESSION_TOKEN_BUDGET` | Tokens (entrada + saída do gerador de SQL) que uma sessão pode gastar. Padrão `200000`, `0` desliga. Esgotado, o agente responde `refused` sem chamar o modelo |
| `VENERGY_AGENT_PROMPT_VERSION` | `v3` (padrão) lê o histórico; `v2` e `v1` o ignoram |

- O histórico vem da auditoria do backend (`app.ai_auditoria`), e não do agente: o usuário `venergy_agent` nunca lê o schema `app`. O agente isolado (terminal, avaliação) só tem memória com o adapter em memória (`InMemoryConversationHistory`).
- Turnos recusados nunca entram no histórico. O histórico é dado delimitado, nunca instrução.
- O backend responde `429` em `POST /ai/ask` quando a sessão passa de `VENERGY_API_AI_LIMITE_PERGUNTAS` perguntas (padrão 20) em `VENERGY_API_AI_JANELA_SEGUNDOS` (padrão 600); `0` desliga.
- A auditoria ganhou `input_tokens` e `output_tokens`. A subida da API e a carga da Gold as acrescentam a um banco antigo sozinhas (`ADD COLUMN IF NOT EXISTS`, sem tocar nas linhas): não há passo manual.
- Limitação: sem autenticação, o `session_id` é escolhido pelo cliente; trocar de sessão zera o limite e o orçamento. É trava de custo e de abuso acidental, não de segurança.

## Chave do modelo

Cada integrante usa a própria chave, no próprio `ai-agent/.env` (fora do Git):

1. Entre em https://aistudio.google.com com a sua conta Google, vá em **Get API key** e crie uma chave.
2. Preencha `VENERGY_AGENT_GOOGLE_API_KEY` no `ai-agent/.env`. O modelo padrão já é `google-gla:gemini-3.1-flash-lite`.
3. Para a amostra sintética, mantenha o projeto no Free Tier, sem ativar cobrança. Os limites aparecem em *Rate limit*, no AI Studio.

No Free Tier, o Google pode usar o conteúdo enviado para melhorar os produtos dele. Por isso, o plano gratuito serve para a amostra sintética. Para a Gold real, a regra ainda não foi decidida pelo time: até decidir, não envie a Gold real pelo plano gratuito.

O OpenRouter continua disponível pelo prefixo `openrouter:` (veja `.env.example`). Os testes não usam nenhuma chave: o modelo é simulado.
