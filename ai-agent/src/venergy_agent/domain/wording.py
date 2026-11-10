import re

TECHNICAL_NAME = re.compile(r"\b[a-zA-Z]+_\w+")
VIEW_REFERENCE = re.compile(r"\b(na|da|a)\s+view\s+(sem_\w+)", re.IGNORECASE)
VIEW_NAMES = {
    "sem_uc": "cadastro de UCs",
    "sem_faturamento_mensal": "faturamento mensal",
    "sem_continuidade_alimentador_mensal": "continuidade por alimentador",
    "sem_kpis_mensais": "totais mensais",
    "sem_kpis_segmento_mensal": "totais por recorte",
    "sem_interrupcoes_uc": "interrupções por UC",
    "sem_atendimentos_uc": "atendimentos por UC",
    "sem_medidor_uc": "medidores",
    "sem_receita_decomposicao": "decomposição da receita",
}
VIEW_ARTICLES = {"na": "nos", "da": "dos", "a": "os"}
ACCENTED = {
    "kwp": "kWp",
    "uc": "UC",
    "ucs": "UCs",
    "gd": "GD",
    "cod": "código",
    "ultima": "última",
    "potencia": "potência",
    "ocorrencia": "ocorrência",
    "nao": "não",
    "ligacao": "ligação",
    "instalacao": "instalação",
    "duracao": "duração",
    "conexao": "conexão",
    "arrecadacao": "arrecadação",
    "ate": "até",
    "pct": "em %",
    "codigo": "código",
    "competencia": "competência",
    "competencias": "competências",
    "decomposicao": "decomposição",
    "eletronico": "eletrônico",
    "emissao": "emissão",
    "inicio": "início",
    "interrupcao": "interrupção",
    "kwh": "kWh",
    "interrupcoes": "interrupções",
    "media": "média",
    "medio": "médio",
    "medicao": "medição",
    "mes": "mês",
    "municipio": "município",
    "numero": "número",
    "participacao": "participação",
    "periodo": "período",
    "preco": "preço",
    "satisfacao": "satisfação",
    "situacao": "situação",
    "ultimo": "último",
    "ultimos": "últimos",
    "unico": "único",
    "variacao": "variação",
}


MONTHS_SUFFIX = re.compile(r"(\d+)m")
PERCENT_THRESHOLD = re.compile(r"(?<![^_])(\d+)_?pct(?![^_])")
MACHINE_DECIMAL = re.compile(r"(?<![\d.,])(\d+)\.(\d+)(?![\d,]|\.\d)")
COLUMN_LABELS = {
    "classe_cadastro": "classe do cadastro",
    "cod_ocorrencia": "código da ocorrência",
    "data_conexao_gd": "data de conexão da GD",
    "duracao_horas": "duração em horas",
    "energia_injetada_kwh_mes": "energia injetada por mês",
    "possui_gd": "tem geração distribuída",
    "consumo_medio_kwh_12m": "consumo médio mensal dos últimos 12 meses",
    "cod_alimentador": "alimentador",
    "cod_uc": "código da UC",
    "dec": "DEC",
    "fec": "FEC",
    "kwh_faturado": "energia faturada",
    "n_uc": "UCs",
    "receita_atual": "receita do período atual",
    "receita_base": "receita do período base",
    "receita_energia": "receita de energia",
}


def label(column: str) -> str:
    if column in VIEW_NAMES:
        return VIEW_NAMES[column]
    if column in COLUMN_LABELS:
        return COLUMN_LABELS[column]
    words = PERCENT_THRESHOLD.sub(r"\1%", column).split("_")
    if words[0] == "n" and len(words) > 1:
        words = ["número", "de", *words[1:]]
    return " ".join(_word(word) for word in words)


def _word(word: str) -> str:
    if months := MONTHS_SUFFIX.fullmatch(word):
        return f"{months.group(1)} meses"
    return ACCENTED.get(word, word)


def plain_words(text: str) -> str:
    text = VIEW_REFERENCE.sub(
        lambda match: f"{VIEW_ARTICLES[match.group(1).lower()]} dados de {label(match.group(2))}",
        text,
    )
    text = TECHNICAL_NAME.sub(lambda name: label(name.group()), text)
    return MACHINE_DECIMAL.sub(_pt_br_decimal, text)


def _pt_br_decimal(match: re.Match[str]) -> str:
    whole, fraction = match.group(1), match.group(2).rstrip("0")
    return f"{whole},{fraction}" if fraction else whole
