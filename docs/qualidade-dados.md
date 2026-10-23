# Log de problemas de qualidade

Problemas encontrados no profiling dos arquivos da landing e a decisão de tratamento aplicada na Silver (`data-engineering/notebooks/Bronze_to_Silver.ipynb`). Alimenta o dicionário de dados.

- **Método:** leitura das tabelas Bronze com todas as colunas como texto; perfil por coluna (nulos, nulos disfarçados, espaços sobrando, valores distintos), distribuição das colunas categóricas e checagem da chave.
- **Decisões:** `tratar` (corrigir/padronizar), `descartar` (remover o registro) ou `flag` (manter e sinalizar com `flag_<motivo>`).
- **Confidencialidade:** este arquivo é público e segue a [DEC-024](decisoes.md). Aqui ficam só ID, coluna, problema e decisão; contagens, faixas e evidências detalhadas ficam no relatório privado do time. Nunca colar CPF, nome, linhas reais ou qualquer identificação de pessoa ou de UC.

## unidades_consumidoras

| ID | Coluna | Problema | Decisão |
|---|---|---|---|
| UC-01 | (linha) | Linha de cabeçalho repetida no meio do arquivo | Descartar. Linha com chave nula não é descartada aqui: o notebook para |
| UC-02 | (linha) | Cópias exatas do mesmo registro | Descartar, manter 1 |
| UC-03 | `id_uc` | Mesma UC repetida com formatação diferente em `nome_titular` e `cpf_cnpj`; demais campos iguais | Tratar: padronizar e depois remover as cópias (resta 1 linha por UC) |
| UC-04 | `nome_titular` | Maiúsculas e minúsculas misturadas | Tratar: padronizar para maiúsculas |
| UC-05 | `cpf_cnpj` | Com e sem pontuação | Tratar: manter só os dígitos, como texto (preserva zero à esquerda) |
| UC-06 | `uf` | Várias grafias para Pernambuco (`PE`, `pe`, `pernambuco`, `P.E.`) | Tratar: padronizar para `PE`. `uf` nula continua nula; grafia de outro estado para o notebook |
| UC-07 | `classe` | Variações de maiúscula e acento | Tratar: padronizar (Residencial, Comercial, Industrial, Rural, Poder Público) |
| UC-08 | `cep` | Ausente ou inválido (sem os 8 dígitos) | Tratar: CEP inválido vira nulo. Flag `flag_cep_ausente`, mantendo a UC |
| UC-09 | `cep`, `logradouro` | Espaços sobrando no início/fim | Tratar: remover espaços |
| UC-10 | `status` | Coluna com valor único (`ATIVA`) | Documentar; não serve como filtro |
| UC-11 | `latitude`, `longitude` | Precisão baixa de casas decimais | Documentar; limita uso em mapa |
| UC-12 | `cpf_cnpj` | Mesmo documento de preenchimento (não nulo) repetido num grupo de UCs; o grupo é exatamente o das UCs sem nenhum medidor | Flag `flag_documento_repetido`, mantendo a UC (descartar apagaria o cadastro). O notebook confere que o grupo coincide com as UCs sem medidor |

**Sem problemas:** `municipio`, `bairro` (uma grafia por bairro em cada município, sem nulos), `subgrupo_tarifario` (B1, B2, B3, A4) e a coerência classe × subgrupo (Residencial = B1, Rural = B2, Comercial e Poder Público = B3, Industrial = A4).

**Ponto para o time:** `cpf_cnpj` e `nome_titular` são dados pessoais e não chegam à Gold (campo sensível no contrato).

## faturas

| ID | Coluna | Problema | Decisão |
|---|---|---|---|
| FAT-01 | (linha) | Linha de cabeçalho repetida no meio do arquivo | Descartar. Linha com chave nula não é descartada aqui: o notebook para |
| FAT-02 | `data_emissao` | 4 formatos: `AAAA-MM-DD`, `DD/MM/AAAA`, `DD.MM.AAAA` e `MM-DD-AAAA` | Tratar: converter conforme o formato de cada linha |
| FAT-03 | `valor_total` | Texto em formato de moeda (`R$ 1.234,56`) | Tratar: remover `R$` e ponto de milhar, vírgula vira ponto, `decimal(12,2)` |
| FAT-04 | `data_pagamento` | Ano `9999` usado como "não pago" em faturas `EM ABERTO` | Tratar: converter para nulo |
| FAT-05 | `id_uc` | Faturas de UCs que não existem no cadastro | Flag `flag_uc_orfa`, sem apagar. Destino final (quarentena) definido na integridade referencial |

