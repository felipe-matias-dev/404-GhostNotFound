# Calibração do juiz (rubrica prompts/judge/v1)

Este arquivo registra a calibração do juiz de respostas (DEC-047) com a amostra sintética de 20 itens. Não contém dados da Gold real.

## Resumo

- Itens: 20
- Acordo de aprovação (nota 4 ou 5 contra nota 4 ou 5): 18/20 (90%)
- Nota exata: 3/20 (15%)
- Diferença de até 1 ponto: 18/20 (90%)

Com 20 itens, o intervalo de confiança do acordo é largo. Isso não fecha a calibração, só mostra o ponto de partida.

## Histórico das rodadas de notas humanas

| Rodada | Itens | Acordo de aprovação |
|---|---|---|
| 1 (notas iniciais) | 20 | 75% (15/20) |
| 2 (após reavaliação às cegas) | 20 | 85% (17/20) |
| 3 (após revisão de três notas) | 20 | 90% (18/20) |

A rodada 3 é a que está registrada abaixo.

## Notas por item

| Item | Nota humana | Nota do juiz | Humana passa | Juiz passa | Divergência de aprovação |
|---|---|---|---|---|---|
| G004 | 5 | 5 | sim | sim | não |
| G005 | 3 | 3 | não | não | não |
| G010 | 3 | 2 | não | não | não |
| G011 | 3 | 2 | não | não | não |
| G012 | 3 | 2 | não | não | não |
| G013 | 4 | 5 | sim | sim | não |
| G019 | 2 | 3 | não | não | não |
| G022 | 4 | 5 | sim | sim | não |
| G024 | 5 | 5 | sim | sim | não |
| G025 | 4 | 5 | sim | sim | não |
| G027 | 4 | 5 | sim | sim | não |
| G030 | 4 | 5 | sim | sim | não |
| G041 | 3 | 2 | não | não | não |
| G042 | 3 | 2 | não | não | não |
| G043 | 3 | 2 | não | não | não |
| G062 | 3 | 2 | não | não | não |
| G066 | 3 | 5 | não | sim | sim |
| G070 | 3 | 2 | não | não | não |
| G073 | 4 | 2 | sim | não | sim |
| G074 | 4 | 5 | sim | sim | não |

## Divergências de aprovação

- **G066:** humana 3, juiz 5. A justificativa da nota humana ainda não foi registrada; o item está em análise.
- **G073:** humana 4, juiz 2. A resposta cita o nome técnico de uma view ("sem faturamento mensal") e uma suposição que não existe nos dados. O juiz identificou o defeito de fidelidade; a nota humana ainda aceita a resposta.

## Pergunta para o grupo

O texto de reserva determinístico do agente (`_deterministic_text`, em `ask.py`) escreve "A consulta devolveu N linha(s)" e "Resultado: coluna = valor", com nomes técnicos de colunas. Nos itens em que isso aparece, o juiz penaliza a clareza e a avaliação humana oscila. Decisão pendente: trocar o texto de reserva por uma frase em português natural?

Se a resposta for sim, a mudança altera o comportamento do agente e precisa passar pelo golden set sem regressão (DEC-016) antes de ser aceita. Este draft não altera código do agente.

## Limitações

- 20 itens, de uma amostra sintética.
- Uma avaliação humana. Não há dupla avaliação para medir concordância entre avaliadores.
- O juiz tende a dar notas extremas (5 ou 2), e a nota exata coincide em {exato}/{n}.
- Qualquer mudança de rubrica, modelo do juiz ou texto avaliado exige recalibração.
