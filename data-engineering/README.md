# Engenharia de Dados

Pipeline em PySpark no Databricks seguindo a arquitetura Medalhão.

- `notebooks/` — notebooks `.ipynb` das camadas Bronze, Silver e Gold e da exportação para o banco local
- `workflow/` — arquivo `.yaml` do Databricks Workflow (Job)

> O dataset bruto é confidencial e **não** deve ser versionado (ver `.gitignore`).

## Testes de qualidade

### Travas dentro dos notebooks

Cada notebook confere a camada antes de gravar. Uma trava que falha levanta erro, o Resumo do notebook fica vermelho e o Job
para ali: nenhuma camada seguinte é gravada e os CSVs da Gold não são exportados.

| Trava | O que exige |
|---|---|
| `exigir_sem_perda` | nenhum valor preenchido vira nulo na conversão de tipo |
| `exigir_chave_unica` | a chave da tabela não se repete |
| `exigir_sem_orfaos` | toda linha aponta para uma UC do cadastro |
| `exigir_mesma_contagem` | a mesma cardinalidade entre etapas |
| `exigir_zero` | nenhuma linha viola a regra (uma ou várias condições nomeadas) |
| `aplicar_contrato` | nomes, ordem e tipos de `contracts/gold_schema.yaml`, com nulidade, domínio, formato e perda na conversão |

Exemplos por camada:

- **Bronze** (`Landing_to_Bronze`, com as travas próprias `exigir_arquivo` e `exigir_sem_erros`): arquivo da landing presente e não
  vazio; cabeçalho sem BOM, sem coluna duplicada ou sem nome; leitura do Spark igual à planilha de origem; `source_file` apontando
  para o arquivo lido.
- **Silver** (`Bronze_to_Silver`): `exigir_sem_perda` nas datas e em `data_ligacao`, `latitude` e `longitude`;
  `exigir_chave_unica` em `id_fatura`, `id_leitura` e `protocolo`; `exigir_sem_orfaos` em leituras, medidores e atendimentos;
  `exigir_zero` no encoding da UC-13 em todas as colunas de texto e na UF fora de PE.
- **Gold** (`Silver_to_Gold`): `aplicar_contrato` em cada tabela, como `gold_kpis_mensais` e `gold_receita_decomposicao`;
  `exigir_mesma_contagem` entre faturas, leituras e linhas do fato; `exigir_sem_orfaos` contra `gold_dim_uc` nas tabelas por UC;
  `exigir_zero` em mais de um medidor vigente por UC e em fatura sem bandeira.

### Notebook `Testes_Qualidade_Gold`

Quarta task do Workflow, depois do export (DEC-074). É somente leitura: lê `v_energy.gold` e os CSVs de `/Volumes/v_energy/gold/csv`
e grava só em `v_energy.qualidade`. O que confere:

| Seção | Teste | Tipo |
|---|---|---|
| 1 | CSV × Gold, para cada uma das 12 tabelas: contagem de linhas, colunas e ordem, soma das colunas numéricas (`money`, `energy_kwh` e `integer` do contrato) e encoding da UC-13 nas colunas de texto | crítico |
| 2 | Variação de linhas de cada tabela contra a execução anterior, com limite de 5% | alerta |
| 3 | Reconciliações entre tabelas: `gold_kpis_mensais` = soma de `gold_kpis_segmento_mensal`; receita total = cadastro + órfãs; preço + volume + mix = variação da receita | crítico |
| 4 | Premissa da DEC-067: nenhuma linha de UC de teste nas tabelas por UC | crítico |

- **Crítico × alerta:** um teste crítico com `FALHA` derruba o notebook e o Job fica vermelho. Um alerta só fica registrado.
- **Linha de base:** na primeira execução não há contagem anterior, e a variação de linhas sai como `LINHA_DE_BASE`; a contagem
  atual vira a base da execução seguinte.
- **Histórico:** cada execução grava uma linha por teste em `v_energy.qualidade.resultados_testes` (append, com `execucao_id`).
  Os números medidos ficam na coluna `valor`, só no Databricks; o print do notebook mostra só teste, tabela, tipo e status.
- **Limitação:** os testes rodam depois do export, então um CSV ruim já foi gravado no Volume quando o teste falha. Regra: com o
  Job vermelho, ninguém baixa os CSVs.
