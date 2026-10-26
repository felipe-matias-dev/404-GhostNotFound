# Dicionário de dados: camada Gold

Definição de cada tabela, coluna e métrica da Gold, com a fórmula e as decisões de limpeza que a afetam. Este documento descreve o **significado**; o nome, o tipo, a nulidade, os valores permitidos e as chaves vêm de [`contracts/gold_schema.yaml`](../contracts/gold_schema.yaml) (versão 0.2.0, rascunho), que é a fonte de verdade. Em caso de divergência, vale o contrato. As decisões de limpeza estão em [`qualidade-dados.md`](qualidade-dados.md), e as decisões de projeto em [`decisoes.md`](decisoes.md).

> **Confidencialidade:** este documento descreve estrutura e regras, sem nenhum dado do dataset ([DEC-024](decisoes.md)).

**Status das colunas:** `confirmada` (já usada pelo backend), `proposta` (nome e significado documentados, tipo e regras por validar) e `a confirmar` (depende da Silver ou de decisão do time). Só as `confirmada` e `proposta` chegam ao agente.

## 1. Convenções

| Tema | Regra |
|---|---|
| Competência | Mês de referência do consumo e da fatura (não o mês de pagamento), texto `AAAA-MM` ([DEC-011](decisoes.md)). |
| Valores em R$ | `numeric(14,2)`, nunca ponto flutuante ([DEC-010](decisoes.md)). Quatro medidas: `receita_faturada` (valor total da fatura), `receita_energia` (só a energia), `tributos` e `receita_arrecadada` (o que foi pago). Total = energia + tributos. |
| Energia | kWh em `numeric(16,3)`. |
| Nulo | Célula vazia no CSV é nulo, nunca zero. Zero é um fato ("não consumiu", "não pagou"); vazio é falta de informação ([DEC-004](decisoes.md)). |
| Listas | Colunas `text[]` vão numa célula só, com os itens separados por `;`. |
| Chaves estrangeiras | Lógicas: checadas na qualidade de dados, sem constraint no banco. |
| Dado pessoal | Só entra mascarado, com `sensitive: true`; o original não chega à Gold ([DEC-022](decisoes.md)). |
| Classe | `classe` guarda B1, B2, B3 ou A4, como o case define "classe de consumo"; `classe_cadastro` guarda as cinco classes do cadastro e separa Comercial de Poder Público, que dividem o B3 ([DEC-023](decisoes.md)). |

Unidades usadas: `R$` (reais); `R$/kWh` (reais por quilowatt-hora); `kWh` (quilowatt-hora); `kWh/mês` (quilowatt-hora por mês); `kWp` (quilowatt-pico (potência de pico da geração solar)); `h` (horas); `UC·h` (consumidor × hora: soma das horas de interrupção de cada UC afetada); `interrupções` (número de interrupções); `contagem` (número de itens (UCs, chamados, interrupções)); `adimensional` (número sem unidade (índice)); `nota` (nota de satisfação do atendimento, de 1 a 5); `posição` (posição em um ranking (1 = primeira)); `dias` (dias corridos).

## 2. Métricas e fórmulas

