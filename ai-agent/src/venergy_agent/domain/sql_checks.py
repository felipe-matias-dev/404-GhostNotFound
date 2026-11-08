import re

AVERAGE_OF_SATISFACTION = re.compile(r"\bavg\s*\(\s*(?:\w+\.)?satisfacao_media\s*\)", re.IGNORECASE)
AVERAGE_OF_TARIFF = re.compile(r"\bavg\s*\(\s*(?:\w+\.)?tarifa_media\s*\)", re.IGNORECASE)
SUM_OF_INDEX = re.compile(r"\bsum\s*\(\s*(?:\w+\.)?(dec|fec)\s*\)", re.IGNORECASE)
FEEDER_VIEW = "sem_continuidade_alimentador_mensal"
DECOMPOSITION_VIEW = "sem_receita_decomposicao"
SEGMENT_VIEW = "sem_kpis_segmento_mensal"
AGGREGATE = re.compile(r"\b(?:sum|count|avg|min|max)\s*\(|\bgroup\s+by\b", re.IGNORECASE)
EFFECT = re.compile(r"(?P<before>\bsum\s*\(\s*)?(?:\w+\.)?\befeito_\w+", re.IGNORECASE)
PER_FEEDER = re.compile(r"\bgroup\s+by\b[^;]*?\bcod_alimentador\b", re.IGNORECASE)
SINGLE_FEEDER = re.compile(r"\bcod_alimentador\s*=\s*'", re.IGNORECASE)

SATISFACTION_FORMULA = (
    "Satisfação de vários meses não é a média de satisfacao_media: use "
    "sum(soma_notas) / NULLIF(sum(n_notas), 0) em sem_kpis_segmento_mensal; por canal ou "
    "assunto, avg(nota_satisfacao) de sem_atendimentos_uc."
)
TARIFF_FORMULA = (
    "Tarifa média de um grupo não é a média de tarifa_media: use "
    "sum(receita_energia) / NULLIF(sum(kwh_faturado), 0)."
)
GROUP_INDEX_FORMULA = (
    "DEC ou FEC de mais de um alimentador não é a soma dos índices: some os componentes, "
    "DEC = sum(horas_interrompidas) / NULLIF(sum(n_uc), 0) e "
    "FEC = 1.0 * sum(n_interrupcoes) / NULLIF(sum(n_uc), 0); num período de vários meses, "
    "divida pela média mensal de UCs (sum(n_uc) / 12.0 num ano)."
)

DECOMPOSITION_FORMULA = (
    "sem_receita_decomposicao tem uma linha por município, bairro, classe e GD: some os efeitos "
    "e as receitas sobre o recorte pedido, sum(efeito_preco), sum(receita_base) e assim por "
    "diante, com o filtro do recorte quando a pergunta citar um."
)

SEGMENT_FORMULA = (
    "sem_kpis_segmento_mensal tem uma linha por município, bairro, classe, alimentador, medidor "
    "e GD em cada mês: some os componentes sobre o recorte pedido (sum(n_faturas), "
    "sum(receita_faturada)), ou agrupe pela coluna que a pergunta pede."
)


def calculation_problem(sql: str) -> str | None:
    if AVERAGE_OF_SATISFACTION.search(sql):
        return SATISFACTION_FORMULA
    if AVERAGE_OF_TARIFF.search(sql):
        return TARIFF_FORMULA
    if (
        FEEDER_VIEW in sql
        and SUM_OF_INDEX.search(sql)
        and not SINGLE_FEEDER.search(sql)
        and not PER_FEEDER.search(sql)
    ):
        return GROUP_INDEX_FORMULA
    if SEGMENT_VIEW in sql and not AGGREGATE.search(sql):
        return SEGMENT_FORMULA
    effects = list(EFFECT.finditer(sql))
    if DECOMPOSITION_VIEW in sql and effects and not any(m["before"] for m in effects):
        return DECOMPOSITION_FORMULA
    return None