**Coluna derivada:** `status_pagamento` (`PAGA`, `PAGA COM ATRASO`, `EM ABERTO`), comparando `data_pagamento` com `data_vencimento`. O `status` original é mantido.

**Validações no notebook:** `id_fatura` único e não nulo, `bandeira_tarifaria` no domínio, `mes_referencia` em `AAAA-MM` com mês de 01 a 12, `status` coerente com `data_pagamento`, pagamento nunca antes da emissão, `valor_total = valor_energia + tributos`.

**Ponto para o time:** faturas não têm kWh; a energia faturada vem das leituras.

## leituras

| ID | Coluna | Problema | Decisão |
|---|---|---|---|
| LEI-01 | (linha) | Cópias exatas do mesmo registro | Descartar, manter 1 |
| LEI-02 | `data_leitura` | 4 formatos: `AAAA-MM-DD`, `DD/MM/AAAA`, `DD.MM.AAAA` e `MM-DD-AAAA` | Tratar: converter conforme o formato de cada linha |
| LEI-03 | `leitura_anterior` | Ausente, escrita como nulo, `N/A`, `NULL` ou `-1` | Tratar: converter para nulo. Flag `flag_sem_leitura_anterior` |
| LEI-04 | `id_uc` × `mes_referencia` | Mesma leitura registrada duas vezes, mudando só `id_leitura` e `id_medidor` | Tratar: fica a leitura cujo medidor pertence à UC no cadastro de medidores; se um par não tiver exatamente uma leitura assim, o notebook para. Flag `flag_leitura_duplicada` |
| LEI-05 | `consumo_kwh` | Consumo negativo | Flag `flag_consumo_negativo`, sem apagar |
| LEI-06 | `leitura_atual` | Leitura atual menor que a anterior | Flag `flag_leitura_regressiva`, sem apagar |
| LEI-07 | `consumo_kwh` | Consumo diferente de `leitura_atual − leitura_anterior` | Flag `flag_consumo_divergente` quando a diferença passa de 5% ou 1 kWh, o que for maior (abaixo disso é arredondamento) |

**Validações no notebook:** `id_leitura` único, 1 leitura por UC × competência, `tipo_leitura` no domínio (REAL, ESTIMADA), `mes_referencia` em `AAAA-MM` com mês de 01 a 12, nenhuma leitura de UC fora do cadastro.

**Ponto para o time:** `consumo_kwh` é o valor oficial de energia; as flags indicam onde ele é suspeito. A Gold decide se exclui os casos sinalizados.

## medidores

| ID | Coluna | Problema | Decisão |
|---|---|---|---|
| MED-01 | (linha) | Cópias exatas do mesmo registro | Descartar, manter 1 (depois de limpar espaços). `id_medidor` passa a ser único |
| MED-02 | `modelo` | Espaços sobrando no início/fim | Tratar: remover espaços e padronizar para maiúsculas |
| MED-03 | `tipo` | Várias grafias para 3 categorias (caixa, acento, hífen e `smart meter`) | Tratar: padronizar para `ELETRONICO`, `ELETROMECANICO` e `SMART` |
| MED-04 | `data_instalacao` | 4 formatos: `AAAA-MM-DD`, `DD/MM/AAAA`, `DD.MM.AAAA` e `MM-DD-AAAA` | Tratar: converter conforme o formato de cada linha |
| MED-05 | `data_retirada` | Data sentinela `9999-12-31` usada como nulo em medidores ativos | Tratar: converter para nulo |
| MED-06 | `data_ultima_manutencao` | Coluna vazia na origem | Documentar; manter como `date` nula |

**Validações no notebook:** `id_medidor` único, `tipo` e `status` no domínio, `ATIVO` sem `data_retirada`, `RETIRADO` com `data_retirada` não anterior à instalação, no máximo 1 medidor `ATIVO` por UC, nenhum medidor de UC fora do cadastro.

## geracao_distribuida

| ID | Coluna | Problema | Decisão |
|---|---|---|---|
| GD-01 | `potencia_kwp` | Vírgula como separador decimal | Tratar: trocar vírgula por ponto e converter para `decimal` |
| GD-02 | `potencia_kwp` | Potência muito acima da faixa normal, compatível com registro em `Wp` em vez de `kWp` | Flag `flag_potencia_anomala`, mantendo o registro |

**Sem problemas:** `data_conexao` (formato único `AAAA-MM-DD`), `modalidade` (`GERACAO NA PROPRIA UC`, `AUTOCONSUMO REMOTO`, `GERACAO COMPARTILHADA`) e `energia_injetada_kwh_media_mensal`.