| Métrica | Definição e fórmula | Observações |
|---|---|---|
| `kwh_faturado` | Energia faturada da UC na competência, já líquida de geração própria. Vale `kwh_leitura` (o consumo apurado) quando o consumo não é negativo; a **leitura atual** quando o consumo é negativo e há medidor instalado na competência (troca de medidor); e o **valor absoluto** quando o consumo é negativo sem medidor novo (sinal invertido). A regra usada fica em `origem_kwh`. | A fatura não tem kWh. A regra foi validada contra o kWh implícito da fatura, e as duas correções são exclusivas e completas ([DEC-023](decisoes.md)). O consumo da leitura já é líquido de GD, como o case descreve. Limpeza: LEI-03 a LEI-07. |
| `tarifa_media` | `receita_energia ÷ kwh_faturado`. Vazia quando `kwh_faturado = 0` (ex.: GD que compensa todo o consumo). | Provisório até a reconciliação do faturamento. |
| `receita_faturada` | Valor emitido na fatura da competência: energia + tributos. | Limpeza: FAT-03 (formato monetário). |
| `receita_energia` | Valor da energia na fatura, sem tributos. Base provisória do PVM e da tarifa média. | A variação percentual da receita é a mesma com e sem tributos; a base muda só os valores absolutos. |
| DEC | Duração equivalente de interrupção por UC: `horas_interrompidas ÷ n_uc`, em horas, com `n_uc` = UCs faturadas (PRODIST). Em um período, divide-se pela média mensal de `n_uc`. | `horas_interrompidas` é em UC·h (soma das durações das ocorrências das UCs do alimentador no mês). Ocorrência que vira o mês entra no mês da abertura. Os valores são simplificados pelo case: servem para comparar alimentadores e períodos, não para comparar com os limites regulatórios. Limpeza: OCO-01 a OCO-03. |
| FEC | Frequência equivalente de interrupção por UC: `n_interrupcoes ÷ n_uc`, com `n_uc` = UCs faturadas. Em um período, divide-se pela média mensal de `n_uc`. | No case, cada ocorrência corresponde a uma UC interrompida. |
| Satisfação média | `soma_notas ÷ n_notas` sobre o recorte escolhido. | Guarda-se a soma e a contagem, e não a média, para agregar corretamente. Limpeza: ATD-01. |
| Efeito preço | Parte da variação da receita explicada pelo preço: `efeito_tarifa + efeito_bandeira`. | `efeito_tarifa` é o reajuste da tarifa base; `efeito_bandeira` é o acréscimo da bandeira (meses com bandeira amarela ou vermelha). No dado, a bandeira é um acréscimo fixo por kWh, igual em todas as classes: a receita sem bandeira é `receita_energia − receita_bandeira` ([DEC-029](decisoes.md)). |
| Efeito volume | Parte da variação explicada pela mudança de energia faturada. | As linhas com `possui_gd = true` isolam o efeito da geração própria. |
| Efeito mix | Parte da variação explicada pela mudança de peso entre classes, medida na empresa inteira. | Calculado, não resíduo. Filtrando um bairro, o efeito mix é a parte daquele bairro no mix da empresa, e não a troca de classes dentro do bairro; volume + mix de cada linha não depende dessa escolha ([DEC-029](decisoes.md)). |
| Checagem do PVM | `abs(efeito_preco + efeito_volume + efeito_mix − (receita_atual − receita_base)) ≤ R$ 0,02` por linha (só o arredondamento dos três efeitos). | É regra de qualidade de dados, não da carga ([DEC-014](decisoes.md)). |
| Score de suspeita | Posição da UC na fila de suspeitas: 1 = mais suspeita. Entram UCs sem GD, com queda de 15% ou mais no consumo médio das 12 últimas competências contra as 12 anteriores; saem as com irregularidade confirmada e as inspecionadas sem irregularidade nos últimos 12 meses. A ordem vem de pontos (queda forte, medidor eletromecânico, leituras estimadas) e depois do kWh a recuperar. | Posição no ranking, e não uma nota. Regras explicáveis, medidas nas inspeções de campo com a janela na data de cada inspeção (precisão e cobertura saem a cada carga) ([DEC-030](decisoes.md)). |
| `possui_gd` | A UC tem geração própria conectada. Em `gold_kpis_segmento_mensal`, vale por competência (a partir do mês da conexão); em `gold_receita_decomposicao`, é o estado no último mês do período atual. | A UC que conectou entre os períodos fica no grupo com GD dos dois lados da decomposição (DEC-023). |
| Potência | Potência de pico instalada, em kWp. | A origem só traz potência de pico. Os registros com potência muito acima do normal (GD-02) estão em Wp e são convertidos para kWp, conferidos pela faixa e pela energia injetada por kWp ([DEC-030](decisoes.md)). |
| Situação da fatura (`status_pagamento`) | Calculada na Gold contra a **data de corte** (a maior data presente nas faturas): `paga` (paga até o vencimento), `paga_com_atraso`, `em_aberto` (não paga e ainda no prazo) e `em_atraso` (não paga e vencida). `dias_em_atraso` = dias entre o vencimento e o pagamento (ou a data de corte). | Uma UC tem uma única fatura por competência, então a situação vive no fato. A Silver só distingue paga, paga com atraso e em aberto. No dataset do case todas as faturas não pagas estão em atraso, porque o corte é posterior a todos os vencimentos. Limpeza: FAT-04. |
| Inadimplência | `valor_nao_pago ÷ receita_faturada` no recorte e período escolhidos. | A situação da fatura é medida na data de corte: numa competência antiga, conta as faturas daquele mês que continuam sem pagamento hoje. Limpeza: FAT-04. |
| Atraso médio | `soma_dias_em_atraso ÷ faturas com atraso` (pagas com atraso + não pagas e vencidas). | Mesma data de corte. |
| Leituras estimadas | `n_leituras_estimadas ÷ n_leituras`. | Sinal de erro de leitura (H5). |
| Idade do medidor | Anos entre a instalação do medidor vigente e o fim da última competência dos dados (`gold_medidor_uc`). | A data da última manutenção não existe na origem (MED-06): "medidor sem manutenção" não é respondível. |
| Pares de períodos da decomposição | A Gold grava todos os pares de **mesmos meses em anos diferentes** (qualquer mês de início, 1 a 12 meses, qualquer par de anos com dado). | Totais e comparações de qualquer período saem da soma dos meses em `gold_kpis_segmento_mensal`. A decomposição de trechos diferentes (ex.: jan–abr × mar–jun) não é gravada, porque todas as combinações passariam de 1 bilhão de linhas; se o portal precisar, o backend calcula na hora com a mesma fórmula ([DEC-028](decisoes.md)). |
| Reconciliação | Ponte do número bruto até o usado nos indicadores, por competência. Receita: total de todas as faturas = cadastro + UCs fora do cadastro; cadastro = energia + tributos. Energia: consumo apurado nas leituras + correção das trocas de medidor + correção do sinal invertido = energia faturada. | Tabela `gold_reconciliacao_faturamento`. As faturas de UCs fora do cadastro (FAT-05) ficam fora do fato por UC, mas nunca são descartadas: aparecem ali. Responde qual receita é considerada, quanto vem de faturas sem cadastro e de onde vem a diferença entre a receita da diretoria e a nossa. |

### KPIs por recorte: como agregar

`gold_kpis_segmento_mensal` guarda **componentes somáveis**, nunca índices prontos. Para qualquer filtro (município, bairro, classe, GD, alimentador, tipo de medidor e período), soma-se cada componente nas linhas escolhidas e calcula-se o índice no fim. Receitas, kWh, horas, interrupções e notas são fluxos e somam entre meses; `n_uc` é um estoque e só soma dentro do mesmo mês, então para vários meses usa-se a média mensal. A soma por competência bate com `gold_kpis_mensais` (total da empresa) e com `gold_continuidade_alimentador_mensal`.

## 3. Tabelas

### `gold_dim_uc`

Dimensão de unidades consumidoras.

- **Grão:** 1 linha por UC
- **Chave:** `cod_uc`
- **Consumidores:** UC 360, agente, filtros
- **Decisões de limpeza que afetam esta tabela:** UC-01 a UC-12 (cadastro; a flag `flag_documento_repetido` da UC-12 fica só na Silver, DEC-023), MED-01 a MED-06 (medidores), GD-01 e GD-02 (potência e conexão)

