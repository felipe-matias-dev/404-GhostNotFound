# Log de problemas de qualidade

Problemas encontrados no profiling dos arquivos da landing, com a decisão de tratamento proposta para a Silver. Alimenta o dicionário de dados.

- **Método:** leitura direta dos arquivos de `v_energy.default.landing`, todas as colunas como texto; perfil por coluna (nulos, nulos disfarçados, espaços sobrando, valores distintos), distribuição das colunas categóricas e checagem da chave.
- **Decisões:** `tratar` (corrigir/padronizar), `descartar` (remover o registro) ou `flag` (manter e sinalizar).
- **Atenção:** este arquivo é público. Nunca colar CPF, nome ou linhas reais do dataset.

## unidades_consumidoras

**Resumo:** 46.461 linhas no arquivo → **45.200 UCs únicas** após o tratamento.

| Etapa | Linhas |
|---|---|
| Arquivo original | 46.461 |
| (−) cabeçalho repetido | 1 |
| (−) cópias exatas e cópias com formatação diferente | 1.260 |
| **= UCs na Silver** | **45.200** |

| ID | Coluna | Problema | Evidência | Decisão |
|---|---|---|---|---|
| UC-01 | (linha) | Linha de cabeçalho repetida no meio do arquivo | 1 linha | Descartar |
| UC-02 | (linha) | Cópias exatas do mesmo registro | 900 linhas | Descartar, manter 1 |
| UC-03 | `id_uc` | Mesma UC repetida com formatação diferente em `nome_titular` (maiúsculas/minúsculas) e `cpf_cnpj` (com/sem pontuação); demais campos iguais | 360 linhas | Tratar: padronizar e depois remover as cópias. Regra validada: resta 1 linha por UC, sem conflito real de dados |
| UC-04 | `nome_titular` | Maiúsculas e minúsculas misturadas | ver UC-03 | Tratar: padronizar a caixa |
| UC-05 | `cpf_cnpj` | Com e sem pontuação (`000.000.000-00` × `00000000000`) | ver UC-03 | Tratar: manter só os dígitos, como texto (preserva zero à esquerda) |
| UC-06 | `uf` | 5 grafias para Pernambuco (`PE`, `pe`, `pernambuco`, `Pernambuco`, `P.E.`) | 6.990 linhas fora de `PE` | Tratar: padronizar para `PE` |
| UC-07 | `classe` | Variações de maiúscula e acento | 16 grafias para 5 classes | Tratar: padronizar (Residencial, Comercial, Industrial, Rural, Poder Público) |
| UC-08 | `cep` | Ausente ou inválido | 1.030 UCs sem CEP + 159 com CEP de 1 dígito (após deduplicação) | Flag: CEP inválido vira nulo e a UC é mantida com `flag_cep_ausente = true` (descartar removeria as faturas dela da receita) |
| UC-09 | `cep`, `logradouro` | Espaços sobrando no início/fim | 174 e 2.797 | Tratar: remover espaços |
| UC-10 | `status` | Coluna com valor único (`ATIVA`) | 100% das linhas | Documentar; não serve como filtro |
| UC-11 | `latitude`, `longitude` | Precisão de 2 casas decimais | — | Documentar; limita uso em mapa |

**Sem problemas:** `municipio` (14 municípios da RMR), `subgrupo_tarifario` (B1, B2, B3, A4) e a coerência classe × subgrupo (Residencial = B1, Rural = B2, Comercial e Poder Público = B3, Industrial = A4).

**Pontos para o time:**
- `cpf_cnpj` e `nome_titular` são dados pessoais. Decidir se a Gold mascara esses campos antes do portal e do agente de IA.
- Teste de qualidade sugerido para a Silver: `COUNT(*) = COUNT(DISTINCT id_uc) = 45.200`.


## inspecoes (3 abas)

