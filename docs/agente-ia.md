# Agente de IA

O agente Text-to-SQL responde em português perguntas sobre consumo, faturamento,
interrupções e atendimento, consultando a Gold no PostgreSQL local. Também redige os
insights da Visão geral, da Receita, da Rede, de Perdas e da UC, escolhendo entre as leituras
que o backend calcula ([DEC-077](decisoes.md#dec-077--insights-de-ia-nas-telas-do-dia-a-dia-com-a-ia-escolhendo-a-leitura)).
É chamado pelo backend em `POST /ai/ask`; para ligá-lo, basta a `GOOGLE_API_KEY` no `.env`
([instalação](instalacao.md#agente-de-ia)).

O passo a passo da pergunta e do insight, com os diagramas, os motivos de cada escolha e as
alternativas descartadas, está no [README do agente](../ai-agent/README.md#como-o-agente-responde-uma-pergunta).

Documentação técnica do módulo: [`ai-agent/README.md`](../ai-agent/README.md),
[mapa do estado atual](../ai-agent/docs/architecture.md) e a
[spec](../ai-agent/docs/specs/2026-10-19-architecture-design.md), que é a fonte da verdade.

## O agente que diz "não sei"

Resposta inventada é pior do que nenhuma resposta. O agente gera um único `SELECT` sobre as views da camada semântica, executa e narra o resultado. Toda resposta volta com um status:

| Status | Quando |
|---|---|
| `answered` | Respondeu com dados, e todo número do texto saiu das linhas retornadas |
| `unknown` | Os dados não respondem à pergunta |
| `clarify` | A pergunta é ambígua (período, recorte); o agente pergunta de volta |
| `refused` | Pedido fora do escopo ou tentativa de manipulação |
| `failed` | Erro do banco ou do provedor; nunca vira exceção para o backend |

A segurança mora no banco e no validador, nunca no prompt:

1. **A pergunta tem no máximo 500 caracteres.** O conteúdo do usuário e do banco entra no prompt entre delimitadores com um rótulo aleatório a cada chamada: é dado, não instrução.
2. **O modelo só enxerga 9 views `sem_*`.** Nenhuma coluna sensível entra (titular e documento ficam fora), e a fila de suspeitas também fica fora, por decisão de produto ([DEC-022](decisoes.md#dec-022--regras-do-agente-sobre-a-gold-e-decisões-da-daily-de-2110)).
3. **Todo SQL passa pelo `SqlglotValidator`.** Ele aceita um único `SELECT`, só views da allowlist e só funções que o parser conhece, e impõe um `LIMIT` de até 200 linhas.
4. **O banco executa em transação somente leitura.** A consulta tem `statement_timeout` de 10 s e roda com o usuário `venergy_agent`, que não tem acesso ao schema `app`.
5. **Os números do texto são conferidos com as linhas.** Se a narrativa citar um número que não está no resultado, a resposta volta a um texto determinístico com os valores ([spec §5.1](../ai-agent/docs/specs/2026-10-19-architecture-design.md)).
6. **Toda resposta é auditada.** Fica gravada em `app.ai_auditoria` (pergunta, SQL, linhas, modelo, versão do prompt, latência) e pode ser lida em `GET /ai/audit/{id}` ([DEC-034](decisoes.md#dec-034--auditoria-do-agente-de-ia-gravação-leitura-e-subida-sem-a-chave)).

**Avaliação.** Usamos um golden set de 105 perguntas (versão 0.18.0, todas revisadas por Dados na issue #90; 95 valem na Gold real e 10 só na amostra) e 17 ataques de red team. Toda mudança de prompt, modelo ou camada semântica só entra se o golden set não regredir ([DEC-016](decisoes.md#dec-016--exceção-de-versionamento-do-prompt-v1-proposta)). Rodada final, na Gold real, narrada e com o juiz (04/11/2026, camada 0.4.1, prompt de SQL `v3`, prompt da narração `v4` da [DEC-079](decisoes.md#dec-079--narrativa-recusada-tem-uma-segunda-chance-e-chega-arredondada), `gemini-3.1-flash-lite` com a cadeia de reserva), comparada com a de 03/11 nos mesmos 95 itens:

| Métrica | 03/11 | 04/11 |
|---|---|---|
| SQL com o resultado certo (execution accuracy) | 94,1% | 98,5% |
| Status certo (respondeu, não sei, esclarecer, recusar) | 95,8% | 100% |
| Recusa certa | 100% | 100% |
| Fidelidade numérica do texto | 86,2% | 88,2% |
| Juiz: respostas `answered` aprovadas, inclusive o texto de reserva | 64,6% de 65, nota média 4,11 | 89,7% de 68, nota média 4,74 |
| Vazamentos de prompt | 0 | 0 |
| `failed` (a rodada vale abaixo de 5%) | 3,2% | 0% |
| Latência p50 / p95 | 2,8 s / 16,6 s | 3,3 s / 27,4 s |

Nenhum item piorou no SQL ou no status. A latência p95 subiu por dois motivos: a segunda narração quando a primeira é recusada e, nessa rodada, a cota esgotada do primeiro modelo de reserva, que levou parte das perguntas para o modelo pago do OpenRouter.

O red team, com os 17 ataques, terminou com 0 escritas aceitas, 0 views alteradas e 0 vazamentos de prompt (rodadas de 28/10 e 04/11). A meta do case para o agente sobre os dados reais (G1-05, pelo menos 80%) está cumprida. O juiz é outro modelo (`gemini-3.5-flash-lite`), calibrado contra notas humanas em 14 de 15 itens ([DEC-047](decisoes.md#dec-047--avaliação-comparativa-e-llm-as-a-judge)). Os relatórios da Gold real ficam fora do Git ([DEC-024](decisoes.md#dec-024--o-que-pode-subir-ao-repositório-público)). Detalhes e rodadas anteriores: [spec §9.6](../ai-agent/docs/specs/2026-10-19-architecture-design.md) e [DEC-047](decisoes.md#dec-047--avaliação-comparativa-e-llm-as-a-judge).

**Limitações conhecidas:**
- **Texto de reserva.** Quando a narrativa cita um número que não está nas linhas ou omite o período, ela é escrita de novo uma vez, com o motivo da recusa ([DEC-079](decisoes.md#dec-079--narrativa-recusada-tem-uma-segunda-chance-e-chega-arredondada)). Se for recusada outra vez, a resposta sai no texto determinístico, correto mas menos claro. Na rodada de 04/11, 11 narrativas foram recusadas na primeira tentativa (7 por número, 4 por período), 9 passaram na segunda e 1 saiu no texto determinístico.
- **Comparação do prompt `v2` com o `v3` (resolvida).** O `v3`, com a memória de conversa, é o padrão desde a [DEC-046](decisoes.md#dec-046--memória-de-conversa-orçamento-de-tokens-e-limite-de-perguntas-por-usuário); a rodada que compara os dois nos itens em comum ([DEC-016](decisoes.md#dec-016--exceção-de-versionamento-do-prompt-v1-proposta)) foi feita em 04/11/2026 e confirma a troca: v2 acertou 91 de 95 e v3 acertou 95 de 95 (execução 100%, status 100%, 0 falhas); nenhum item piorou; follow-ups 6 de 6 na v3 (inclusive o G046) contra 3 de 6 na v2, que pedia esclarecimento em G046, G099 e G102 por não ter o histórico.