| Coluna | Tipo | Nulo | Unidade | Status | Definição |
|---|---|---|---|---|---|
| `cod_uc` | text | não |  | confirmada | Código da unidade consumidora (ponto com medidor). |
| `municipio` | text | não |  | confirmada | Município da UC. |
| `bairro` | text | não |  | confirmada | Bairro da UC. |
| `classe` | text (B1, B2, B3, A4) | não |  | confirmada | Classe de consumo como no case: B1 residencial, B2 rural, B3 comercial e poder público, A4 industrial MT; define a tarifa. |
| `classe_cadastro` | text (Residencial, Comercial, Industrial, Rural, Poder Público) | não |  | proposta | Classe da UC no cadastro comercial; separa Comercial de Poder Público, que dividem o B3. Opção B da DEC-023: acrescenta a coluna sem mudar classe, que backend e agente já usam. |
| `cod_alimentador` | text | não |  | confirmada | Alimentador (circuito de média tensão) que atende a UC. |
| `possui_gd` | boolean | não |  | confirmada | A UC tem geração própria (ex.: solar). |
| `consumo_medio_kwh_12m` | numeric(16,3) | sim | kWh/mês | confirmada | Consumo médio mensal da UC nos últimos 12 meses; vazio quando a UC não tem leitura. Nulo, e não zero: há UCs do cadastro sem nenhuma leitura (log da Silver), e sem leitura não há média (DEC-023). |
| `titular_mascarado` | text | sim |  | proposta | Iniciais do titular da UC, para o atendente confirmar a identidade na UC 360. **Sensível: fora do agente.** O nome completo não chega à Gold; fora do agente (DEC-023). |
| `documento_mascarado` | text | sim |  | proposta | Documento do titular com só os 3 últimos dígitos, para o atendente confirmar a identidade. **Sensível: fora do agente.** O documento completo não chega à Gold; fora do agente (DEC-023). |
| `potencia_kwp` | double precision | sim | kWp | proposta | Potência de pico instalada da geração própria; só para UCs com GD. Era potencia_kw: a origem só traz potência de pico (kWp), e kW seria outra grandeza (DEC-023). Os registros com potência anômala da Silver (GD-02) estão em Wp e são convertidos para kWp: o valor convertido cai na faixa normal e a energia injetada por kWp passa a bater com a das demais UCs (DEC-030). |
| `data_ligacao` | date | não |  | proposta | Data em que a UC foi ligada (cliente desde). A UC conta no n_uc a partir do mês da ligação (DEC-030). |
| `data_conexao_gd` | date | sim |  | proposta | Data em que a geração própria foi conectada; vazia sem GD. Permite comparar o consumo da UC antes e depois da conexão (H1, UC 360). |
| `modalidade_gd` | text (geracao_propria_uc, autoconsumo_remoto, geracao_compartilhada) | sim |  | proposta | Modalidade da geração própria; vazia sem GD. |
| `energia_injetada_kwh_mes` | numeric(16,3) | sim | kWh/mês | proposta | Energia média injetada na rede por mês pela geração própria; vazia sem GD. |

### `gold_fato_faturamento_mensal`

Faturamento por UC e competência.

- **Grão:** UC × competência
- **Chave:** `cod_uc`, `competencia`
- **Consumidores:** KPIs, tela Receita, UC 360, agente
- **Chave estrangeira (lógica):** cod_uc → gold_dim_uc.cod_uc
- **Decisões de limpeza que afetam esta tabela:** FAT-01 a FAT-05 (faturas), LEI-01 a LEI-07 (leituras e consumo), MED-03 (tipo do medidor)

| Coluna | Tipo | Nulo | Unidade | Status | Definição |
|---|---|---|---|---|---|
| `cod_uc` | text | não |  | proposta | Código da unidade consumidora. |
| `competencia` | text | não |  | proposta | Mês de referência do consumo e da fatura (não o mês de pagamento). |
| `kwh_faturado` | numeric(16,3) | não | kWh | proposta | Energia cobrada na fatura, já líquida de GD. Regra em origem_kwh, validada contra o kWh implícito da fatura; o consumo da leitura já é líquido de GD, conferido contra a energia injetada (DEC-023). |
| `kwh_leitura` | numeric(16,3) | não | kWh | proposta | Consumo apurado na leitura, sem correção (consumo_kwh da Silver). Pode ser negativo; guardado para rastrear a correção. |
| `origem_kwh` | text (leitura, leitura_atual_troca_medidor, consumo_absoluto) | não |  | proposta | Regra que gerou kwh_faturado: o próprio consumo da leitura (consumo não negativo); a leitura atual quando o consumo é negativo e há medidor instalado na competência (troca de medidor); ou o valor absoluto quando o consumo é negativo sem medidor novo (sinal invertido). |
| `receita_faturada` | numeric(14,2) | não | R$ | proposta | Valor total emitido na fatura da competência (energia + tributos). |
| `receita_energia` | numeric(14,2) | não | R$ | proposta | Valor da energia na fatura, sem tributos. Base provisória da receita comercial no PVM até a reconciliação (DEC-023). |
| `tributos` | numeric(14,2) | não | R$ | proposta | Tributos cobrados na fatura. |
| `receita_arrecadada` | numeric(14,2) | sim | R$ | proposta | Valor efetivamente pago. |
| `tarifa_media` | double precision | sim | R$/kWh | proposta | Receita de energia dividida pela energia faturada (sem tributos). receita_energia ÷ kwh_faturado, provisório até a reconciliação (DEC-023); NULL quando kwh_faturado = 0 (ex.: GD que compensa todo o consumo). |
| `bandeira` | text (verde, amarela, vermelha_p1, vermelha_p2) | sim |  | proposta | Bandeira tarifária da competência (acréscimo mensal). A Silver usa Verde, Amarela, Vermelha P1 e Vermelha P2; a Gold converte para este formato. |
| `data_vencimento` | date | não |  | proposta | Data de vencimento da fatura. |
| `data_pagamento` | date | sim |  | proposta | Data em que a fatura foi paga; vazia quando não foi paga. A Silver converte o ano 9999 (código de não pago) em nulo (FAT-04). |
| `status_pagamento` | text (paga, paga_com_atraso, em_aberto, em_atraso) | não |  | proposta | Situação da fatura na data de corte: paga (até o vencimento), paga com atraso, em aberto (não paga e ainda no prazo) ou em atraso (não paga e vencida). Regra em conventions.invoice_status; a Silver só distingue paga, paga com atraso e em aberto. |
| `dias_em_atraso` | integer | sim | dias | proposta | Dias de atraso: da data de pagamento depois do vencimento (paga com atraso) ou da data de corte depois do vencimento (em atraso); vazio nos demais casos. Dá ao portal a gravidade do atraso sem precisar conhecer a data de corte. |
| `receita_bandeira` | numeric(14,2) | não | R$ | proposta | Parte da receita de energia que é acréscimo da bandeira tarifária do mês (zero na bandeira verde). kwh_faturado × acréscimo da bandeira por kWh (DEC-029); receita_energia - receita_bandeira é a receita pela tarifa base. |
| `tipo_leitura` | text (real, estimada) | não |  | proposta | Se a leitura do mês foi feita no medidor (real) ou estimada. |
| `tipo_medidor` | text (eletromecanico, eletronico, smart) | não |  | proposta | Tipo do medidor que fez a leitura do mês. |
| `dias_faturados` | integer | sim | dias | proposta | Dias entre a leitura do mês e a do mês anterior; vazio na primeira leitura da UC. Explica parte da variação da conta (insight conta alta, G2-05). |

