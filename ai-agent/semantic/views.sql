-- Gerado por venergy_agent.infrastructure.views_sql a partir de
-- semantic/semantic_layer.yaml
-- e contracts/gold_schema.yaml. Não edite à mão.
-- Regenerar: cd ai-agent && uv run python -m venergy_agent.infrastructure.views_sql

CREATE OR REPLACE VIEW gold.sem_uc AS
SELECT
    cod_uc,
    municipio,
    bairro,
    classe,
    classe_cadastro,
    cod_alimentador,
    possui_gd,
    consumo_medio_kwh_12m,
    data_ligacao,
    data_conexao_gd,
    modalidade_gd,
    energia_injetada_kwh_mes,
    potencia_kwp
FROM gold.gold_dim_uc;

CREATE OR REPLACE VIEW gold.sem_faturamento_mensal AS
SELECT
    cod_uc,
    competencia,
    kwh_faturado,
    receita_faturada,
    receita_energia,
    tributos,
    receita_arrecadada,
    tarifa_media,
    bandeira,
    receita_bandeira,
    data_vencimento,
    data_pagamento,
    status_pagamento,
    dias_em_atraso,
    tipo_leitura,
    tipo_medidor,
    dias_faturados
FROM gold.gold_fato_faturamento_mensal;

CREATE OR REPLACE VIEW gold.sem_continuidade_alimentador_mensal AS
SELECT
    cod_alimentador,
    competencia,
    dec,
    fec,
    n_uc,
    n_interrupcoes,
    horas_interrompidas
FROM gold.gold_continuidade_alimentador_mensal;

CREATE OR REPLACE VIEW gold.sem_kpis_mensais AS
SELECT
    competencia,
    kwh_faturado,
    receita_faturada,
    receita_energia,
    dec,
    fec,
    n_chamados,
    satisfacao_media
FROM gold.gold_kpis_mensais;

CREATE OR REPLACE VIEW gold.sem_kpis_segmento_mensal AS
SELECT
    competencia,
    municipio,
    bairro,
    classe_cadastro,
    classe,
    cod_alimentador,
    tipo_medidor,
    possui_gd,
    n_uc,
    kwh_faturado,
    receita_faturada,
    receita_energia,
    tributos,
    receita_arrecadada,
    horas_interrompidas,
    n_interrupcoes,
    n_chamados,
    soma_notas,
    n_notas,
    receita_bandeira,
    n_faturas,
    n_faturas_nao_pagas,
    valor_nao_pago,
    n_faturas_pagas_com_atraso,
    soma_dias_em_atraso,
    n_leituras,
    n_leituras_estimadas
FROM gold.gold_kpis_segmento_mensal;

CREATE OR REPLACE VIEW gold.sem_receita_decomposicao AS
SELECT
    periodo_base,
    periodo_atual,
    municipio,
    bairro,
    classe,
    possui_gd,
    receita_base,
    receita_atual,
    efeito_preco,
    efeito_tarifa,
    efeito_bandeira,
    efeito_volume,
    efeito_mix
FROM gold.gold_receita_decomposicao;

CREATE OR REPLACE VIEW gold.sem_interrupcoes_uc AS
SELECT
    cod_ocorrencia,
    cod_uc,
    competencia,
    data_abertura,
    data_encerramento,
    duracao_horas,
    tipo,
    causa
FROM gold.gold_interrupcoes_uc;

CREATE OR REPLACE VIEW gold.sem_atendimentos_uc AS
SELECT
    protocolo,
    cod_uc,
    competencia,
    data_abertura,
    data_fechamento,
    canal,
    assunto,
    subassunto,
    nota_satisfacao
FROM gold.gold_atendimentos_uc;

CREATE OR REPLACE VIEW gold.sem_medidor_uc AS
SELECT
    cod_uc,
    cod_medidor,
    tipo_medidor,
    modelo,
    data_instalacao,
    idade_anos,
    n_trocas,
    data_ultima_troca
FROM gold.gold_medidor_uc;
