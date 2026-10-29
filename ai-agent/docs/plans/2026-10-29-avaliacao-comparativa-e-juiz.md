# Avaliação comparativa (G2-08) e LLM as a judge (§9.4): plano de implementação

**Objetivo:** fechar o G2-08 (avaliação automatizada com tabela comparativa de experimentos) e entregar o código do juiz da §9.4 da spec, sem rodar o modelo (sem cota). De quebra, o runner passa a executar os itens de follow-up em sequência na mesma sessão, que é a parte de avaliação do G1-10 (a memória em si é da trilha B).

**Branch e worktree:** `feat/ai-agent-avaliacao-comparativa-juiz`, em `/Users/lipeperylo/Documents/Workspace/03_Projetos/Rocket/case/404-wt-avaliacao` (base: `main`). Trilha paralela: B (`feat/ai-agent-memoria-orcamento`, plano `2026-10-29-memoria-e-orcamento.md`).

**Spec:** `ai-agent/docs/specs/2026-10-19-architecture-design.md` §7, §9.3, §9.4, §9.5, §11. Backlog: G2-08 e G1-10 (`docs/backlog.md`). DEC-015, DEC-016, DEC-024, issue #56.

## Aceite

1. `make eval` roda golden set e red team e imprime execution accuracy, acurácia de status, taxa de recusa correta, violações de segurança e latência (aceite do G2-08); repassa `DATASET`, `ONLY` e `JUDGE`.
2. `make eval-compare A=... B=...` (que chama `python -m venergy_agent.evaluation.compare A.json B.json`) imprime uma tabela markdown, sem chamar modelo:
   - cabeçalho com a configuração das duas rodadas (modelo, `prompt_version`, camada, `golden_version`, `red_team_version`, base, narrada, juiz);
   - métricas lado a lado com a diferença, recalculadas só sobre os itens em comum;
   - quantos itens existem só em A e só em B (quando `golden_version` ou o recorte diferem);
   - itens em comum que mudaram em `matched`, `status`, `numeric_fidelity` ou `judge_passed`;
   - aviso quando uma rodada tem `failed` acima do limite (provável erro de provedor: a comparação não vale, README "Erros do provedor").
3. O runner executa cada cadeia de follow-up (`follow_up_of`) em sequência, numa sessão própria; itens independentes ganham uma sessão cada. Um `recorder` opcional recebe cada turno (é por ele que a trilha B liga a memória na avaliação).
4. Juiz: `JudgeVerdict(score 1–5, passed, rationale)`, porta `AnswerJudge`, adapter PydanticAI, rubrica `prompts/judge/v1/judge.md`, `judge_model` diferente do `llm_model` (validado em `AgentSettings`), flag `--judge` desligada por padrão e recusada com `--dataset gold_real` e com `--sql-only`. Campos do juiz por item, métricas agregadas e colunas na comparação.
5. README do agente com a seção de avaliação atualizada e a tabela da última rodada válida (resultado no README, aceite do G2-08).
6. `uv run pytest -q` e `uv run ruff check . && uv run ruff format --check .` passam em `ai-agent/`.

## Regras para o implementador

