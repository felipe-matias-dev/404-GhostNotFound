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
    consumo_medio_kwh_12m
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
    bandeira
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
    n_notas
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
