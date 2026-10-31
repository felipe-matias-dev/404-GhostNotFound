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

**Recarga da Gold (spec §10, D7):** a carga apaga as views `sem_*` e as aplica de novo na mesma transação, então não há passo manual. Para aplicar `semantic/views.sql` à mão num banco que já tem as views, apague-as antes: `CREATE OR REPLACE VIEW` não muda o tipo de uma coluna.

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

Da raiz do repositório:

```bash
make eval                                  # os dois conjuntos, na amostra
make eval ONLY=red_team                    # só o red team
make eval SQL_ONLY=1                       # sem o redator: menos cota
make eval ONLY=references DATASET=gold_real  # só confere as referências do golden na base carregada, sem modelo
make eval DATASET=gold_real                # Gold real, com redator (relatório fora do Git)
make eval JUDGE=1                          # com o juiz, só na amostra narrada
make eval-compare A=eval/runs/a.json B=eval/runs/b.json
```

O `make eval` chama `python -m venergy_agent.evaluation` com `--dataset`, `--only`, `--judge` e `--sql-only`. Os caminhos do `eval-compare` são relativos a `ai-agent/`. Sem o `make`, rode os dois módulos com `uv run python -m` dentro de `ai-agent/`.

Antes de chamar o modelo, a avaliação confere que o banco carregado é a base declarada em `--dataset` (pelo número de UCs em `sem_uc`) e para se não for. Com `--sql-only` o agente não monta o redator, e a fidelidade numérica fica fora; use quando a mudança não toca a narração, para gastar menos cota. Na Gold real, o relatório vai para `eval/runs_gold/`, fora do Git, porque o SQL e a justificativa do juiz podem trazer valores do dataset (DEC-024, DEC-015). Na correção de SQL, a mensagem de erro de dado volta ao modelo só com o tipo do erro, sem o valor.

Cada execução grava `eval/runs/<data>.json`, com as métricas da spec §9.3 (execution accuracy, acurácia de status, taxa de recusa correta, violações de segurança e latência), e imprime a tabela. A linha de base e os achados estão na spec §9.6. Mudanças de prompt, modelo, few-shot ou camada semântica só entram se a execution accuracy e a acurácia de status não regredirem (DEC-016).

Os itens de follow-up (`follow_up_of`) rodam logo depois da pergunta de origem, em sequência, numa sessão por cadeia (`eval-<rodada>-<item raiz>`); os demais itens e os ataques do red team ganham uma sessão cada. Um follow-up sem a pergunta de origem na rodada (outra base, ou `--only red_team`) não roda e conta em `follow_up_skipped`.

### Comparar rodadas

`make eval-compare` não chama o modelo. Imprime em markdown a configuração das duas rodadas (modelo, `prompt_version`, camada semântica, versões dos conjuntos, base, narrada e juiz), as métricas lado a lado com a diferença (taxas em pontos percentuais, contagens e latência em valor absoluto) e os itens em comum que mudaram de `matched`, `status`, `numeric_fidelity` ou `judge_passed`. As métricas são recalculadas só sobre os itens em comum, para que uma versão nova do golden set não distorça a comparação; a tabela diz quantos itens existem só em A e só em B. Se uma rodada tem mais de 5% de itens `failed`, a saída avisa que a comparação provavelmente não vale (erro do provedor, abaixo).

Última rodada válida, comparada com a linha de base (nenhuma das duas teve `failed`):

| Métrica (82 itens em comum) | 24/10/2026 (linha de base) | 28/10/2026 | Diferença |
|---|---|---|---|
| execution_accuracy | 72.2% | 100.0% | +27.8 pp |
| status_accuracy | 86.2% | 95.4% | +9.2 pp |
| status_accuracy_unknown | 72.7% | 100.0% | +27.3 pp |
| refusal_accuracy | 92.0% | 88.0% | -4.0 pp |
| manipulation_block_rate | 100.0% | 100.0% | +0.0 pp |
| numeric_fidelity | 66.7% | 69.0% | +2.4 pp |
| latency_p50_ms | 1014 | 2935 | +1921 |
| latency_p95_ms | 9585 | 11392 | +1807 |

Configuração: `google-gla:gemini-3.1-flash-lite`, `prompt_version` v2, narrada, base `amostra`. A linha de base usou a camada 0.2.0 e a de 28/10, a 0.4.0 e o golden set 0.9.0 (a de 24/10 não registrou a versão do golden set).

### Juiz (`--judge`)

Avalia clareza e fidelidade da resposta em português (spec §9.4), com a rubrica `prompts/judge/v1/judge.md` e o modelo `VENERGY_AGENT_JUDGE_MODEL`, que precisa ser diferente do `LLM_MODEL` e do `FALLBACK_MODEL` e usa a chave do próprio provedor. Só julga itens `answered` de rodada narrada, na amostra ou na Gold real: `--judge` com `--sql-only` é recusado. O relatório ganha `judge_score`, `judge_passed` e `judge_rationale` (até 300 caracteres) por item e `judge_pass_rate`, `judge_mean_score`, `judge_items` e `judge_errors` nas métricas. O juiz ainda não foi calibrado com uma pessoa: o resultado dele não decide merge (spec §9.4).

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

## Memória e orçamento

Follow-up ("e em Olinda?" depois de uma pergunta sobre Recife) e orçamento de tokens, o histórico por `session_id` e o orçamento por usuário (G1-10, DEC-046).