**Validações:**
- receita_faturada = receita_energia + tributos (por linha, diferença máxima de R$ 0,01)
- 0 <= receita_bandeira <= receita_energia; receita_bandeira = 0 quando a bandeira é verde
- data_pagamento vazia se e somente se status_pagamento é em_aberto ou em_atraso; dias_em_atraso vazio quando a fatura foi paga até o vencimento ou está em aberto

### `gold_receita_decomposicao`

Decomposição da variação de receita entre dois períodos (PVM com efeito mix).

- **Grão:** par de períodos × município × bairro × classe × possui_gd
- **Chave:** `periodo_base`, `periodo_atual`, `municipio`, `bairro`, `classe`, `possui_gd`
- **Consumidores:** tela Receita, insight, diagnóstico, agente
- **Pares de períodos:** Todos os pares de 'mesmos meses em anos diferentes' com dado nos dois lados: para cada mês de início, cada duração de 1 a 12 meses e cada par de anos (ex.: 2024-01/2024-04 x 2025-01/2025-04; 2022-07/2023-06 x 2025-07/2026-06). Outros pares (trechos diferentes, ex.: jan-abr x mar-jun) não são gravados: todas as combinações passariam de 1 bilhão de linhas. Se o portal precisar deles, o backend calcula na hora com a mesma fórmula, a partir de gold_fato_faturamento_mensal e receita_bandeira (DEC-028).
- **Decisões de limpeza que afetam esta tabela:** FAT-03 e FAT-05, LEI-03 a LEI-07, GD-01

| Coluna | Tipo | Nulo | Unidade | Status | Definição |
|---|---|---|---|---|---|
| `periodo_base` | text | não |  | proposta | Faixa de meses do período inicial da comparação. Texto AAAA-MM/AAAA-MM (ex.: 2022-07/2023-06), formato confirmado; aceita qualquer par de períodos (ex.: os mesmos meses em anos diferentes). |
| `periodo_atual` | text | não |  | proposta | Faixa de meses do período comparado. Texto AAAA-MM/AAAA-MM (ex.: 2025-07/2026-06), formato confirmado. |
| `municipio` | text | não |  | proposta | Município. |
| `bairro` | text | não |  | proposta | Bairro. |
| `classe` | text (B1, B2, B3, A4) | não |  | proposta | Classe de consumo (B1, B2, B3, A4). |
| `possui_gd` | boolean | não |  | proposta | A UC tinha geração própria conectada no último mês do período atual; o efeito GD é o efeito volume das linhas com possui_gd = true. DEC-023: separa a queda de volume da GD do restante sem coluna de efeito própria. O grupo vale para a UC nos dois períodos: quem conectou a GD entre eles fica no grupo com GD de ambos os lados (DEC-023). |
| `receita_base` | numeric(14,2) | não | R$ | proposta | Receita de energia (sem tributos) no período base. Base provisória: receita_energia, até a reconciliação (DEC-023). |
| `receita_atual` | numeric(14,2) | não | R$ | proposta | Receita de energia (sem tributos) no período atual. Base provisória: receita_energia, até a reconciliação (DEC-023). |
| `efeito_preco` | numeric(14,2) | não | R$ | proposta | Parte da variação de receita explicada pela mudança de preço: efeito_tarifa + efeito_bandeira. |
| `efeito_tarifa` | numeric(14,2) | não | R$ | proposta | Parte do efeito preço explicada pelo reajuste da tarifa base, sem a bandeira. |
| `efeito_bandeira` | numeric(14,2) | não | R$ | proposta | Parte do efeito preço explicada pelo acréscimo da bandeira tarifária (meses com bandeira amarela ou vermelha). Método na DEC-029: a bandeira é um acréscimo fixo por kWh; efeito_tarifa usa a receita sem o acréscimo. |
| `efeito_volume` | numeric(14,2) | não | R$ | proposta | Parte da variação de receita explicada pela mudança de energia faturada. |
| `efeito_mix` | numeric(14,2) | não | R$ | proposta | Parte da variação de receita explicada pela mudança de peso entre classes. Mede o peso das classes na empresa inteira: filtrando um bairro, o efeito mix é a parte daquele bairro no mix da empresa, e não a troca de classes dentro do bairro. |

**Validações:**
- |efeito_preco - (efeito_tarifa + efeito_bandeira)| <= R$ 0,01 por linha
- |efeito_preco + efeito_volume + efeito_mix - (receita_atual - receita_base)| <= R$ 0,02 por linha (só o arredondamento dos três efeitos; DEC-014). O mix é calculado, não resíduo.

### `gold_kpis_mensais`

Indicadores executivos por competência: total da empresa, igual à soma de gold_kpis_segmento_mensal por competência.

- **Grão:** 1 linha por competência
- **Chave:** `competencia`
- **Consumidores:** dashboard executivo, GET /receita/mensal, agente
- **Decisões de limpeza que afetam esta tabela:** FAT-03, LEI-03 a LEI-07, OCO-01 a OCO-03, ATD-01 a ATD-03

| Coluna | Tipo | Nulo | Unidade | Status | Definição |
|---|---|---|---|---|---|
| `competencia` | text | não |  | proposta | Mês de referência. |
| `kwh_faturado` | numeric(16,3) | não | kWh | proposta | Energia faturada no mês, somando todas as UCs. |
| `receita_faturada` | numeric(14,2) | não | R$ | proposta | Receita faturada no mês (energia + tributos), somando todas as UCs. |
| `receita_energia` | numeric(14,2) | não | R$ | proposta | Receita de energia no mês (sem tributos), somando todas as UCs. |
| `dec` | double precision | sim | h | proposta | DEC do mês: duração equivalente de interrupção por UC. |
| `fec` | double precision | sim | interrupções | proposta | FEC do mês: frequência equivalente de interrupção por UC. |
| `n_chamados` | integer | sim | contagem | proposta | Chamados de atendimento abertos no mês (pela data de abertura). Vazio quando não há atendimento carregado no período. |
| `satisfacao_media` | double precision | sim | nota | proposta | Nota média de satisfação dos chamados abertos no mês, de 1 a 5. Soma das notas ÷ chamados com nota; chamados sem nota ficam fora da média (ATD-01). |

