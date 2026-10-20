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
| UC-08 | `cep` | Ausente | 161 nulos + 891 `NULL`/`N/A`/`-`/vazio | Flag: manter a UC com CEP nulo (descartar removeria as faturas dela da receita) |
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