| Variável | Para quê |
|---|---|
| `VENERGY_AGENT_HISTORY_TURNS` | Turnos anteriores da sessão que o gerador de SQL recebe. Padrão `3`, `0` desliga a memória |
| `VENERGY_AGENT_SESSION_TOKEN_BUDGET` | Tokens (entrada + saída do gerador de SQL) que cada usuário pode gastar na API (no agente isolado, cada sessão). Padrão `200000`, `0` desliga. Esgotado, o agente responde `refused` sem chamar o modelo |
| `VENERGY_AGENT_PROMPT_VERSION` | `v3` (padrão) lê o histórico; `v2` e `v1` o ignoram |

- O histórico vem da auditoria do backend (`app.ai_auditoria`), e não do agente: o usuário `venergy_agent` nunca lê o schema `app`. O agente isolado (terminal, avaliação) só tem memória com o adapter em memória (`InMemoryConversationHistory`).
- Turnos recusados nunca entram no histórico. O histórico é dado delimitado, nunca instrução.
- O backend responde `429` em `POST /ai/ask` quando o usuário passa de `VENERGY_API_AI_LIMITE_PERGUNTAS` perguntas (padrão 20) em `VENERGY_API_AI_JANELA_SEGUNDOS` (padrão 600); `0` desliga.
- A auditoria ganhou `input_tokens` e `output_tokens`. A subida da API e a carga da Gold as acrescentam a um banco antigo sozinhas (`ADD COLUMN IF NOT EXISTS`, sem tocar nas linhas): não há passo manual.
- Com o login (DEC-049), o limite e o orçamento valem por usuário, em todas as sessões dele: omitir ou trocar o `session_id` não zera nada. Um `session_id` de outro usuário responde `403` sem chamar o agente.

## Chave do modelo

Cada integrante usa a própria chave, no próprio `ai-agent/.env` (fora do Git):

1. Entre em https://aistudio.google.com com a sua conta Google, vá em **Get API key** e crie uma chave.
2. Preencha `VENERGY_AGENT_GOOGLE_API_KEY` no `ai-agent/.env`. O modelo padrão já é `google-gla:gemini-3.1-flash-lite`.
3. Mantenha o projeto no Free Tier, sem ativar cobrança. Os limites aparecem em *Rate limit*, no AI Studio.

No Free Tier, o Google pode usar o conteúdo enviado para melhorar os produtos dele. O time aceita esse envio para a amostra e para a Gold real (DEC-015): o dataset é do case. O que nunca pode acontecer é o dataset, ou qualquer saída com dados dele, ir para o Git (DEC-024).

O OpenRouter continua disponível pelo prefixo `openrouter:` (veja `.env.example`). Os testes não usam nenhuma chave: o modelo é simulado.

### Modelo reserva

Na API do `docker compose`, o agente sobe com um modelo reserva: `VENERGY_AGENT_FALLBACK_MODEL`, padrão `google-gla:gemini-3.5-flash` (troque por `GEMINI_FALLBACK_MODEL` no `.env` da raiz). Se o modelo principal falhar com 429 (cota) ou 503 (sobrecarga) depois das retentativas, a mesma pergunta vai para o reserva. No plano gratuito a cota é contada por modelo, então o reserva tem cota própria.

A variável aceita uma **cadeia**, separada por vírgula, tentada em ordem. Com a chave do OpenRouter (`OPENROUTER_API_KEY` no `.env` da raiz), a cadeia pode seguir para outro provedor e cobrir uma queda do Gemini inteiro:

```
GEMINI_FALLBACK_MODEL=google-gla:gemini-3.5-flash,openrouter:nvidia/nemotron-3.5-super-vl:free,openrouter:google/gemma-4-31b-it:free
```

- Os modelos `:free` do OpenRouter têm limite de 50 chamadas por dia por conta e são instáveis (no teste de 29/10, `gemma-4-31b` deu 429 e outros deram 503); por isso a cadeia tem mais de um. O `nemotron-3.5-super-vl` acertou o SQL das perguntas de teste, mas leva cerca de 40 s por chamada: serve de última linha, não de reserva do dia a dia.
- Só entram modelos com *tool calling* (o agente devolve saída estruturada).
- Um modelo `openrouter:` na cadeia exige a chave do OpenRouter: sem ela, o agente não sobe (o `/ai` responde 503). O padrão do compose é só Gemini por isso.
- Nenhum modelo da cadeia pode ser igual ao do juiz (`VENERGY_AGENT_JUDGE_MODEL`, padrão `gemini-3.5-flash-lite`).
- Fora do compose (`python -m venergy_agent`, avaliação), a cadeia vem do `ai-agent/.env`.

### Dia da apresentação

- Use a chave de quem não rodou nada no dia; a cota renova por volta das 4h (horário de Brasília). Leve a chave de outro integrante como segunda opção: trocar o `GOOGLE_API_KEY` no `.env` da raiz e reiniciar a API leva menos de um minuto.
- Não rode avaliação no dia: uma rodada do golden set gasta de 90 a 140 chamadas. Uma pergunta ao agente gasta cerca de 2 (SQL e narração), e um insight de tela, 1 por combinação de filtros (fica em cache).
- Antes de começar, faça uma pergunta de teste pelo portal ou pelo `POST /ai/ask`. A resposta mostra o `model` que respondeu: se for o reserva, o principal está sem cota.
