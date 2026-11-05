# Robustez do agente, validada no portal e por usuário: plano

**Objetivo:** toda pergunta feita no portal recebe uma resposta boa:
- status certo;
- números do banco;
- texto claro do modelo;
- tabela formatada pela unidade;
- poucos segundos de espera.

E isso vale para os 5 usuários de demonstração. **Só conta como validado o que estiver certo na tela do portal.** Um JSON certo da API não basta.

**Base:** a `main` com a [DEC-080](../../../docs/decisoes.md#dec-080--agente-confiável-no-portal-depois-da-apresentação), branch `feat/ai-agent-ajustes-pos-apresentacao` ([plano](2026-11-04-ajustes-pos-apresentacao.md)). Cada tarefa abaixo tem a sua branch, a partir da `main`, e o PR é revisado pelo outro integrante do GenAI (Luis Felipe e Lucas).

**Spec e regras:**
- [spec](../specs/2026-10-19-architecture-design.md) §4 (`AgentAnswer`), §5 e §9;
- `ai-agent/CLAUDE.md`;
- DEC-016 (nenhuma mudança de prompt, few-shot, glossário ou camada entra se o golden regredir);
- DEC-019, DEC-070, DEC-079 e DEC-080 (checagem da narrativa);
- DEC-024 (nenhum número da Gold real vai para o Git).

## Como trabalhar neste plano (passo a passo)

### 1. Preparar a máquina (uma vez)

1. **Clonar e instalar.** Na raiz do repositório:
   ```bash
   make setup
   ```
   Isso instala o workspace do uv, o frontend e os hooks de pre-commit.
2. **`.env` da raiz:** `cp .env.example .env` e preencher:
   - `POSTGRES_PASSWORD`, `AGENT_DB_PASSWORD`, `JWT_SECRET` e `SENHA_DEMO` (a senha dos 5 logins de demonstração);
   - `GOOGLE_API_KEY`: a sua chave do Gemini (aistudio.google.com);
   - `LLM_MODEL=openrouter:google/gemini-3.1-flash-lite`, `GEMINI_FALLBACK_MODEL=google-gla:gemini-3.1-flash-lite,openrouter:anthropic/claude-haiku-5.5` e `OPENROUTER_API_KEY`, a chave paga do grupo. O Luis Felipe passa a chave por mensagem, nunca pelo Git;
   - `AGENT_SESSION_TOKEN_BUDGET=0`, para o orçamento de tokens não travar a validação.
3. **`ai-agent/.env`:** `cp ai-agent/.env.example ai-agent/.env`, com as mesmas chaves e os mesmos modelos (`VENERGY_AGENT_LLM_MODEL`, `VENERGY_AGENT_FALLBACK_MODEL`, `VENERGY_AGENT_OPENROUTER_API_KEY`). É o arquivo que a avaliação usa.
4. **Gold real.** Copiar os CSVs para `data/gold/`. Eles ficam fora do Git (DEC-024) e o Luis Felipe passa por fora. Depois:
   ```bash
   make up
   ```
   ```bash
   make load
   ```
   ```bash
   make users
   ```
   A carga recria as views do agente; `make users` cria os 5 logins.
5. **Conferir.**
   - Em `http://localhost:3000`, entrar com `henrique` e a `SENHA_DEMO`.
   - Na página Agente, "Quantas UCs existem?" responde algo da ordem de 45 mil. Na amostra sintética o número é bem menor, e isso indica que a Gold real não foi carregada.

### 2. Começar uma tarefa

1. Branch nova a partir da `main` atualizada, com um nome por tarefa, por exemplo `feat/ai-agent-e2e-portal` para a T3:
   ```bash
   git switch main && git pull && git switch -c feat/ai-agent-e2e-portal
   ```
2. Ler, nesta página, a tarefa e a "Definição de validado". Se a tarefa mexer no agente, ler também `ai-agent/CLAUDE.md`.
3. Escrever o teste antes do código, nas regras do projeto. Os testes nunca chamam o modelo.

### 3. Rodar os testes de cada parte

| Parte | Comando | Observação |
|---|---|---|
| Agente | `cd ai-agent && uv run pytest -q tests/unit && uv run ruff check . && uv run ruff format --check .` | os testes de integração rodam no CI |
| Backend | `cd backend && uv run pytest -q && uv run ruff check` | exporte `VENERGY_API_TEST_DATABASE_URL` e `VENERGY_API_TEST_AGENT_DATABASE_URL` apontando para o banco **`venergy_test`**, nunca o `venergy` |
| Frontend | `cd frontend && npm test && npx tsc -p . --noEmit && npx biome check src` | — |
| Contrato | `make openapi` | sempre que um schema do backend mudar; regera `contracts/openapi.json` e os tipos do portal |

### 4. Subir o portal com o código da branch

Escolha uma das duas formas:

- **Docker (mais simples):** `docker compose up -d --build`. O `--build` é obrigatório, porque sem ele a API continua com o código antigo da imagem.
- **Local (recarrega mais rápido):**
  - API:
    ```bash
    set -a; . ./.env; set +a; VENERGY_API_DATABASE_URL=postgresql+psycopg://venergy:$POSTGRES_PASSWORD@localhost:5433/venergy VENERGY_AGENT_DATABASE_URL=postgresql://venergy_agent:$AGENT_DB_PASSWORD@localhost:5433/venergy VENERGY_API_JWT_SECRET=$JWT_SECRET VENERGY_API_SENHA_DEMO=$SENHA_DEMO VENERGY_AGENT_GOOGLE_API_KEY=$GOOGLE_API_KEY VENERGY_AGENT_OPENROUTER_API_KEY=$OPENROUTER_API_KEY VENERGY_AGENT_LLM_MODEL=$LLM_MODEL VENERGY_AGENT_FALLBACK_MODEL=$GEMINI_FALLBACK_MODEL VENERGY_AGENT_SESSION_TOKEN_BUDGET=0 VENERGY_API_AI_LIMITE_PERGUNTAS=0 uv --directory backend run uvicorn venergy_api.main:create_app --factory --port 8001
    ```
  - Portal: `cd frontend && API_PROXY_TARGET=http://localhost:8001 npm run dev`.

O limite de 20 perguntas a cada 10 min ainda não passa pelo compose. A T3 acrescenta `AI_LIMITE_PERGUNTAS` ao `docker-compose.yml`, como já foi feito com o orçamento. Até lá, use a forma local para validar muitas perguntas seguidas.

### 5. Validar no portal (obrigatório em toda tarefa)

1. Para cada um dos 5 logins (henrique, camila, rafael, beatriz, patricia):
   - abrir a página Agente e o widget numa tela comum do perfil;
   - fazer as perguntas da tarefa e as do conjunto de fumaça (seção 6).
2. Para cada resposta, conferir os 8 itens da "Definição de validado".
3. Recarregar a página e conferir que a próxima pergunta entra numa conversa nova.
4. Registrar no PR uma tabela "pergunta × usuário × ok", com o que falhou. Depois da T3, o `make e2e-agente` faz isso sozinho e grava o relatório em `ai-agent/eval/runs_gold/`.
5. Se algo sair diferente entre usuários, é defeito: anotar e corrigir antes do merge.

### 6. Rodar a avaliação no nível certo

| Quando | Comando | Tempo e custo |
|---|---|---|
| Durante a tarefa | `make eval DATASET=gold_real IDS=G106,G107,... JUDGE=1`, com os itens novos ou afetados mais o conjunto de fumaça | 2 a 4 min, centavos |
| Mudança que só mexe no SQL | `make eval DATASET=gold_real SQL_ONLY=1` | cerca de 10 min |
| Antes do merge de mudança de prompt, few-shot, glossário ou camada (DEC-016) | `make eval DATASET=gold_real JUDGE=1` (completo) | 25 a 30 min, cerca de US$ 0,40 |
| Comparar com a rodada anterior | `make eval-compare A=ai-agent/eval/runs_gold/<anterior>.json B=ai-agent/eval/runs_gold/<nova>.json` | sem modelo |

- **Conjunto de fumaça** (até a T11 marcar no golden): G001, G005, G099, G015, G036, G033, G047, G056, G063, G065, G071, G104, G105, G106, G107, G108, G109.
- **Critério para o PR:** nenhum item piora em `matched` ou `status` no `eval-compare`, e o `fallback_rate` não sobe.
- **Relatórios:** ficam em `eval/runs_gold/`, fora do Git. No PR vão só as métricas.

### 7. Mudar prompt, glossário ou camada

- **Prompt:** nunca editar uma versão que já existe. Criar `prompts/vN+1/` (SQL) ou `prompts/answer/vN+1/` (narração) e trocar o padrão em `ai-agent/src/venergy_agent/config.py`.
- **Camada:** subir a `version` de `semantic/semantic_layer.yaml`; se as views mudarem, rodar `uv run python -m venergy_agent.infrastructure.views_sql`.
- **Golden:** item novo ou gabarito mudado entra com `revisado_por: null` e a versão do golden sobe.
- **Regra de entrada:** rodada completa antes do merge (DEC-016).

### 8. Entregar

- **Antes do commit:**
  - todos os testes da seção 3 passando;
  - a validação da seção 5 registrada;
  - a avaliação da seção 6 no nível da mudança;
  - a DEC nova ou atualizada em `docs/decisoes.md`, quando houver decisão;
  - este plano atualizado: marcar a tarefa como feita e o que ficou de fora.
- **Commit:** Conventional Commits.
- **PR:** com o resultado do `eval-compare` e a tabela da validação no portal, revisado pelo Luis Felipe.

## Por que este plano

Na apresentação de 04/11/2026, o agente acertou o SQL e mesmo assim falhou para quem usava o portal:
- a memória se perdeu, porque o chat abria numa conversa antiga;
- a pergunta da diretora saiu no texto de reserva cru;
- "208 kWh" apareceu para 208 UCs;
- um percentual apareceu como R$;
- as respostas levaram de 20 a 29 s.

A DEC-080 corrigiu esses casos, mas só os que vimos falhar. A avaliação de hoje chama o agente direto, sem backend, sem login e sem a tela. Por isso nada garante que outros tipos de pergunta, ou o mesmo tipo escrito de outro jeito, saiam bem no portal.

## Achados do João Euclides no portal (04/11/2026, 21h)

1. **Termo fora do vocabulário:**
   - "percentil" não foi entendido como percentual. O agente não tem como interpretar um termo que não está no glossário nem nos nomes das colunas, e ou pede esclarecimento, ou erra.
   - Um sinônimo no glossário resolve esse caso, mas não o próximo termo inesperado.
2. **Memória depois de um esclarecimento:**
   - o agente pediu esclarecimento, o João respondeu, e o agente esqueceu a pergunta original;
   - o turno de esclarecimento entra no histórico com a pergunta e o pedido (`history_renderer.py`), mas a resposta curta ("percentual", "em 2025") chega ao gerador como uma pergunta nova;
   - juntar as duas fica a critério do modelo, e a regra de follow-up (`domain/followup.py`) só reconhece frases que começam com "e" ou dizem "o mesmo";
   - a pergunta original se perde quando o modelo trata a resposta como uma pergunta solta.

As duas frentes viram as tarefas T9 e T10.

## O que muda por usuário (levantamento de 04/11/2026)

O agente não recebe perfil nem contexto da tela: o portal manda só `{question, session_id}` (`frontend/src/features/agente/consulta.ts`). **O conteúdo da resposta é o mesmo para todos.** O que muda por usuário, e por isso precisa de teste em cada um:

| O que | Onde | Efeito na tela |
|---|---|---|
| Limite de perguntas (20 a cada 10 min, por login) | `backend/src/venergy_api/routers/ai.py` (`_verificar_pedido`), `config.py` (`ai_limite_perguntas`) | 429 com `Retry-After` |
| Orçamento de tokens por login (200 mil em 24 h) | `historico_ia.py` (`_tokens_used`), `ai-agent` (`session_token_budget`) | resposta `refused` "limite de uso" |
| Posse da conversa | `routers/ai.py` (`sessao_de_outro_usuario`, `_exigir_sessao`) | 403 para a conversa de outro login |
| Uma pergunta por vez por login | `routers/ai.py` (`ai_travas`) | segunda aba espera |
| Histórico de conversas por login | `AgenteProvider` com chave pelo login (`frontend/src/routes/__root.tsx`), `GET /ai/sessions` | lista da página Agente |
| Auditoria só para TI | `GET /ai/audit/{id}` com `exigir_perfil(Perfil.TI)` | não há tela; `buscarAuditoriaIa` (`features/agente/api.ts`) não é usada |
| Página inicial e ordem do menu | `features/auth/profiles.ts`, `__root.tsx` | o agente e o widget aparecem para todos |
| Insights | rotas abertas a todos; cache por tela e métricas (`backend/src/venergy_api/insights.py`) | o mesmo texto para todos |
| Ações da fila | `perdas-page.tsx`, `fila-suspeitas.tsx`, `ordens-table.tsx` (`perfil === "perdas"`) | botões só para Perdas |

O seletor "Todos os dados" do agente só filtra os exemplos sugeridos (`filtrarExemplosPorEscopo`). Ele não muda a pergunta enviada.

## Definição de "validado"

Uma pergunta está validada quando, no portal, logado, pela página Agente **e** pelo widget, tudo isto vale:

1. **Status certo:** resposta, esclarecimento, "não sei" ou recusa.
2. **Números:** os do texto batem com o gabarito do golden set, em formato pt-BR.
3. **Texto do modelo:** "A consulta devolveu…" só aparece quando o modelo falhou, e a falha fica registrada no log.
4. **Sem nome técnico** (`receita_faturada`, `sem_*`, `cod_uc`) no texto, nas suposições e no cabeçalho da tabela.
5. **Tabela:** formatada pela unidade (R$, kWh, %, h, contagem) e com rótulo em português.
6. **Período citado.**
7. **Tempo:** menos de 10 s.
8. **Follow-up:** mantém o contexto do turno anterior.

E vale para henrique (Diretoria), camila (Atendimento), rafael (Perdas), beatriz (Operação) e patricia (TI).

## Mapa de tipos de pergunta

Cada tipo precisa de pelo menos 3 formas de escrever no golden set:
- formal;
- coloquial;
- com erro de digitação ou termo trocado, como "percentil" por percentual.

A coluna "já coberto" lista itens do golden 0.19.0.

| Tipo | Exemplo | Esperado | Já coberto |
|---|---|---|---|
| Valor simples | quantas UCs, receita de um mês | resposta | G001, G005, G006, G106 |
| Recorte | município, bairro, classe, GD, alimentador, UC | resposta | G002, G013, G014, G023, G088 |
| Mês, intervalo, ano | junho de 2025; de janeiro a março | resposta | G017, G018, G083 |
| Relativo à base | primeiro ano, últimos 12 meses | resposta | G041 a G043, G104 |
| Sem período quando importa | queda de consumo acima de 30% | esclarecimento | G056, G058, G060 |
| Relativo ao calendário | mês passado, último ano, último trimestre | esclarecimento | G039, G044 |
| Comparação de períodos | quanto cresceu entre 2024 e 2025 | resposta | G015, G016, G059, G076 a G082 |
| Ranking e top N | 3 alimentadores com maior DEC | resposta | G007, G063 |
| Agrupamento | por classe, por canal | tabela | G003, G068 |
| Percentuais e razões | tributos, não pagas, leituras estimadas, tarifa média | resposta | G071, G096, G097, G108, G110 |
| "Por que" | decomposição, com premissas na pergunta | resposta | G104, G109 |
| Continuidade | DEC/FEC da empresa, município, bairro, alimentador, período acumulado | resposta | G010, G065, G083, G089, G091 |
| Atendimento | canal, satisfação, chamados | resposta | G026, G027, G068 |
| Medidor e GD | eletromecânicos, painel solar | resposta | G004, G069, G094 |
| Por UC | interrupções, faturas de uma UC | resposta | só na amostra |
| Follow-up | troca de período, recorte ou métrica; três turnos | resposta com contexto | G046, G099, G102, G107, G108 |
| Resultado vazio | período fora da base | resposta sem dados | G029, G030 |
| Resultado grande | lista truncada | resposta com aviso | falta |
| Fora do escopo | cancelamentos, CEP | "não sei" | G033, G035 |
| Dado proibido | fila de suspeitas, titular | "não sei" | G028, G031, G064 |
| Manipulação | injeção, escrita, segredo | recusa | G047 a G055, red team |

Lacunas principais:
- formas coloquiais e com erro de digitação de quase todos os tipos;
- resultado grande;
- follow-up de troca de métrica ("e o percentual?");
- por UC na Gold real, com código fictício que exista só no `esperado.json` local;
- percentuais por recorte;
- perguntas longas com premissas fora do tema de receita.

## Tarefas

### T1. Fechar a DEC-080 (Luis Felipe)

- Rodada completa do golden na Gold real, narrada, com juiz e com o modelo pago como principal; `make eval-compare` contra a rodada de 04/11/2026.
- Preencher a "Evidência" da DEC-080; PR e merge.

**Aceite:** nenhum item piora no SQL ou no status.

### T2. Golden 0.20.0 e valores esperados (Luis Felipe; Dados revisa)

- Cerca de 60 itens novos (G111 em diante), cobrindo as lacunas do mapa.
  - Variações de escrita da mesma intenção apontam para o mesmo `reference_sql`.
  - Cadeias de follow-up de 3 turnos usam `follow_up_of`.
  - Todo item novo entra com `revisado_por: null`.
- `ai-agent/src/venergy_agent/evaluation/expected_values.py`:
  - executa as referências na Gold real, reaproveitando o caminho do `--only references` de `evaluation/__main__.py`;
  - grava `ai-agent/eval/runs_gold/esperado.json` (pergunta, status esperado, números esperados em pt-BR, unidade de cada coluna);
  - **o arquivo fica fora do Git.**
- **Testes:**
  - estrutura do golden (`tests/unit/test_golden_set.py`);
  - o script grava só em `eval/runs_gold/`.

### T3. Teste de ponta a ponta no portal (Lucas)

- **Ferramenta:** Playwright no frontend (`npm i -D @playwright/test`).
  - Arquivos: `frontend/playwright.config.ts`, `frontend/e2e/agente.spec.ts` e o script `npm run e2e`.
  - Alvo: o frontend em `localhost:3000` e a API com a Gold real.
- **Fluxo para cada usuário** (`test.describe.each` com os 5 logins; senha de `VENERGY_API_SENHA_DEMO`):
  1. Login e `/agente`: a conversa abre vazia, o que é regressão da DEC-080.
  2. Perguntas do `esperado.json` pela página. Um subconjunto (5 perguntas e 1 cadeia de follow-up) vai também pelo widget, numa tela comum do perfil.
  3. Para cada resposta, confere os 8 itens da definição de "validado":
     - lê o texto, o status, as suposições e a tabela (cabeçalho e células) pelo DOM;
     - os nomes técnicos são procurados com a mesma expressão de `TECHNICAL_NAME` (`ai-agent/src/venergy_agent/domain/wording.py`).
  4. Recarrega a página: a próxima pergunta entra numa conversa nova, e o histórico mostra a anterior.
- **Testes por usuário:**
  - a conversa de um login não abre para outro (403, com mensagem na tela);
  - o limite de 20 perguntas gera 429 com mensagem clara (rodada com o limite baixo);
  - com o orçamento esgotado, aparece a mensagem de limite de uso;
  - duas abas do mesmo login: a segunda pergunta espera a primeira;
  - patricia abre a auditoria (depois da T6), e os outros 4 não veem o link.
- **Insights:** em cada perfil, "Gerar insight" na página inicial dele. Confere o rótulo ("IA" ou "Leitura automática") e se os números do texto estão na tela. Confere também que o texto é o mesmo entre perfis para o mesmo recorte, por causa do cache por métricas.
- **Execução:**
  - fora do CI, porque chama o modelo de verdade: `make e2e-agente`;
  - a API sobe com `AGENT_SESSION_TOKEN_BUDGET=0` e `VENERGY_API_AI_LIMITE_PERGUNTAS=0`, exceto nos testes de limite;
  - o relatório (por usuário e por pergunta, com o tempo) vai para `ai-agent/eval/runs_gold/e2e-<data>.json`, fora do Git;
  - capturas de tela das falhas ficam em `frontend/test-results/`, que vai para o `.gitignore`.

### T4. Casas decimais e mensagens de erro (Lucas no frontend, Luis Felipe no agente)

- **Política por unidade:**
  - DEC e FEC com 2 casas;
  - R$ com 2;
  - % com até 2;
  - kWh inteiro;
  - contagem inteira.
- **Onde vale:**
  - no texto: `rounded_for_display` em `domain/numbers.py`, que passa a receber a unidade;
  - no texto de reserva: `_pt_br` em `application/ask.py`;
  - na tabela: `formatarCelulaResultado` em `frontend/src/features/agente/conversions.ts`.
- Hoje a tabela mostra 0,02 e o texto mostra 0,024: os dois passam a sair iguais.
- **Mensagens na tela:** 429, 403, 409, 503 e prazo estourado, em português, iguais para todos os perfis e cobertas pela T3.

### T5. Vazio, grande, glossário e esclarecimento (Luis Felipe; Lucas no frontend)

- **Resultado vazio:** a narrativa diz que não há registros no período e recorte pedidos, sem concluir nada. Hoje o texto é só determinístico.
- **Resultado truncado:** a narrativa cita o total (`row_count`) e avisa que a tabela é uma amostra. No portal, a tabela ganha paginação e o aviso.
- **Glossário (camada 0.4.3):**
  - sinônimos e erros comuns: "percentil", "faturamento", "consumo", "luz", "conta", "imposto", "inadimplência", "DEC do bairro";
  - cada sinônimo novo ganha um item no golden;
  - a mudança passa pela regra da DEC-016.
- **Esclarecimento com sugestões:**
  - o pedido de período traz até 3 opções (por exemplo, "últimos 12 meses", "em 2025", "em junho de 2026");
  - no portal, as opções viram botões que completam a pergunta.
  - **Como implementar:** as opções vêm de um campo novo e opcional do `AgentAnswer` (`clarification_options`). Isso é mudança de contrato e precisa de DEC.

### T6. Auditoria para a TI (Lucas)

- Link "ver auditoria" em cada resposta, só para o perfil TI. Ele abre um painel com `GET /ai/audit/{id}` (`buscarAuditoriaIa`): pergunta, SQL, linhas, modelo, versão do prompt, tempo e tokens.
- Os outros perfis não veem o link. Se chamarem a rota, recebem 403.

### T7. Filtro no texto, motivos de recusa e tempo limite (Luis Felipe)

- **Filtro no texto:**
  - a narrativa diz o filtro da pergunta ("queda acima de 30%");
  - hoje o 30 é recusado porque o SQL usa `0.7`;
  - a saída proposta é um campo `filters` no rascunho do SQL (`SqlDraft`), com os limites ditos pela pergunta e conferidos contra os literais do SQL validado.
- **Motivos de recusa:**
  - o script `ai-agent/src/venergy_agent/evaluation/log_summary.py` lê o log da API e resume os motivos (`verificacao_numerica_falhou`, `unidade_errada_na_resposta`, `periodo_ausente_na_resposta`, `sem_tempo_para_narrar`, `periodo_nao_informado`);
  - o resumo entra no relatório da T3.
- **Tempo limite:** medir com o modelo pago e ajustar `llm_request_timeout_seconds` (`config.py`, hoje 15 s) e `narration_min_seconds` (hoje 4 s).

### T8. Rodada final (os dois)

- Golden completo, com juiz, mais a T3 nos 5 usuários, 3 vezes seguidas no conjunto da apresentação.
- DEC nova com as medições.
- Atualizar `ai-agent/docs/architecture.md`, o README do agente e `docs/agente-ia.md`.

### T9. Resposta a um esclarecimento continua a pergunta original (Luis Felipe)

- **Regra no código, não no prompt:**
  - quando o turno mais recente do histórico tem status `clarify`, a pergunta atual é tratada como a resposta a ele;
  - o agente monta a pergunta efetiva = pergunta original + "Esclarecimento: " + resposta, e é ela que vai para o gerador de SQL, para a checagem de ano (`_invented_years`) e para o redator;
  - a auditoria guarda a pergunta como o usuário escreveu, e o log registra `pergunta_completada`.
- **Exceção:** se a resposta for uma pergunta completa e nova (tem verbo interrogativo e métrica própria), segue como pergunta nova.
- **Onde:** `ai-agent/src/venergy_agent/application/ask.py` (antes da geração) e `domain/followup.py` (a regra de "resposta a esclarecimento").
- **Testes:**
  - "queda acima de 30%?" → esclarecimento → "entre 2024 e 2025" responde a pergunta original;
  - "percentil de tributos" → esclarecimento → "percentual" responde com o percentual de tributos;
  - pergunta nova depois de um esclarecimento não herda nada.
- **Golden:** cadeias G-esclarecimento → resposta, com `follow_up_of`.
- **Portal (T3):** as mesmas cadeias pela tela, nos 5 usuários.

### T10. Termos que não estão no vocabulário (Luis Felipe; Lucas no frontend)

Quatro camadas, da mais barata para a mais cara:

1. **Correspondência aproximada, determinística:**
   - antes de gerar o SQL, cada palavra da pergunta é comparada, por distância de edição e por radical, com os termos do glossário, os sinônimos e os rótulos das colunas (`domain/wording.py`, `semantic_layer.yaml`);
   - os candidatos próximos ("percentil → percentual", "inadiplencia → inadimplência", "fatura → receita faturada") entram no prompt como dica delimitada, "termos parecidos com o vocabulário", e nunca como instrução;
   - **onde:** `domain/vocabulary.py`, novo, usado pelo `SqlGenerator`;
   - **testes:** os pares acima e palavras comuns que não podem casar ("para", "mês").
2. **Regra no prompt de SQL** (versão nova):
   - se um termo da pergunta não está no vocabulário e a dica traz um candidato claro, use o candidato e declare como suposição ("entendi 'percentil' como percentual");
   - sem candidato claro, peça esclarecimento citando as opções mais próximas, em vez de chutar;
   - a suposição aparece na tela, e o usuário vê como o termo foi lido.
3. **Opções no esclarecimento** (usa o `clarification_options` da T5): "Você quis dizer: percentual de tributos, valor dos tributos?" vira botões no portal.
4. **Ciclo de aprendizado:**
   - o script `evaluation/unmapped_terms.py` lê a auditoria (`app.ai_auditoria`, pela conexão do backend, nunca pelo usuário do agente) e lista as perguntas com `clarify` ou `unknown` e as suposições "entendi X como Y";
   - uma pessoa decide quais viram sinônimo no glossário e item no golden;
   - nada entra no glossário sozinho.

**Golden:** um item por termo trocado ou com erro de digitação, incluindo um termo sem candidato, que precisa virar esclarecimento.

**Fora:** dicionário externo ou embeddings. O vocabulário do domínio é pequeno (glossário mais cerca de 90 colunas), e a correspondência aproximada sobre ele resolve sem dependência nova.

### T11. Avaliação mais rápida (Lucas)

- **Conjunto de fumaça no golden:**
  - campo `smoke: true` nos itens da seção 6;
  - opção `--smoke` no `evaluation/__main__.py` (e `SMOKE=1` no `make eval`), que roda só eles e os turnos de que dependem.
- **Itens em paralelo:**
  - o runner (`evaluation/runner.py`) roda até `--concurrency N` cadeias ao mesmo tempo, mantendo a ordem dentro de cada cadeia de follow-up;
  - a pausa entre chamadas, por limite do provedor, continua valendo por modelo.
  - **Meta:** a rodada completa em cerca de 8 minutos.
- **Testes:**
  - a ordem dos turnos de uma cadeia se mantém com concorrência;
  - o `--smoke` inclui os turnos anteriores.

## Critério de aceite

| Métrica | Meta |
|---|---|
| execution accuracy (golden completo, Gold real) | ≥ 98%, nenhum item piora |
| status certo | 100% |
| `fallback_rate` | ≤ 2% |
| juiz | ≥ 95% |
| latência p95 | ≤ 10 s |
| red team | 0 violações |
| T3 nos 5 usuários | 100% das perguntas validadas pela tela |
| conjunto da apresentação | 3 execuções seguidas sem falha |
| cadeias esclarecimento → resposta (T9) | 100% respondem a pergunta original, pela tela |
| termos trocados ou com erro (T10) | 100% entendidos ou com esclarecimento que cita o candidato |

## Ordem

| Ordem | Tarefa | Quem | Depende de |
|---|---|---|---|
| 1 | T1 | Luis Felipe | — |
| 2 | T2 | Luis Felipe | T1 |
| 3 | T3 | Lucas | T2 (`esperado.json`) |
| 4 | T4 | Lucas e Luis Felipe | T3 para validar |
| 5 | T5 | Luis Felipe e Lucas | T2 |
| 6 | T6 | Lucas | — |
| 7 | T7 | Luis Felipe | T3 para o resumo |
| 6b | T9 (resposta a esclarecimento) | Luis Felipe | — |
| 6c | T10 (termos fora do vocabulário) | Luis Felipe e Lucas | T5 para as opções |
| 2b | T11 (avaliação mais rápida) | Lucas | — |
| 8 | T8 | os dois | todas |

## Regras para quem implementar

- **Código do agente:** em inglês, sem comentários, com testes só para regras do projeto. **Documentação:** em português.
- **Testes:** nunca chamam o modelo real. A avaliação e a T3 chamam, fora do CI.
- **Integração:** os testes de integração usam o banco `venergy_test`, nunca o `venergy`.
- **Contrato:** mudança no `AgentAnswer` (T5) é combinada com o backend e o portal e registrada em DEC.
- **Commits:** Conventional Commits. Commit, push e PR só com pedido explícito.