**Validações:**
- kwh_faturado, receita_faturada e receita_energia = soma de gold_kpis_segmento_mensal na competência

### `gold_kpis_segmento_mensal`

KPIs por recorte (município, bairro, classe e geração própria) e competência, guardados como componentes somáveis. Qualquer período é a soma das competências escolhidas. O portal e o agente somam os componentes do filtro e calculam os índices no final.

- **Grão:** competência × município × bairro × classe_cadastro × possui_gd × alimentador × tipo de medidor
- **Chave:** `competencia`, `municipio`, `bairro`, `classe_cadastro`, `possui_gd`, `cod_alimentador`, `tipo_medidor`
- **Consumidores:** dashboard executivo, filtros da diretoria, agente
- **Decisões de limpeza que afetam esta tabela:** FAT-03 a FAT-05, LEI-02 a LEI-07, MED-03 a MED-05 (medidor vigente), OCO-01 a OCO-04, ATD-01 a ATD-03

| Coluna | Tipo | Nulo | Unidade | Status | Definição |
|---|---|---|---|---|---|
| `competencia` | text | não |  | proposta | Mês de referência. |
| `municipio` | text | não |  | proposta | Município. |
| `bairro` | text | não |  | proposta | Bairro (o mesmo nome pode existir em municípios diferentes: sempre junto com o município). |
| `classe_cadastro` | text (Residencial, Comercial, Industrial, Rural, Poder Público) | não |  | proposta | Classe da UC no cadastro comercial. |
| `classe` | text (B1, B2, B3, A4) | não |  | proposta | Classe de consumo (B1, B2, B3, A4); determinada pela classe do cadastro. |
| `possui_gd` | boolean | não |  | proposta | A UC já tinha geração própria conectada na competência (data de conexão até o mês). Por competência, e não o estado atual: antes da conexão a UC conta como sem GD, o que permite comparar antes e depois. |
| `cod_alimentador` | text | não |  | proposta | Alimentador que atende as UCs do recorte (do cadastro da UC). Cada bairro é atendido por 1 ou 2 alimentadores; permite cruzar continuidade com bairro, classe e GD (DEC-027). |
| `tipo_medidor` | text (eletromecanico, eletronico, smart, sem_medidor) | não |  | proposta | Tipo do medidor vigente na UC na competência; sem_medidor quando a UC não tem medidor instalado no mês. Vigente pela data de instalação e de retirada: muda quando o medidor é trocado (DEC-027). |
| `n_uc` | integer | não | contagem | proposta | UCs faturadas no recorte, na competência (denominador do DEC/FEC, como no PRODIST). É um estoque: some só dentro do mesmo mês. Para um período de vários meses, o DEC e o FEC usam a média mensal (soma de n_uc ÷ número de meses). |
| `kwh_faturado` | numeric(16,3) | não | kWh | proposta | Energia faturada no recorte. |
| `receita_faturada` | numeric(14,2) | não | R$ | proposta | Receita faturada no recorte (energia + tributos). |
| `receita_energia` | numeric(14,2) | não | R$ | proposta | Receita de energia no recorte (sem tributos). |
| `tributos` | numeric(14,2) | não | R$ | proposta | Tributos no recorte. |
| `receita_arrecadada` | numeric(14,2) | sim | R$ | proposta | Valor efetivamente pago no recorte. Vazio quando o recorte não tem fatura na competência (não arrecadar e não ter fatura são coisas diferentes); zero quando há fatura e nada foi pago (DEC-030). |
| `horas_interrompidas` | double precision | não | UC·h | proposta | Soma das horas de interrupção das UCs do recorte. DEC de um mês = soma de horas ÷ soma de n_uc do mês; de um período = soma de horas ÷ média mensal de n_uc, calculado no portal e no agente sobre o filtro escolhido. |
| `n_interrupcoes` | integer | não | contagem | proposta | Número de ocorrências das UCs do recorte. FEC de um mês = soma de n_interrupcoes ÷ soma de n_uc do mês; de um período = soma de n_interrupcoes ÷ média mensal de n_uc. |
| `n_chamados` | integer | não | contagem | proposta | Chamados de atendimento das UCs do recorte, abertos no mês (pela data de abertura). |
| `soma_notas` | double precision | sim | nota | proposta | Soma das notas de satisfação (de 1 a 5) dos chamados avaliados. Vazio quando nenhum chamado do recorte foi avaliado (n_notas = 0). Guardar soma e contagem, e não a média, para agregar corretamente entre recortes (DEC-030). |
| `n_notas` | integer | não | contagem | proposta | Chamados com nota de satisfação. Satisfação média = soma de soma_notas ÷ soma de n_notas (ATD-01: chamado sem nota fica fora). |
| `receita_bandeira` | numeric(14,2) | não | R$ | proposta | Parte da receita de energia do recorte que é acréscimo de bandeira. receita_energia - receita_bandeira = receita pela tarifa base (DEC-029). |
| `n_faturas` | integer | não | contagem | proposta | Faturas emitidas para as UCs do recorte na competência. |
| `n_faturas_nao_pagas` | integer | não | contagem | proposta | Faturas da competência ainda não pagas na data de corte (em aberto ou em atraso). Situação medida na data de corte, e não no mês da fatura: numa competência antiga, conta as faturas daquele mês que continuam sem pagamento hoje (DEC-027). |
| `valor_nao_pago` | numeric(14,2) | não | R$ | proposta | Valor das faturas da competência ainda não pagas na data de corte. Inadimplência do recorte = valor_nao_pago ÷ receita_faturada; mesma semântica da data de corte. |
| `n_faturas_pagas_com_atraso` | integer | não | contagem | proposta | Faturas da competência pagas depois do vencimento. |
| `soma_dias_em_atraso` | integer | não | dias | proposta | Soma dos dias de atraso das faturas com atraso (pagas com atraso ou em atraso). Atraso médio = soma_dias_em_atraso ÷ (n_faturas_pagas_com_atraso + faturas em atraso). |
| `n_leituras` | integer | não | contagem | proposta | Leituras das UCs do recorte na competência. |
| `n_leituras_estimadas` | integer | não | contagem | proposta | Leituras estimadas (não feitas no medidor) das UCs do recorte na competência. Parte de leituras estimadas = n_leituras_estimadas ÷ n_leituras (H5). |

