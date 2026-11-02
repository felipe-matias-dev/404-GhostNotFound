# Calibração do juiz (rubrica prompts/judge/v1)

Este arquivo registra a calibração oficial do juiz (DEC-047, issue #116) e a análise diagnóstica de 20 itens que veio antes dela.

## Calibração oficial (01/11/2026)

O critério da DEC-047 e da spec §9.4 vale para 15 itens `answered`: `passed` igual em pelo menos 12 e diferença média absoluta de nota de até 1 ponto, com as notas humanas dadas sem ver as do juiz.

- **Itens:** 15 novos, sem repetir os 20 da análise diagnóstica. As respostas foram geradas de novo na amostra sintética, com as suposições declaradas separadas do texto.
- **Avaliação humana:** Lucas Mendes, às cegas, na rubrica `prompts/judge/v1`.

| Medida | Resultado | Critério |
|---|---|---|
| `passed` igual | 14 de 15 (93%) | pelo menos 12 de 15 |
| Diferença média absoluta | 0,33 | até 1 |
| Diferença média com sinal (juiz menos humano) | −0,20 | |
| Itens a até 1 ponto | 15 de 15 | |
| Nota exata | 10 de 15 | |

A diferença média absoluta sai das outras linhas. As notas são inteiras, os 15 itens ficaram a até 1 ponto e 10 tiveram nota igual, então 5 itens diferem em exatamente 1 ponto: 5 ÷ 15 = 0,33.

**Resultado:** critério atingido. A rubrica continua na v1, sem `judge/v2`.

**Divergência de aprovação:**

- **G014:** humana 4, juiz 3. A resposta começa com "A consulta devolveu 1 linha(s)" e omite a unidade da energia. É o texto de reserva determinístico do agente (ver "Pergunta para o grupo").

**Ressalvas:**

- Com 15 itens, o intervalo de confiança do acordo continua largo.
- Uma pessoa avaliou. A issue #116 pede, de preferência, uma segunda pessoa; o critério da DEC-047 não exige.
- Amostra sintética, sem dados da Gold real.
- As respostas completas e as linhas ficam fora do repositório, na pasta local de calibração.

## Análise diagnóstica (20 itens, antes da calibração oficial)

Feita na mesma amostra sintética, para entender as divergências antes da calibração. Não conta para o critério.

### Como os 20 itens foram usados

| Rodada | Notas cegas? | Acordo de aprovação |
|---|---|---|
| 1 (notas iniciais, antes da execução do juiz) | sim | 75% (15/20) |
| 2 (reavaliação, sem ver as notas do juiz) | sim | 85% (17/20) |
| 3 (revisão de notas, depois de ver as notas do juiz) | não | 90% (18/20) |

A rodada 3 não conta como calibração cega, porque algumas notas foram revistas depois de ver as do juiz. Ela é apresentada só como registro do que mudou.

Estado da amostra: 18 de 20 de acordo na aprovação, nota exata em 3 de 20, diferença de até 1 ponto em 18 de 20. Com 20 itens, o intervalo de confiança é largo, então isso não fechava a calibração.

### Notas por item

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

### Divergências de aprovação

As duas ficam como registro do diagnóstico e não entram no resultado oficial.

- **G066:** humana 3, juiz 5. A justificativa da nota humana ainda não foi registrada; o item está em análise.
- **G073:** humana 4, juiz 2. A resposta cita o nome técnico de uma view ("sem faturamento mensal") e uma suposição que não existe nos dados. O juiz identificou o defeito de fidelidade; a nota humana ainda aceita a resposta.

## Pergunta para o grupo

O texto de reserva determinístico do agente (`_deterministic_text`, em `ask.py`) escreve "A consulta devolveu N linha(s)" e "Resultado: coluna = valor", com nomes técnicos de colunas. Nos itens em que isso aparece, o juiz penaliza a clareza e a avaliação humana oscila. Decisão pendente: trocar o texto de reserva por uma frase em português natural?

Se a resposta for sim, a mudança altera o comportamento do agente e precisa passar pelo golden set sem regressão (DEC-016) antes de ser aceita. Este draft não altera código do agente.

## Limitações

- Amostra sintética nas duas etapas.
- Uma avaliação humana. Não há dupla avaliação para medir concordância entre avaliadores.
- Na análise diagnóstica, o juiz tendeu a notas extremas (5 ou 2), com nota exata em 3 de 20; na calibração oficial, a nota exata coincidiu em 10 de 15.
- Qualquer mudança de rubrica, modelo do juiz ou texto avaliado exige recalibração.