**Resumo:** 1.389 inspeções nas tabelas `inspecoes_ago_set` (511), `inspecoes_out_nov` (495) e `inspecoes_dez` (383). Sem duplicatas de `id_inspecao`, sem órfãos (todo `id_uc` existe no cadastro) e cada UC aparece em uma só inspeção.

| ID | Coluna | Problema | Evidência | Decisão |
|---|---|---|---|---|
| INSP-01 | `resultado` | 8 grafias para 3 valores (variações de caixa; `CONFIRMADA` sozinho) | 168 linhas fora do padrão | Tratar: padronizar para `IRREGULARIDADE CONFIRMADA` / `SEM IRREGULARIDADE` |
| INSP-02 | `resultado` | Valor `NADA CONSTA`, fora do padrão | 22 linhas; todas sem tipo e com kWh zero, igual a `SEM IRREGULARIDADE` | Tratar como `SEM IRREGULARIDADE` + flag de origem |
| INSP-03 | `tipo_irregularidade` | Ausência escrita de várias formas (vazio, `-`, `N/A`, `NULL`) | 518 linhas, exatamente as sem irregularidade | Tratar: converter para nulo |
| INSP-04 | `data` | 4 formatos: `AAAA-MM-DD`, `DD.MM.AAAA`, `DD/MM/AAAA` e `MM-DD-AAAA` (padrão americano) | 133 linhas fora de `AAAA-MM-DD` | Tratar: converter conforme o formato de cada linha. Formatos confirmados pelos valores acima de 12 |
| INSP-05 | `data` × aba | Inspeções de agosto a novembro lançadas na aba `dez` | 107 linhas | Flag: vale a `data`; a aba fica só como origem |
| INSP-06 | `inspetor` | Espaços sobrando no início/fim | 83 linhas | Tratar: remover espaços |
| INSP-07 | `kwh_recuperado` | Vírgula como separador decimal | 125 linhas | Tratar: trocar vírgula por ponto e converter para número |

**Coerência validada:** toda irregularidade confirmada tem tipo e kWh maior que zero; todo caso sem irregularidade não tem tipo e tem kWh zero.

**Ponto para o time:** as inspeções são o gabarito do score de suspeita (ADR-05). Na base, 871 de 1.389 inspeções confirmaram irregularidade.


## medidores

**Resumo:** 51.812 linhas no arquivo → **51.299 medidores únicos** após o tratamento. Sem órfãos de `id_uc`: cobre 45.000 das 45.200 UCs do cadastro (todas com exatamente 1 medidor `ATIVO`; 200 UCs do cadastro não possuem medidor).

| Etapa | Linhas |
|---|---|
| Arquivo original | 51.812 |
| (−) cópias exatas | 513 |
| **= Medidores na Silver** | **51.299** |

| ID | Coluna | Problema | Evidência | Decisão |
|---|---|---|---|---|
| MED-01 | (linha) | Cópias exatas do mesmo registro | 513 linhas | Descartar, manter 1 (`id_medidor` passa a ser único) |
| MED-02 | `modelo` | Espaços sobrando no início/fim | 3.109 linhas no bruto (3.078 nas únicas); 81 variações para 9 modelos | Tratar: remover espaços |
| MED-03 | `tipo` | 10 grafias para 3 categorias (variações de caixa, acento, hífen e `smart meter`) | 5.354 linhas no bruto (5.297 nas únicas) fora do padrão | Tratar: padronizar para `ELETRONICO`, `ELETROMECANICO` e `SMART` |
| MED-04 | `data_instalacao` | 4 formatos: `AAAA-MM-DD`, `DD/MM/AAAA`, `DD.MM.AAAA` e `MM-DD-AAAA` (padrão americano) | 3.728 linhas no bruto (3.694 nas únicas) fora de `AAAA-MM-DD` | Tratar: converter conforme o formato de cada linha. Formatos confirmados pelos valores acima de 12 |
| MED-05 | `data_retirada` | Data sentinela `9999-12-31` usada como nulo disfarçado em medidores ativos | 13.649 linhas no bruto (13.500 nas únicas), todas com `status = ATIVO` | Tratar: converter `9999-12-31` para nulo |
| MED-06 | `data_ultima_manutencao` | Coluna 100% vazia | 100% das linhas | Documentar; manter como `date` nula na Silver |