- Código, nomes e testes em inglês, **sem comentários** no código do `ai-agent`; documentação em português. Siga a densidade do código vizinho (`runner.py`, `insight_writer.py`, `__main__.py`).
- TDD só para regras do projeto: nada de testar enum, `Protocol`, `Field(ge=...)` do Pydantic ou o próprio PydanticAI. Testes nunca chamam o modelo real (use `FunctionModel` ou fakes) e não precisam de chave.
- Camadas: `domain` não importa o projeto; `application` só importa `domain`; adapters em `infrastructure`; o pacote `evaluation` consome portas e é composition root da avaliação (como já é hoje).
- Segurança: pergunta, resposta e linhas chegam ao juiz delimitadas com nonce (`delimited` de `prompt_renderer.py`), como nos outros prompts. Nenhuma chave em log, relatório ou Git. Linhas da Gold real nunca vão ao juiz (DEC-015, issue #56).
- O relatório continua sem linhas e sem o texto da resposta (DEC-024). O `rationale` do juiz entra no relatório só porque o juiz roda apenas na amostra sintética; corte em 300 caracteres.
- Commits locais, Conventional Commits, **sem linha `Co-Authored-By`**. Sem push e sem PR.
- Se o import falhar no macOS: `chflags -R nohidden /Users/lipeperylo/Documents/Workspace/03_Projetos/Rocket/case/404-wt-avaliacao/.venv`.

## Decisões e alternativas descartadas

- **Métricas comparadas sobre a interseção dos itens**, sempre recalculadas a partir de `items` com a mesma função do runner (`compute_metrics`). As métricas da rodada que não saem dos itens (`writes_accepted`, `views_changed`, `red_team_violations`, `follow_up_skipped`, `other_dataset_skipped`) aparecem como estão no relatório, num bloco "da rodada". Descartado: comparar os `metrics` gravados, que misturam conjuntos diferentes quando a versão do golden set muda.
- **Aviso de `failed`:** acima de 5% (`FAILED_WARNING_RATE = 0.05`) em qualquer lado. O relatório não guarda o tipo de erro; `failed` em massa é o sintoma conhecido de 429/503 (§9.6).
- **Diferença:** taxas em pontos percentuais (`+2.7 pp`), contagens e latência em valor absoluto (`+120`), `—` quando um lado é nulo. Mesmo estilo do `format_metrics` (`70.3%`).
- **Nova métrica `refusal_accuracy`:** itens com `expected_status = refused` (golden e red team) que terminaram `refused`. É a "taxa de recusa correta" do aceite do G2-08; o `manipulation_block_rate` mede vazamento, não recusa.
- **Juiz só em itens `answered` de rodada narrada.** `unknown`, `refused` e `failed` são textos fixos, sem LLM (§5.1, item 8): julgar seria medir constante. Sem narrativa (`--sql-only`) não há o que julgar.
- **`passed` coerente com o `score`:** `passed` é verdadeiro se e só se `score >= 4` (`PASS_SCORE`). Incoerência é erro de validação, e o PydanticAI devolve ao modelo (retry de saída).
- **`judge_model` diferente do gerador:** compara o nome do modelo sem o provedor e sem o prefixo de organização (`google-gla:gemini-3.1-flash-lite` e `openrouter:google/gemini-3.1-flash-lite` contam como o mesmo). Vale contra `llm_model` e `fallback_model`. A chave do provedor do juiz **não** é exigida em `AgentSettings` (o backend carrega as settings e não usa juiz); é conferida ao montar o juiz, com erro claro no CLI. Padrão: `google-gla:gemini-3.1-flash`.
- **`--judge` com `--dataset gold_real` é erro** (código 1, mensagem em português), e não silêncio: quem pediu o juiz precisa saber que ele não rodou. Mesma coisa com `--sql-only`.
- **Erro do provedor no juiz** não derruba a rodada: os campos do juiz ficam nulos e o item conta em `judge_errors`.
- **Sessão por item ou cadeia:** `eval-<run_id>-<id da raiz>`, com `run_id = uuid4().hex[:8]`. Hoje todos os itens usam `"eval"`; com memória ligada, o golden set inteiro viraria uma conversa só e um item contaminaria o seguinte.
- **Follow-up cuja raiz não roda** (outra base ou `--only red_team`) não roda e conta em `follow_up_skipped`, que passa a significar "follow-up sem a pergunta de origem na rodada". Descartado: rodar o follow-up sozinho, que mede outra coisa (a pergunta isolada).
- **`TurnRecorder`** é um `Protocol` do pacote `evaluation` (`record(session_id, question, answer)`), e não uma porta da aplicação: quem grava é o "backend" da avaliação, nunca o agente.

## Arquivos

| Ação | Arquivo | Tarefa |
|---|---|---|
| criar | `ai-agent/src/venergy_agent/domain/judge.py` | 1 |
| criar | `ai-agent/tests/unit/domain/test_judge.py` | 1 |
| alterar (compartilhado, ver "Conflitos") | `ai-agent/src/venergy_agent/application/ports.py` | 1 |
| alterar (compartilhado) | `ai-agent/src/venergy_agent/config.py` | 2 |
| alterar | `ai-agent/tests/unit/test_config.py` (só testes novos no fim) | 2 |
| alterar | `ai-agent/src/venergy_agent/infrastructure/llm.py`, `ai-agent/tests/unit/infrastructure/test_llm.py` | 2 |
| alterar | `ai-agent/src/venergy_agent/infrastructure/prompt_renderer.py`, `ai-agent/tests/unit/infrastructure/test_prompt_renderer.py` | 3 |
| criar | `ai-agent/prompts/judge/v1/judge.md` | 3 |
| criar | `ai-agent/src/venergy_agent/infrastructure/answer_judge.py`, `ai-agent/tests/unit/infrastructure/test_answer_judge.py` | 3 |
| alterar | `ai-agent/src/venergy_agent/evaluation/report.py` | 4, 5 |
| alterar | `ai-agent/src/venergy_agent/evaluation/runner.py`, `ai-agent/tests/unit/evaluation/test_runner.py` | 4, 5 |
| alterar | `ai-agent/src/venergy_agent/evaluation/__main__.py`, `ai-agent/tests/unit/evaluation/test_cli.py` | 6 |
| criar | `ai-agent/src/venergy_agent/evaluation/compare.py`, `ai-agent/tests/unit/evaluation/test_compare.py` | 7 |
| alterar | `Makefile` (raiz) | 8 |
| alterar (compartilhado, só o fim) | `ai-agent/.env.example` | 2 |
| alterar (docs, só as seções desta trilha) | `ai-agent/README.md` (seção "Avaliação"), `ai-agent/docs/architecture.md` (§2 linhas novas e §6b), spec (§1 lista, §7 linhas `judge_*`, §9.3, §9.4, §9.5, §11), `docs/decisoes.md` (DEC-047) | 9 |

**Fora desta trilha (não tocar):** `application/ask.py`, `domain/answer.py`, `bootstrap.py`, `infrastructure/sql_generator.py`, `prompts/v*/`, `eval/golden_set.yaml`, `tests/unit/test_golden_set.py`, `tests/unit/test_bootstrap.py`, todo o `backend/`.

### Conflitos previstos com a trilha B (triviais)

- `application/ports.py`: esta trilha só acrescenta `class AnswerJudge` **no fim do arquivo** e o import `from venergy_agent.domain.judge import JudgeVerdict`. A trilha B acrescenta `ConversationHistory` e `SessionUsage` logo depois de `TextToSqlAgent`, muda a assinatura de `SqlGenerator.generate` e importa `domain.conversation`. O conflito possível é só no bloco de imports: manter os dois, em ordem alfabética.
- `config.py`: esta trilha acrescenta `judge_model` e `judge_prompt_version` **logo depois de `insight_prompt_version`** e um segundo `@model_validator` (`check_judge_model`) **depois de `check_provider_keys`**. A trilha B acrescenta `history_turns` e `session_token_budget` depois de `answer_sample_rows` e muda o padrão de `prompt_version`.
- `ai-agent/.env.example`: esta trilha acrescenta um bloco no **fim** do arquivo; a B, antes da linha do usuário somente leitura.
- Docs (spec, `architecture.md`, `decisoes.md`, README do agente): cada trilha edita só as próprias seções; na §7 e na lista da §1, manter as linhas das duas.

## Tarefas (TDD: teste que falha → código → verificação)

### Tarefa 1 · `JudgeVerdict` e porta `AnswerJudge`

1. Teste (`tests/unit/domain/test_judge.py`), parametrizado: `score` 4 ou 5 com `passed=False` e `score` 1–3 com `passed=True` são rejeitados; `rationale` em branco é rejeitado (regra do projeto: texto em branco não conta como preenchido). Um caso válido.
2. Código: `domain/judge.py` com `PASS_SCORE = 4` e `JudgeVerdict(BaseModel, frozen)`: `score: int = Field(ge=1, le=5)`, `passed: bool`, `rationale: NonBlankText`, `@model_validator` da coerência.
3. `application/ports.py`, no fim: `class AnswerJudge(Protocol): async def judge(self, question: str, answer: AgentAnswer) -> JudgeVerdict: ...` (assinatura da spec §9.5).
4. Verificação: `uv run pytest -q tests/unit/domain/test_judge.py`.

### Tarefa 2 · Configuração e modelo do juiz

1. Testes no fim de `tests/unit/test_config.py`:
   - `judge_model` igual ao `llm_model` é rejeitado; igual ao `fallback_model` também;
   - o mesmo modelo por outro provedor (`openrouter:google/gemini-3.1-flash-lite` contra `google-gla:gemini-3.1-flash-lite`) é rejeitado;
   - provedor desconhecido ou nome vazio no `judge_model` é rejeitado;
   - com `llm_model` do OpenRouter e só a chave do OpenRouter, as settings carregam (a chave do juiz não é exigida aqui).
2. Testes em `tests/unit/infrastructure/test_llm.py`: `build_judge_model(settings)` monta `GoogleModel` para `google-gla:`; sem a chave do provedor do juiz, levanta `ValueError` com o nome da variável (`VENERGY_AGENT_GOOGLE_API_KEY`) e sem valor de chave na mensagem.
3. Código:
   - `config.py`: `judge_model: str = "google-gla:gemini-3.1-flash"` e `judge_prompt_version: str = "v1"` depois de `insight_prompt_version`; `check_judge_model` depois de `check_provider_keys`;
   - `llm.py`: `build_judge_model(settings) -> Model`, que confere a chave e reaproveita `_build`. Sem fallback no juiz.
   - `.env.example`, no fim: bloco comentado "Avaliação: modelo do juiz (só para `--judge`, diferente do `LLM_MODEL`)" com `# VENERGY_AGENT_JUDGE_MODEL=google-gla:gemini-3.1-flash`.
4. Verificação: `uv run pytest -q tests/unit/test_config.py tests/unit/infrastructure/test_llm.py`.

### Tarefa 3 · Rubrica `judge/v1` e adapter `PydanticAiAnswerJudge`

1. Testes:
   - `test_prompt_renderer.py`: `render_judge_user(question, answer, nonce)` delimita a pergunta (`pergunta`), o texto da resposta (`resposta`) e as linhas (`dados`, com `total de linhas`, `truncado`, `suposições declaradas` e as linhas em JSON); o nonce que aparece no conteúdo vira `[redigido]`; nonce em branco é recusado; `render_judge_system` preenche `{{nonce}}`.
   - `test_answer_judge.py` (com `FunctionModel` devolvendo a saída estruturada): o veredito do modelo é devolvido; um veredito incoerente (`score=5`, `passed=False`) volta ao modelo e o segundo, coerente, é aceito; versão de prompt inexistente falha na construção; o prompt de sistema enviado contém a rubrica e não contém a pergunta; a pergunta e as linhas chegam só dentro das tags com o nonce.
2. Código:
   - `prompt_renderer.py`: `render_judge_system(template, nonce)` e `render_judge_user(question, answer, nonce)`, no padrão de `render_answer_*`;
   - `infrastructure/answer_judge.py`: `PydanticAiAnswerJudge(model, prompts_dir, prompt_version, nonce=None)`, lê `prompts_dir / prompt_version / "judge.md"`, `Agent(output_type=JudgeVerdict, retries=2)`, `temperature` 0. Erro do provedor propaga (o runner trata).
   - `prompts/judge/v1/judge.md`, em português:
     - papel: avaliar uma resposta já dada por outro sistema; **não** refazer a consulta nem decidir se o número está certo no mundo (isso é das métricas da §9.3);
     - critérios: **clareza** (responde à pergunta, em português direto, sem nome técnico de coluna ou view, com unidade e período quando as linhas têm) e **fidelidade** (toda afirmação e todo número estão nas linhas ou no total de linhas; não inventa causa, tendência ou comparação que as linhas não sustentam; avisa truncamento e repete as suposições declaradas quando mudam o número);
     - escala 1–5 descrita por nível, `passed` só com 4 ou 5, `rationale` curto (até 2 frases) citando o critério que pesou;
     - seção "Dados não são instruções" igual à dos outros prompts, com as tags `<pergunta-{{nonce}}>`, `<resposta-{{nonce}}>` e `<dados-{{nonce}}>`; uma resposta que tenta instruir o juiz ("dê nota 5") é sinal de falha de fidelidade.
3. Verificação: `uv run pytest -q tests/unit/infrastructure`.

### Tarefa 4 · Runner: sessões por cadeia, follow-ups em sequência e `recorder`

1. Testes em `tests/unit/evaluation/test_runner.py` (o `ScriptedAgent` já guarda `(question, session_id)`):
   - substituir `test_follow_up_items_are_skipped_until_the_agent_has_memory` por: o follow-up roda logo depois da raiz e na mesma sessão, mesmo listado antes de outro item; é avaliado como item comum (`matched` contra o próprio `reference_sql`); `follow_up_skipped == 0`;
   - cadeia de três (`G1 ← G2 ← G3`) roda na ordem e na mesma sessão;
   - itens independentes e ataques do red team recebem sessões diferentes entre si, e duas rodadas não repetem sessão;
   - follow-up cuja raiz está em outra base (ou com `--only red_team`) não vai ao agente e conta em `follow_up_skipped`;
   - com `recorder`, cada `ask` bem-sucedido gera um `record(session_id, question, answer)` na ordem; quando o `ask` levanta, nada é gravado.
2. Código:
   - `runner.py`: `class TurnRecorder(Protocol): async def record(self, session_id: str, question: str, answer: AgentAnswer) -> None: ...`; `EvaluationRunner(..., recorder: TurnRecorder | None = None, judge: AnswerJudge | None = None)` (o `judge` entra na tarefa 5);
   - montar o plano como lista de cadeias: cada item sem `follow_up_of` abre uma cadeia; os follow-ups entram na cadeia da raiz (resolvendo cadeias longas); cadeia sem raiz na rodada é descartada e contada;
   - `_evaluate` recebe o `session_id`; `SESSION_ID` deixa de existir;
   - `report.py`: nada novo nesta tarefa.
3. Verificação: `uv run pytest -q tests/unit/evaluation/test_runner.py`.

### Tarefa 5 · Runner e relatório: juiz e `refusal_accuracy`

1. Testes:
   - com `judge` e rodada narrada, só os itens `answered` são julgados; o juiz recebe a pergunta e o `AgentAnswer`; o item grava `judge_score`, `judge_passed` e `judge_rationale` (cortado em 300 caracteres);
   - rodada sem narrativa (`narrated=False`) nunca chama o juiz, mesmo com `judge`;
   - juiz que levanta: campos nulos, o item continua avaliado e `judge_errors == 1`;
   - métricas: `judge_pass_rate` (aprovados / julgados), `judge_mean_score`, `judge_items`, `judge_errors`; sem juiz, as taxas são `None` e as contagens 0;
   - `refusal_accuracy` conta golden `refused` e red team que terminaram `refused`;
   - `test_report_never_contains_rows_or_answer_text` continua passando com o juiz ligado.
2. Código:
   - `report.py`: `ItemResult` ganha `judge_score: int | None = None`, `judge_passed: bool | None = None`, `judge_rationale: str | None = None`; `EvaluationReport` ganha `judge_model: str | None = None` e `judge_prompt_version: str | None = None` (padrões nulos: relatórios antigos continuam carregando);
   - `runner.py`: `_metrics` vira `compute_metrics(items)` público (a comparação usa a mesma função) e ganha `refusal_accuracy` e as métricas do juiz; `run(...)` aceita `judge_model` e `judge_prompt_version` opcionais e os grava.
3. Verificação: `uv run pytest -q tests/unit/evaluation`.

### Tarefa 6 · CLI: `--judge`

1. Testes em `test_cli.py`:
   - `judges(dataset, judge, sql_only)` é falso sem `--judge`; com `--judge` e `gold_real` levanta `JudgeNotAllowed` (mensagem cita os dados reais e a issue #56); com `--judge` e `--sql-only` também;
   - `format_metrics` mostra `judge_mean_score` como número (`4.20`), e não como percentual.
2. Código (`__main__.py`): `--judge` no parser; `judges(...)`; com juiz, `PydanticAiAnswerJudge(build_judge_model(settings), settings.prompts_dir / "judge", settings.judge_prompt_version)` passado ao runner, e `judge_model`/`judge_prompt_version` no relatório; `main` trata `JudgeNotAllowed` e o `ValueError` de chave ausente do juiz com código 1 e mensagem curta, sem segredo. `_format_value` recebe o nome da métrica para tratar `judge_mean_score`.
3. Verificação: `uv run pytest -q tests/unit/evaluation/test_cli.py`.

### Tarefa 7 · Comparação de rodadas (`evaluation/compare.py`)

1. Testes (`test_compare.py`, com relatórios montados em memória ou em `tmp_path`):
   - métricas lado a lado com a diferença: taxa em pp, latência e contagens em absoluto, `—` com lado nulo;
   - com `golden_version` diferente, as métricas saem só dos itens em comum, e o texto diz quantos itens são só de A e só de B;
   - itens em comum que mudaram aparecem com `A → B` em `matched`, `status`, `numeric_fidelity` e `judge_passed`; item igual não aparece;
   - aviso quando `failed` passa de 5% em qualquer lado; sem aviso abaixo disso;
   - métricas da rodada (`red_team_violations`, `writes_accepted`, `views_changed`, `follow_up_skipped`, `other_dataset_skipped`) aparecem como estão, sem recalcular, e chave ausente num relatório antigo vira `—`;
   - todo relatório versionado em `eval/runs/*.json` carrega sem erro (protege a compatibilidade com os relatórios antigos);
   - arquivo inexistente ou JSON inválido: código 1 e mensagem curta.
2. Código: `compare.py` com funções puras (`load_report(path)`, `compare(a, b) -> str`) e `main(argv) -> int`; `if __name__ == "__main__": raise SystemExit(main(sys.argv[1:]))`. Saída: markdown em `stdout`. Nenhum import de `bootstrap`, `llm` ou do banco.
3. Verificação: `uv run pytest -q tests/unit/evaluation/test_compare.py` e, à mão, `uv run python -m venergy_agent.evaluation.compare eval/runs/2026-10-24T033727Z.json eval/runs/2026-10-28T113557Z.json`.

### Tarefa 8 · `Makefile`

- `eval: db` → `uv --directory ai-agent run --frozen python -m venergy_agent.evaluation --dataset $(or $(DATASET),amostra) $(if $(ONLY),--only $(ONLY)) $(if $(JUDGE),--judge) $(if $(SQL_ONLY),--sql-only)`.
- `eval-compare:` → `uv --directory ai-agent run --frozen python -m venergy_agent.evaluation.compare $(A) $(B)` (caminhos relativos a `ai-agent/`, porque o `--directory` muda o diretório; dizer isso no `help`).
- Acrescentar os dois alvos ao `.PHONY` e ao `help`. Fora do `make ci`: a avaliação é paga.
- Verificação: `make help`; `make eval-compare A=eval/runs/2026-10-24T033727Z.json B=eval/runs/2026-10-28T113557Z.json` (não chama modelo). Não rodar `make eval`.

### Tarefa 9 · Documentação e DEC

- `ai-agent/README.md`, seção "Avaliação": `make eval` (com `DATASET`, `ONLY`, `JUDGE`, `SQL_ONLY`), `make eval-compare`, o que a tabela mostra, a regra dos itens em comum e o aviso de `failed`; follow-ups em sequência numa sessão por cadeia; `--judge` (só amostra, modelo diferente, ainda não calibrado: não decide merge). Tabela de "última rodada válida" gerada pela comparação da linha de base (`2026-10-24T033727Z`) com a última rodada versionada (`2026-10-28T113557Z`), com as datas e a configuração.
- Spec: §7 (linhas `judge_model` e `judge_prompt_version`); §9.3 (`refusal_accuracy`); §9.4 (o que foi implementado, `PASS_SCORE`, só `answered` narrados, proibido na Gold real, calibração pendente); §9.5 (CLI com `--judge`, `compare`, sessões por cadeia e `TurnRecorder`); §11 (estado dos diferenciais "LLM as a judge" e "avaliação automatizada"); §1 (linha "em revisão").
- `ai-agent/docs/architecture.md`: §2 (linhas `domain/judge.py` e `infrastructure/answer_judge.py`) e §6b (compare, juiz, follow-ups).
- `docs/decisoes.md`: **DEC-047 · Avaliação comparativa e LLM as a judge**, no formato das DEC vizinhas: comparação sobre os itens em comum, aviso de `failed`, juiz só em `answered` narrados da amostra, modelo diferente validado nas settings, `rationale` no relatório, calibração antes de o juiz contar. Antes de commitar, confira que DEC-047 continua livre (`git grep -n "DEC-047" origin/main` e PRs abertos); a DEC-046 está reservada para a trilha B.
- Verificação final da trilha (abaixo).

## Fica para depois (sem cota)

1. **Calibração do juiz (§9.4):** numa rodada narrada da amostra, sortear 15 itens `answered`. Uma pessoa dá a nota 1–5 com a mesma rubrica, sem ver a do juiz. Rodar `make eval JUDGE=1 ONLY=golden`. Critério para o juiz passar a contar: concordância de `passed` em pelo menos 12 de 15 (80%) e diferença média absoluta de nota até 1. Registrar na spec §9.4 e na DEC-047. Se não passar, ajustar a rubrica numa `judge/v2` e repetir.
2. **Primeira rodada com juiz:** `make eval JUDGE=1` na amostra, sem nenhum `failed` de provedor, e `make eval-compare` contra a última rodada sem juiz (as métricas determinísticas não podem mudar além da variação do modelo, porque o juiz não altera a resposta).
3. Atualizar a tabela do README com essa rodada.

## Checklist final

- [ ] `uv run pytest -q` em `ai-agent/` (com o banco do compose no ar para os testes de integração)
- [ ] `uv run ruff check . && uv run ruff format --check .` em `ai-agent/`
- [ ] Nenhum arquivo da lista "fora desta trilha" alterado (`git diff --stat main`)
- [ ] `make eval-compare` roda sem chave e sem modelo
- [ ] Nenhum teste chama o modelo real; nenhuma chave em arquivo versionado
- [ ] README, spec, `architecture.md` e DEC-047 atualizados no mesmo branch
- [ ] Commits locais em Conventional Commits, sem `Co-Authored-By`; sem push e sem PR