**Validações:**
- soma por competência de kwh_faturado, receita_faturada e receita_energia = gold_kpis_mensais
- soma por competência e alimentador de n_uc, horas_interrompidas e n_interrupcoes = gold_continuidade_alimentador_mensal
- receita_faturada = receita_energia + tributos por linha (diferença máxima de R$ 0,01)
- índices (DEC, FEC, satisfação) não são guardados: só componentes somáveis, para qualquer filtro dar o mesmo resultado que a empresa inteira

### `gold_continuidade_alimentador_mensal`

DEC e FEC por alimentador e competência.

- **Grão:** alimentador × competência
- **Chave:** `cod_alimentador`, `competencia`
- **Consumidores:** tela DEC/FEC, agente
- **Decisões de limpeza que afetam esta tabela:** OCO-01 a OCO-04 (ocorrências; a OCO-04 tira as registradas antes da ligação da UC)

| Coluna | Tipo | Nulo | Unidade | Status | Definição |
|---|---|---|---|---|---|
| `cod_alimentador` | text | não |  | proposta | Alimentador (circuito de média tensão). |
| `competencia` | text | não |  | proposta | Mês de referência. |
| `dec` | double precision | não | h | proposta | Duração equivalente de interrupção por UC no alimentador. horas_interrompidas ÷ n_uc (DEC-014). |
| `fec` | double precision | não | interrupções | proposta | Frequência equivalente de interrupção por UC no alimentador. n_interrupcoes ÷ n_uc (DEC-014). |
| `n_uc` | integer | não | contagem | proposta | UCs faturadas atendidas pelo alimentador na competência, e não só as afetadas. PRODIST: o denominador é o de UCs faturadas; ficam fora as UCs sem fatura no mês, como as da UC-12 (DEC-023). |
| `n_interrupcoes` | integer | não | contagem | proposta | Número de ocorrências das UCs do alimentador no mês. No case, cada ocorrência corresponde a uma UC interrompida; ocorrência que vira o mês entra no mês da abertura (DEC-014). |
| `horas_interrompidas` | double precision | não | UC·h | proposta | Soma das durações das ocorrências das UCs do alimentador no mês. Consumidor × hora; ocorrência que vira o mês entra no mês da abertura (DEC-014). |

### `gold_interrupcoes_uc`

Interrupções que afetaram cada UC (UC 360).

- **Grão:** UC × ocorrência
- **Chave:** `cod_ocorrencia`
- **Consumidores:** UC 360, agente
- **Chave estrangeira (lógica):** cod_uc → gold_dim_uc.cod_uc
- **Decisões de limpeza que afetam esta tabela:** OCO-01 a OCO-04

| Coluna | Tipo | Nulo | Unidade | Status | Definição |
|---|---|---|---|---|---|
| `cod_ocorrencia` | text | não |  | proposta | Código da ocorrência de rede. |
| `cod_uc` | text | não |  | proposta | Código da unidade consumidora interrompida. |
| `cod_alimentador` | text | não |  | proposta | Alimentador da UC (do cadastro). |
| `competencia` | text | não |  | proposta | Mês da abertura da ocorrência. Ocorrência que vira o mês entra no mês da abertura (DEC-014). |
| `data_abertura` | timestamp | não |  | proposta | Início da interrupção. |
| `data_encerramento` | timestamp | não |  | proposta | Fim da interrupção. |
| `duracao_horas` | double precision | não | h | proposta | Duração da interrupção em horas. |
| `tipo` | text | não |  | proposta | Tipo da ocorrência (ex.: FALTA DE ENERGIA, OSCILACAO). |
| `causa` | text | sim |  | proposta | Causa registrada (ex.: CLIMATICA, VEGETACAO); vazia quando não foi registrada (OCO-01). |

**Validações:**
- soma por competência e alimentador de duracao_horas e contagem = gold_continuidade_alimentador_mensal
- nenhuma ocorrência antes do mês de ligação da UC (DEC-030)

### `gold_atendimentos_uc`

Chamados de atendimento por UC (UC 360).

- **Grão:** UC × chamado
- **Chave:** `protocolo`
- **Consumidores:** UC 360, agente
- **Chave estrangeira (lógica):** cod_uc → gold_dim_uc.cod_uc
- **Decisões de limpeza que afetam esta tabela:** ATD-01 a ATD-03

| Coluna | Tipo | Nulo | Unidade | Status | Definição |
|---|---|---|---|---|---|
| `protocolo` | text | não |  | proposta | Protocolo do chamado. |
| `cod_uc` | text | não |  | proposta | Código da unidade consumidora. |
| `competencia` | text | não |  | proposta | Mês de abertura do chamado. |
| `data_abertura` | timestamp | não |  | proposta | Abertura do chamado. |
| `data_fechamento` | timestamp | não |  | proposta | Fechamento do chamado. |
| `canal` | text | não |  | proposta | Canal de entrada (ex.: TELEFONE, APP, WHATSAPP). |
| `assunto` | text | não |  | proposta | Assunto do chamado (ex.: FALTA DE ENERGIA, FATURA). |
| `subassunto` | text | sim |  | proposta | Detalhe do assunto. |
| `nota_satisfacao` | double precision | sim | nota | proposta | Nota de satisfação de 1 a 5; vazia quando o cliente não avaliou (ATD-01). |

> O histórico de interações do chamado (texto livre) fica fora da Gold: é dado sensível e não é usado pelo portal nem pelo agente.

### `gold_medidor_uc`

Medidor vigente de cada UC e o histórico de trocas (UC 360).

- **Grão:** 1 linha por UC com medidor
- **Chave:** `cod_uc`
- **Consumidores:** UC 360, score de suspeita, agente
- **Chave estrangeira (lógica):** cod_uc → gold_dim_uc.cod_uc
- **Decisões de limpeza que afetam esta tabela:** MED-01 a MED-06 (MED-06: sem data de manutenção na origem)