**Coerência validada:** após `MED-05`, 100% dos medidores `ATIVO` (45.000) têm `data_retirada` nula e 100% dos `RETIRADO` (6.299) têm `data_retirada` válida (`>= data_instalacao`), sem sobreposição de datas entre medidores da mesma UC. A relação `modelo` × `tipo` é 100% determinística (`CG-500`, `EM-1200`, `EM-1400` = `ELETROMECANICO`; `EL-2200`, `EL-3000`, `NX-700` = `ELETRONICO`; `IQ-900`, `SM-4100`, `SM-4500` = `SMART`).


## geracao_distribuida

**Resumo:** 3.510 linhas no arquivo → **3.510 registros** na Silver. Sem duplicatas (`1 linha por id_uc`) e sem órfãos no cadastro.

| ID | Coluna | Problema | Evidência | Decisão |
|---|---|---|---|---|
| GD-01 | `potencia_kwp` | Vírgula como separador decimal | 316 linhas | Tratar: trocar vírgula por ponto e converter para `decimal` |
| GD-02 | `potencia_kwp` | Potência ~1.000× acima da faixa normal (`3.049,99` a `8.994,91`, compatíveis com registro em `Wp` em vez de `kWp`), gerando razão `energia_injetada / potencia < 0,35` em UCs residenciais (33) e comerciais (2) | 35 linhas (`potencia_kwp > 500`, contra `1,5` a `75,0` kWp nas demais 3.475 UCs) | Flag: manter o registro e sinalizar com `flag_potencia_anomala` |

**Sem problemas:** `data_conexao` (100% em `AAAA-MM-DD`), `modalidade` (3 categorias padronizadas: `GERACAO NA PROPRIA UC`, `AUTOCONSUMO REMOTO`, `GERACAO COMPARTILHADA`) e `energia_injetada_kwh_media_mensal` (100% numérica positiva com ponto decimal).


## ocorrencias_rede

**Resumo:** 180.000 ocorrências únicas (`id_ocorrencia` único), sem duplicatas e sem órfãos de `id_uc` (41.512 UCs atingidas em 122 alimentadores).

| ID | Coluna | Problema | Evidência | Decisão |
|---|---|---|---|---|
| OCO-01 | `causa` | Ausência escrita de várias formas (vazio: 1.356, `-`: 1.363, `N/A`: 1.341, `NULL`: 1.340), além da categoria `NAO IDENTIFICADA` (26.328) | 5.400 linhas (3,0%) sem causa informada | Tratar + Flag: converter vazio/`-`/`N/A`/`NULL` para nulo e sinalizar com `flag_causa_ausente` |
| OCO-02 | `duracao_min` | Sufixo textual `" min"` concatenado ao valor (ex.: `"23 min"`) | 16.200 linhas (9,0%) | Tratar: remover `" min"` e converter para `decimal` |
| OCO-03 | `data_abertura`, `data_encerramento` | Registradas com data e hora (`AAAA-MM-DD HH:MM:SS`) | 180.000 linhas | Documentar; converter para `timestamp` para preservar o cálculo de duração |

**Coerência validada:** após `OCO-02`, 100% das 180.000 linhas têm `data_encerramento > data_abertura` e `duracao_min` exatamente igual à diferença em minutos entre encerramento e abertura (de 5 a 2.880 min). `tipo` possui 5 categorias padronizadas (`FALTA DE ENERGIA`, `DANO EM EQUIPAMENTO`, `OSCILACAO`, `SOBRECARGA`, `FIO PARTIDO`).


## atendimentos

**Resumo:** 318.871 atendimentos únicos (`protocolo` único), sem duplicatas e sem órfãos de `id_uc` (44.940 UCs).

