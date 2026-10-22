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