| Coluna | Tipo | Nulo | Unidade | Status | Definição |
|---|---|---|---|---|---|
| `cod_uc` | text | não |  | proposta | Código da unidade consumidora. |
| `cod_medidor` | text | não |  | proposta | Código do medidor vigente. |
| `tipo_medidor` | text (eletromecanico, eletronico, smart) | não |  | proposta | Tipo do medidor vigente. |
| `modelo` | text | sim |  | proposta | Modelo do medidor vigente. |
| `data_instalacao` | date | não |  | proposta | Instalação do medidor vigente. |
| `idade_anos` | double precision | não | anos | proposta | Idade do medidor vigente no fim da última competência dos dados. |
| `n_trocas` | integer | não | contagem | proposta | Medidores já retirados da UC. |
| `data_ultima_troca` | date | sim |  | proposta | Retirada do medidor anterior; vazia se nunca houve troca. |

> UCs sem medidor (UC-12) não têm linha. A data da última manutenção não existe na origem (MED-06), então 'medidor sem manutenção' não é respondível.

### `gold_inspecoes_uc`

Inspeções de campo por UC: histórico na UC 360, taxa de irregularidade por recorte (H2) e régua da fila de suspeitas.

- **Grão:** UC × inspeção
- **Chave:** `cod_inspecao`
- **Consumidores:** UC 360, tela Perdas, diagnóstico
- **Chave estrangeira (lógica):** cod_uc → gold_dim_uc.cod_uc
- **Decisões de limpeza que afetam esta tabela:** INSP-01 a INSP-07

| Coluna | Tipo | Nulo | Unidade | Status | Definição |
|---|---|---|---|---|---|
| `cod_inspecao` | text | não |  | proposta | Código da inspeção. |
| `cod_uc` | text | não |  | proposta | Código da unidade consumidora inspecionada. |
| `data_inspecao` | date | não |  | proposta | Data da inspeção (vale a data, não a aba de origem: INSP-05). |
| `competencia` | text | não |  | proposta | Mês da inspeção. |
| `resultado` | text (irregularidade_confirmada, sem_irregularidade) | não |  | proposta | Resultado da inspeção. |
| `tipo_irregularidade` | text | sim |  | proposta | Tipo da irregularidade (ex.: DESVIO DIRETO, BY-PASS); vazio sem irregularidade. |
| `kwh_recuperado` | numeric(16,3) | não | kWh | proposta | Energia recuperada com a regularização; zero sem irregularidade. |

> O nome do inspetor fica fora da Gold (dado pessoal sem uso no portal).

### `gold_reconciliacao_faturamento`

Ponte do faturamento e da energia, do número bruto até o usado nos indicadores, por competência, com cada parcela e o motivo.

- **Grão:** 1 linha por competência
- **Chave:** `competencia`
- **Consumidores:** diagnóstico, tela Receita, agente
- **Decisões de limpeza que afetam esta tabela:** FAT-01 a FAT-05 (faturas, inclusive as de UCs fora do cadastro), LEI-03 a LEI-07 (correção do consumo)

| Coluna | Tipo | Nulo | Unidade | Status | Definição |
|---|---|---|---|---|---|
| `competencia` | text | não |  | proposta | Mês de referência. |
| `receita_faturada_total` | numeric(14,2) | não | R$ | proposta | Soma de todas as faturas da competência (energia + tributos), inclusive as de UCs fora do cadastro. |
| `receita_faturada_orfas` | numeric(14,2) | não | R$ | proposta | Parte da receita total em faturas de UCs fora do cadastro. Ficam fora do fato por UC, mas nunca são descartadas (FAT-05). |
| `receita_faturada_cadastro` | numeric(14,2) | não | R$ | proposta | Receita total das UCs do cadastro; igual à soma de receita_faturada em gold_fato_faturamento_mensal. |
| `tributos_cadastro` | numeric(14,2) | não | R$ | proposta | Tributos das faturas das UCs do cadastro. |
| `receita_energia_cadastro` | numeric(14,2) | não | R$ | proposta | Receita de energia das UCs do cadastro, base dos indicadores (base provisória do PVM). |
| `n_faturas_orfas` | integer | não | contagem | proposta | Faturas de UCs fora do cadastro. |
| `kwh_leitura_total` | numeric(16,3) | não | kWh | proposta | Soma do consumo apurado nas leituras, sem correção. As UCs fora do cadastro não têm leitura, então a ponte de energia é só do cadastro. |
| `kwh_correcao_troca_medidor` | numeric(16,3) | não | kWh | proposta | Ajuste das trocas de medidor: leitura atual no lugar do consumo negativo. Soma de (kwh_faturado - kwh_leitura) onde origem_kwh = leitura_atual_troca_medidor. |
| `kwh_correcao_sinal_invertido` | numeric(16,3) | não | kWh | proposta | Ajuste do consumo com o sinal invertido: valor absoluto no lugar do consumo negativo. Soma de (kwh_faturado - kwh_leitura) onde origem_kwh = consumo_absoluto. |
| `kwh_faturado_total` | numeric(16,3) | não | kWh | proposta | Energia faturada final, já líquida de GD; igual à soma de kwh_faturado em gold_fato_faturamento_mensal. |

**Validações:**
- receita_faturada_total = receita_faturada_cadastro + receita_faturada_orfas (diferença máxima de R$ 0,01)
- receita_faturada_cadastro = receita_energia_cadastro + tributos_cadastro (diferença máxima de R$ 0,01)
- kwh_faturado_total = kwh_leitura_total + kwh_correcao_troca_medidor + kwh_correcao_sinal_invertido (diferença máxima de 0,001 kWh)
- receita_faturada_cadastro, receita_energia_cadastro, tributos_cadastro e kwh_faturado_total = soma por competência de gold_fato_faturamento_mensal

### `gold_fila_suspeitas`

UCs suspeitas de perda não técnica, ordenadas por prioridade.

- **Grão:** 1 linha por UC suspeita
- **Chave:** `cod_uc`
- **Consumidores:** tela Perdas, ordens de inspeção
- **Chave estrangeira (lógica):** cod_uc → gold_dim_uc.cod_uc
- **Decisões de limpeza que afetam esta tabela:** INSP-01 a INSP-07 (inspeções, gabarito do score), LEI-03 a LEI-07, MED-03

| Coluna | Tipo | Nulo | Unidade | Status | Definição |
|---|---|---|---|---|---|
| `cod_uc` | text | não |  | proposta | Código da unidade consumidora suspeita. |
| `score_suspeita` | integer | não | posição | proposta | Posição da UC no ranking de suspeita: 1 = mais suspeita. Posição no ranking, não nota (decisão da daily de 21/10). |
| `motivos` | text[] | não |  | proposta | Regras ou fatores que mais explicam o score, em texto legível. No CSV, itens separados por ; na mesma célula. |
| `kwh_recuperavel_est` | numeric(16,3) | sim | kWh/mês | proposta | Energia estimada a recuperar por mês se a irregularidade for confirmada. |