| ID | Coluna | Problema | Evidência | Decisão |
|---|---|---|---|---|
| ATD-01 | `nota_satisfacao` | Avaliação de satisfação ausente (`null` na origem) | 9.566 linhas (3,0%) | Flag: manter nulo e sinalizar com `flag_sem_nota_satisfacao` |
| ATD-02 | `historico` | Array aninhado de 1 a 3 structs (`sequencia`, `data` em `AAAA-MM-DDTHH:MM:SS`, `acao`, `canal`) em que o rótulo de `acao` não segue ordem cronológica fixa (ex.: `ENCERRAMENTO` na sequência 1) | 318.871 linhas (636.857 eventos) | Documentar; tipar campos da struct (`sequencia` inteiro, `data` timestamp) mantendo a estrutura |
| ATD-03 | `data_abertura`, `data_fechamento` | Registradas com data e hora (`AAAA-MM-DD HH:MM:SS`) | 318.871 linhas | Documentar; converter para `timestamp` |

**Coerência validada:** `canal` (5 categorias), `assunto` (6 categorias) e `subassunto` (15 categorias, 100% coerentes com `assunto`) sem nulos nem espaços sobrando. Em 100% dos registros `data_fechamento > data_abertura`, o primeiro item de `historico` tem o mesmo `canal` do atendimento e o último item coincide com `data_fechamento`. Quando preenchida (309.305 linhas), `nota_satisfacao` varia de `1,3` a `5,0` (1 casa decimal).


## faturas

**Resumo:** 2.184.623 linhas no arquivo → **2.184.621 faturas** (sem duplicatas de `id_fatura`). Período de 2022-07 a 2026-06 (48 competências).

| ID | Coluna | Problema | Evidência | Decisão |
|---|---|---|---|---|
| FAT-01 | (linha) | Linha de cabeçalho repetida no meio do arquivo | 2 linhas | Descartar |
| FAT-02 | `data_emissao` | 4 formatos: `AAAA-MM-DD`, `DD/MM/AAAA`, `DD.MM.AAAA` e `MM-DD-AAAA` (padrão americano) | 183.361 linhas fora de `AAAA-MM-DD` | Tratar: converter conforme o formato de cada linha. Ordem confirmada pelos valores acima de 12 |
| FAT-03 | `valor_total` | Texto em formato de moeda (`R$ 1.234,56`) | 196.622 linhas | Tratar: remover `R$` e ponto de milhar, vírgula vira ponto, `decimal(12,2)` |
| FAT-04 | `data_pagamento` | Ano `9999` usado como "não pago" em faturas `EM ABERTO` | 61.333 linhas | Tratar: converter para nulo. Depois disso, `status` e `data_pagamento` ficam 100% coerentes |
| FAT-05 | `id_uc` | Faturas de UCs que não existem no cadastro (`id_uc` com 7 dígitos, `id_fatura` com prefixo próprio), distribuídas por todas as competências | 32.285 faturas de 31.706 UCs | Flag `flag_uc_orfa`, sem apagar. Destino final (quarentena) definido na integridade referencial |

**Coluna derivada:** `status_pagamento` (`PAGA`, `PAGA COM ATRASO`, `EM ABERTO`), comparando `data_pagamento` com `data_vencimento`. O `status` original é mantido.

**Sem problemas:** `mes_referencia` (formato único `AAAA-MM`), `data_vencimento` (sempre 12 dias após a emissão), `valor_energia` e `tributos` (sem negativos nem zeros), `valor_total` igual a `valor_energia + tributos` em todas as faturas, `bandeira_tarifaria` (Verde, Amarela, Vermelha P1, Vermelha P2), nenhum pagamento anterior à emissão.

**Pontos para o time:**
- Faturas não têm kWh: a energia faturada vem das leituras.
- Faturas de UCs fora do cadastro aparecem em todas as competências (hipótese H6 do diagnóstico).
- A maior parte das faturas pagas foi paga depois do vencimento (ponto para o diagnóstico de arrecadação).