**Validações no notebook:** 1 linha por `id_uc` (deduplicação depois de limpar espaços), nenhuma conversão perdida, nenhuma GD de UC fora do cadastro.

## ocorrencias_rede

| ID | Coluna | Problema | Decisão |
|---|---|---|---|
| OCO-01 | `causa` | Ausência escrita de várias formas (vazio, `-`, `N/A`, `NULL`) | Tratar: converter para nulo. Flag `flag_causa_ausente` |
| OCO-02 | `duracao_min` | Sufixo `" min"` junto ao valor (ex.: `"23 min"`) | Tratar: remover o sufixo e converter para `decimal` |
| OCO-03 | `data_abertura`, `data_encerramento` | Registradas com data e hora | Tratar: converter para `timestamp` |

**Validações no notebook:** `id_ocorrencia` único (deduplicação depois de limpar espaços), encerramento depois da abertura, `duracao_min` igual à diferença entre encerramento e abertura, nenhuma ocorrência de UC fora do cadastro. `tipo` tem 5 categorias (`FALTA DE ENERGIA`, `DANO EM EQUIPAMENTO`, `OSCILACAO`, `SOBRECARGA`, `FIO PARTIDO`).

## atendimentos

| ID | Coluna | Problema | Decisão |
|---|---|---|---|
| ATD-01 | `nota_satisfacao` | Avaliação ausente na origem | Flag `flag_sem_nota_satisfacao`, mantendo nulo |
| ATD-02 | `historico` | Array aninhado de eventos em que o rótulo de `acao` não segue ordem cronológica fixa | Documentar; tipar os campos da struct (`sequencia` inteiro, `data` timestamp) mantendo a estrutura |
| ATD-03 | `data_abertura`, `data_fechamento` | Registradas com data e hora | Tratar: converter para `timestamp` |

**Sem problemas:** `canal`, `assunto` e `subassunto` (coerente com `assunto`), sem nulos nem espaços sobrando; fechamento sempre depois da abertura.

## inspecoes (3 abas → 1 tabela)

As abas `inspecoes_ago_set`, `inspecoes_out_nov` e `inspecoes_dez` viram uma tabela só, `silver.inspecoes`. A coluna `aba_origem` guarda a aba de onde veio cada linha.

| ID | Coluna | Problema | Decisão |
|---|---|---|---|
| INSP-01 | `resultado` | Várias grafias (caixa; `CONFIRMADA` sozinho) | Tratar: padronizar para `IRREGULARIDADE CONFIRMADA` / `SEM IRREGULARIDADE` |
| INSP-02 | `resultado` | Valor `NADA CONSTA`, fora do padrão, com mesmo perfil de `SEM IRREGULARIDADE` | Tratar como `SEM IRREGULARIDADE`. Flag `flag_resultado_nada_consta` |
| INSP-03 | `tipo_irregularidade` | Ausência escrita de várias formas (vazio, `-`, `N/A`, `NULL`) | Tratar: converter para nulo |
| INSP-04 | `data` | 4 formatos: `AAAA-MM-DD`, `DD.MM.AAAA`, `DD/MM/AAAA` e `MM-DD-AAAA` | Tratar: converter conforme o formato de cada linha |
| INSP-05 | `data` × aba | Inspeções lançadas em aba de outros meses | Flag `flag_aba_divergente`: vale a `data`; a aba fica em `aba_origem` |
| INSP-06 | `inspetor` | Espaços sobrando no início/fim | Tratar: remover espaços |
| INSP-07 | `kwh_recuperado` | Vírgula como separador decimal | Tratar: trocar vírgula por ponto e converter para número |

**Validações no notebook:** `id_inspecao` único, 1 inspeção por UC, `resultado` no domínio, irregularidade confirmada sempre com tipo e kWh maior que zero, sem irregularidade sempre sem tipo e com kWh zero, nenhuma inspeção de UC fora do cadastro.

**Ponto para o time:** as inspeções são o gabarito do score de suspeita (ADR-05).

## Validação cruzada (UCs × faturas × leituras)

Conferências entre as tabelas Silver, feitas no notebook depois do tratamento.

| Conferência | Regra |
|---|---|
| Pareamento fatura × leitura | Cada fatura de UC válida tem exatamente uma leitura na mesma UC e competência, e vice-versa |
| Tarifa implícita | `valor_energia ÷ consumo_kwh` em faixa estreita por subgrupo e ano |
| Encadeamento das leituras | `leitura_anterior` de um mês = `leitura_atual` do mês anterior, na mesma UC |
| Datas | Leitura dentro do mês da competência; fatura emitida depois da leitura |
| Alimentadores | Alimentadores das ocorrências existem no cadastro de UCs |