## Pendências

- Dados (Alisson, Arthur e Gabriel) faz três cópias independentes da transformação Silver -> Gold, todas contra este contrato; as três são comparadas entre si antes de definir a Gold que será exportada.
- Período base: decidido manter qualquer par de períodos em gold_receita_decomposicao. Falta alinhar docs/arquitetura.md e docs/planejamento.md, que ainda falam em primeiros e últimos 12 meses e em votação.
- Tabelas da UC 360 (DECIDIDO, DEC-027): gold_interrupcoes_uc, gold_atendimentos_uc e gold_medidor_uc com colunas e chave, e gold_inspecoes_uc nova.
- Precisão numérica (energy_kwh, money) e normalização de município/bairro dependem da Silver.
- Titular na UC 360 (DECIDIDO, DEC-023): a Gold traz só titular_mascarado (iniciais) e documento_mascarado (3 últimos dígitos), ambos sensitive. Não há cod_cliente: a origem não tem código de cliente e, no dataset, cada titular tem uma UC só, exceto um documento de preenchimento repetido em um grupo de UCs cadastradas sem nenhum medidor (verificado: o grupo é exatamente o das UCs sem medidor, e o documento não é nulo).
- DEC-004: a Gold agregada não vai ao repositório público (a confirmar com a organização).
- classe x subgrupo (DECIDIDO: opção B, DEC-023): o glossário do case chama de 'classe de consumo' os grupos B1, B2, B3 e A4, e o B3 junta comercial e poder público; a diretoria pergunta por 'receita comercial' e 'volume residencial', e a Silver traz as duas informações (classe com 5 nomes e subgrupo_tarifario B1/B2/B3/A4, com cada classe em um só subgrupo). Opção A: classe passa a ter os 5 nomes e subgrupo guarda B1/B2/B3/A4. Opção B: classe continua B1/B2/B3/A4, como no case, e entra uma coluna nova com os 5 nomes. A opção A muda o domínio de classe, que hoje é usado pelo backend (teste do contrato) e pela camada semântica do agente (regra 'classe tem exatamente B1, B2, B3 e A4' e exemplos); a opção B só acrescenta coluna.
- receita (A CONFIRMAR APÓS A RECONCILIAÇÃO): receita_energia é a base provisória do PVM e da tarifa_media (DEC-023). Teste declarado: medir qual definição (com ou sem tributos) reproduz a variação citada pela diretoria e registrar o resultado como hipótese testada, sem ajustar números. Confirmar com o diagnóstico do PR #19 qual coluna foi usada para reproduzir a variação.
- kwh_faturado x consumo_kwh (VALIDADO, DEC-023): a fatura não tem kWh, e a energia faturada vem do consumo_kwh das leituras. O case diz que a energia da GD é abatida do consumo faturado. Teste: para as UCs com GD, a queda do consumo médio depois da conexão (até 12 meses de cada lado, mínimo 6) dividida pela energia injetada média mensal fica em torno de 1 (mediana próxima de 1, todas dentro de 0,7 a 1,3), então o consumo da leitura já é líquido de GD e não precisa de correção.
- Regra de kwh_faturado (VALIDADA contra a fatura, DEC-023): troca de medidor -> leitura_atual; consumo negativo sem troca (sinal invertido) -> valor absoluto; demais -> consumo_kwh. Teste: o kWh implícito da fatura (valor_energia ÷ tarifa mediana do subgrupo na competência, calculada só com leituras limpas) reproduz kwh_faturado dentro de 2% em todos os grupos sinalizados. Os dois grupos de leitura negativa são exclusivos e completos: todas as leituras sinalizadas pelo notebook de Silver são negativas, e cada uma cai em exatamente uma regra.
- Efeito bandeira e efeito GD (DECIDIDO, DEC-023): efeito_preco passa a ser efeito_tarifa + efeito_bandeira, e possui_gd entra no grão de gold_receita_decomposicao, de modo que o efeito GD é o efeito volume das linhas com possui_gd = true. Método (DECIDIDO, DEC-029): no dado, a bandeira é um acréscimo fixo por kWh, igual em todas as classes; efeito_tarifa usa a receita sem o acréscimo, e efeito_bandeira a variação do acréscimo. As parcelas fecham com a variação total por construção (conferido por trava).
- KPIs por recorte (DECIDIDO, DEC-023): gold_kpis_segmento_mensal guarda componentes somáveis por mês, município, bairro, classe e geração própria (possui_gd), para o filtro da diretoria, do portal e do agente; qualquer período é a soma das competências escolhidas. gold_kpis_mensais continua como total da empresa, e as duas são conferidas entre si. Os componentes de atendimento (n_chamados, soma_notas, n_notas) saem da Silver de atendimentos, que já existe, e contam o chamado pelo mês de abertura.
- possui_gd por competência (DECIDIDO, DEC-023): em gold_kpis_segmento_mensal, a UC conta como com GD a partir do mês da conexão. Em gold_receita_decomposicao, possui_gd é o estado no último mês do período atual e vale para a UC nos dois períodos, base e atual: a UC que conectou a GD entre eles fica no grupo com GD dos dois lados, para o PVM comparar as mesmas UCs e o efeito GD ser a queda de volume delas. Por isso a soma de possui_gd = true no período base da decomposição pode diferir da tabela mensal.
- Faturas de UCs fora do cadastro (flag_uc_orfa): ficam fora do fato por UC (não há UC para ligar), mas não são descartadas: entram em gold_reconciliacao_faturamento, que também traz a ponte da energia (DEC-023). Limite: sem cadastro, não dá para cruzá-las com município, bairro ou classe.
- Pares da decomposição (DECIDIDO, DEC-028): a Gold grava todos os pares de mesmos meses em anos diferentes; pares de trechos diferentes ficam para o backend calcular na hora, se o portal precisar (gravar todos passaria de 1 bilhão de linhas).
- Ocorrências registradas antes da ligação da UC (DECIDIDO, DEC-030): ficam fora da Gold (OCO-04).
