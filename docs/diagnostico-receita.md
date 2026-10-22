# Diagnóstico: receita x volume faturado

## Pergunta

A tarifa residencial subiu 10,5% desde meados de 2022 e a base de clientes cresceu.
Mesmo assim, nos últimos 12 meses, comparados ao primeiro ano, a energia faturada
caiu cerca de 4% e a receita subiu só cerca de 8%. Por quê?

## Resposta

1. **Os números da pergunta se confirmam na camada Silver**, depois do tratamento das
   leituras com erro (item 4).
2. **A energia caiu por causa da geração distribuída (GD).** Quase toda a queda de
   volume vem das unidades consumidoras que conectaram GD depois de jul/2022: a energia
   que elas injetam é abatida do consumo faturado. As UCs sem GD ficaram praticamente
   estáveis.
3. **A receita subiu menos que a tarifa porque o volume caiu.** O aumento de preço,
   descontada a queda de volume, explica o crescimento da receita.
4. **Os erros de leitura exageravam a queda.** Entre set/2025 e mar/2026, uma parte das
   leituras veio com consumo negativo impossível. Sem tratamento, a queda parece maior
   do que é; com essas leituras corrigidas, ela volta ao valor citado na pergunta.

## Hipóteses avaliadas

| Hipótese | Resultado |
|---|---|
| H1 Geração distribuída | Confirmada: principal causa da queda de volume |
| H5 Erros de leitura | Confirmada: exagerava a queda de volume |
| H3 Mix de clientes | Descartada: a base cresceu de forma parecida em todos os subgrupos |

H2, H4, H6 e H7 não se aplicam a esta pergunta e ficam para as próximas análises.
Os números e as evidências estão no relatório privado do time.

## Recomendações

- Levar à V-Energy o problema das leituras negativas de set/2025 a mar/2026
  (falha de processamento: atinge UCs diferentes a cada mês, sem relação com GD
  ou subgrupo tarifário).
- Acompanhar o crescimento da GD como principal fator de queda do volume faturado.

## Método

- **Períodos comparados:** jul/2022 a jun/2023 (base) e jul/2025 a jun/2026 (atual).
- **Fonte:** tabelas da camada Silver (`faturas`, `leituras`, `unidades_consumidoras`
  e `geracao_distribuida`).
- **Leituras com consumo negativo:** excluídas e substituídas pela média das leituras
  válidas do mesmo período.
- **Quebras da queda de volume:** por subgrupo tarifário e por UC com ou sem GD.
