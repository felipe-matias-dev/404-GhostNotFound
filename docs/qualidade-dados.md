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