## leituras

**Resumo:** 2.182.468 linhas nos 5 arquivos anuais → **2.152.336 leituras**, 1 por UC × competência (mesmo total das faturas de UCs válidas). Período de 2022-07 a 2026-06.

| Etapa | Linhas |
|---|---|
| Arquivos originais | 2.182.468 |
| (−) cópias exatas | 21.523 |
| (−) mesma leitura registrada com 2 medidores | 8.609 |
| **= leituras na Silver** | **2.152.336** |

| ID | Coluna | Problema | Evidência | Decisão |
|---|---|---|---|---|
| LEI-01 | (linha) | Cópias exatas do mesmo registro | 21.523 linhas | Descartar, manter 1 |
| LEI-02 | `data_leitura` | 4 formatos: `AAAA-MM-DD`, `DD/MM/AAAA`, `DD.MM.AAAA` e `MM-DD-AAAA` (padrão americano) | 259.332 linhas fora de `AAAA-MM-DD` | Tratar: converter conforme o formato de cada linha. Ordem confirmada pelos valores acima de 12 |
| LEI-03 | `leitura_anterior` | Ausente, escrita como nulo, `N/A`, `NULL` ou `-1` | 32.285 leituras | Tratar: converter para nulo. Flag `flag_sem_leitura_anterior` |
| LEI-04 | `id_uc` × `mes_referencia` | Mesma leitura registrada duas vezes, mudando só `id_leitura` e `id_medidor` | 8.609 pares | Tratar: manter a de menor `id_leitura`. Flag `flag_leitura_duplicada`. Revisar o desempate com a tabela de medidores |
| LEI-05 | `consumo_kwh` | Consumo negativo (casas decimais aparecem só nos negativos) | 8.016 leituras | Flag `flag_consumo_negativo`, sem apagar |
| LEI-06 | `leitura_atual` | Leitura atual menor que a anterior | 6.215 leituras | Flag `flag_leitura_regressiva`, sem apagar |
| LEI-07 | `consumo_kwh` | Consumo diferente de `leitura_atual − leitura_anterior` em mais de 5% | 1.687 leituras | Flag `flag_consumo_divergente`. Diferenças de até 5% são aceitas como arredondamento |

**Sem problemas:** `mes_referencia` (formato único `AAAA-MM`), `tipo_leitura` (REAL e ESTIMADA), nenhuma leitura de UC fora do cadastro.

**Pontos para o time:**
- `consumo_kwh` é o valor oficial de energia; as flags indicam onde ele é suspeito. A Gold decide se exclui os casos sinalizados.
- 200 UCs do cadastro (ligadas entre 1997 e 2024) não têm nenhuma leitura nem fatura (hipótese H6 do diagnóstico).
- Leituras estimadas são parte relevante da base (hipótese H5 do diagnóstico).


## Validação cruzada (UCs × faturas × leituras)

Conferências entre as tabelas Silver, depois do tratamento. Todas passaram.

| Conferência | Regra | Resultado |
|---|---|---|
| Pareamento fatura × leitura | Cada fatura de UC válida tem exatamente uma leitura na mesma UC e competência, e vice-versa | 0 faturas sem leitura, 0 leituras sem fatura |
| Tarifa implícita | `valor_energia ÷ consumo_kwh` em faixa estreita por subgrupo e ano | Faixas estreitas; B1 sobe 10,5% entre 2022 e 2026, igual ao reajuste citado no case |
| Encadeamento das leituras | `leitura_anterior` de um mês = `leitura_atual` do mês anterior, na mesma UC | 0 quebras |
| Datas | Leitura dentro do mês da competência; fatura emitida depois da leitura | 0 casos fora da regra |

**Ponto para o time:** a tarifa implícita do subgrupo A4 (industrial) cai em 2026, enquanto as demais sobem (insumo para o diagnóstico de receita).
