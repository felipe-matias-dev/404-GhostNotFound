"""As métricas da tela de Receita que o redator de insights narra.

O JSON sai dos números que a Gold já calculou, somados como a tela soma (DEC-035). O LLM só
narra: o agente descarta o texto se algum número dele não for exatamente um valor deste JSON
(DEC-019). Por isso os valores já vêm arredondados como a tela os mostra, em R$ com 2 casas e
em % com 1: com os 15 dígitos de um float, "−3,9%" no texto nunca bateria com −3.912621359.
"""

import re
from collections.abc import Sequence
from decimal import ROUND_HALF_UP, Decimal

from venergy_api.schemas import DecomposicaoFiltroSchema, DecomposicaoLinhaSchema
from venergy_api.variacao import variacao_pct

MAX_QUEDAS = 3
MIN_SEGMENTOS_PARA_CONTAR = 3

_PLURAL_DO_NIVEL = {"municipio": "municípios", "bairro": "bairros", "classe": "classes"}
# Palavras que o texto do modelo não pode usar: jargão da ponte, ou o que já saiu errado na
# medição ("simultaneamente" afirma mais do que a soma de quantidade e perfil garante).
_TERMOS_PROIBIDOS = re.compile(
    r"\b(faturamento|simultaneamente|desempenho|segmentos?|efeitos?|mix|volume|recorte)\b|·",
    re.IGNORECASE,
)
# Folga para o modelo reescrever a leitura, sem espaço para ele acrescentar outra conclusão.
_FOLGA_DO_TEXTO = 40
# Sentido de cada afirmação, na ordem do texto. "Ganho" fica de fora: é o nome do efeito do preço.
_SENTIDO = re.compile(
    r"\b(?:(?P<alta>cresc\w*|sub\w*|alta|aument\w*)"
    r"|(?P<queda>recu\w*|ca[ií]\w*|qued\w*|perd\w*|redu\w*|derrub\w*))\b",
    re.IGNORECASE,
)
_NUMERO = re.compile(r"\d+(?:\.\d{3})*(?:,\d+)?")

_CENTAVOS = Decimal("0.01")


def _reais(valor: Decimal) -> float:
    return float(valor.quantize(_CENTAVOS, rounding=ROUND_HALF_UP))


def _pct(base: Decimal, variacao: Decimal) -> float | None:
    percentual = variacao_pct(base, base + variacao)
    return None if percentual is None else round(percentual, 1)


def _recorte(filtro: DecomposicaoFiltroSchema) -> str:
    partes = [filtro.municipio or "todos os municípios"]
    if filtro.bairro:
        partes.append(filtro.bairro)
    if filtro.classe:
        partes.append(f"classe {filtro.classe}")
    return " · ".join(partes)


def _queda(linha: DecomposicaoLinhaSchema) -> dict[str, object]:
    queda: dict[str, object] = {
        "segmento": linha.segmento,
        "variacao_receita": _reais(linha.variacao_receita),
    }
    percentual = _pct(linha.receita_base, linha.variacao_receita)
    # Sem receita base (segmento novo) não existe percentual (DEC-035).
    if percentual is not None:
        queda["variacao_pct"] = percentual
    return queda


def filtro_acima(filtro: DecomposicaoFiltroSchema) -> DecomposicaoFiltroSchema | None:
    """O recorte que contém este e os seus vizinhos, ou None se já é a empresa inteira."""
    if filtro.bairro:
        return filtro.model_copy(update={"bairro": None})
    if filtro.municipio:
        return filtro.model_copy(update={"municipio": None})
    if filtro.classe:
        return filtro.model_copy(update={"classe": None})
    return None


def _nome_acima(filtro: DecomposicaoFiltroSchema) -> tuple[str, str]:
    """Como o texto chama o recorte de cima: sujeito ("a empresa") e lugar ("na empresa")."""
    if filtro.bairro:
        nome, lugar = filtro.municipio or "", f"em {filtro.municipio}"
    else:
        nome, lugar = "a empresa", "na empresa"
    if filtro.classe and (filtro.bairro or filtro.municipio):
        return f"{nome} (classe {filtro.classe})", f"{lugar} (classe {filtro.classe})"
    return nome, lugar


def _numero_br(valor: object, casas: int = 1) -> str:
    return f"{valor:,.{casas}f}".replace(",", "#").replace(".", ",").replace("#", ".")


def _variou(pct: float) -> str:
    if pct == 0:
        return "ficou estável"
    return f"{'cresceu' if pct > 0 else 'recuou'} {_numero_br(abs(pct))}%"


def _leitura_principal(
    metricas: dict[str, object], filtro: DecomposicaoFiltroSchema
) -> tuple[str, str]:
    """A leitura mais forte do recorte e o texto dela, que a tela não resume (DEC-066).

    A regra é daqui, e não do LLM: ele só redige. Se o texto dele não servir, este é o que a
    tela mostra.
    """
    n = metricas["n_segmentos"]
    plural = _PLURAL_DO_NIVEL[metricas["nivel_das_linhas"]]
    todos, dos, artigo = (
        ("todas as", "das", "as") if plural == "classes" else ("todos os", "dos", "os")
    )
    contar = n >= MIN_SEGMENTOS_PARA_CONTAR
    pct = metricas.get("variacao_receita_pct")
    pct_acima = metricas.get("variacao_acima_pct")
    so_preco = metricas["n_segmentos_alta_so_por_preco"]
    quantidade = metricas["n_segmentos_quantidade_em_queda"]
    bandeira = metricas.get("bandeira_no_preco_pct")
    nome_acima, lugar_acima = _nome_acima(filtro)

    if metricas.get("unico_em_queda") and pct is not None and pct_acima is not None:
        nome = filtro.bairro or filtro.municipio
        tipo_do_nome = "bairro" if filtro.bairro else "município"
        return "unico_em_queda", (
            f"{nome} foi o único {tipo_do_nome} a perder receita {lugar_acima}: "
            f"{_variou(pct)}, enquanto {nome_acima} {_variou(pct_acima)}."
        )
    if contar and metricas["variacao_receita"] > 0 and so_preco * 2 >= n:
        quantos = f"{todos} {n}" if so_preco == n else f"{so_preco} {dos} {n}"
        return "alta_depende_do_preco", (
            f"Em {quantos} {plural}, a receita só subiu por causa do preço: sem ele, a quantidade "
            "vendida e o perfil de consumo somados a teriam derrubado."
        )
    if bandeira is not None and bandeira >= 50:
        return "bandeira_pesa", (
            f"{_numero_br(bandeira)}% do ganho de preço veio da bandeira, não da tarifa."
        )
    if contar and quantidade == n:
        return "quantidade_geral", (
            f"A quantidade vendida caiu em {todos} {n} {plural}: a queda é geral, não localizada."
        )
    participacao = metricas.get("maior_queda_participacao_pct")
    if metricas["n_segmentos_em_queda"] >= 2 and participacao >= 50:
        return "quedas_concentradas", (
            f"{metricas['maiores_quedas'][0]['segmento']} responde por "
            f"{_numero_br(participacao)}% da soma das quedas de receita entre {artigo} {plural}."
        )
    if pct is not None and pct_acima is not None:
        nome = filtro.bairro or filtro.municipio
        lugar = f"Em {nome}" if nome else f"Na classe {filtro.classe}"
        return "comparacao_acima", (
            f"{lugar}, a receita {_variou(pct)}, enquanto {nome_acima} {_variou(pct_acima)}."
        )
    if metricas["fatores_a_favor"] or metricas["fatores_contra"]:
        artigo_do_fator = "a" if metricas["maior_fator"] == "quantidade vendida" else "o"
        return "maior_fator", f"O que mais pesou foi {artigo_do_fator} {metricas['maior_fator']}."
    return "sem_variacao", "A receita não variou entre os dois períodos."


def _numeros(texto: str) -> set[Decimal]:
    return {Decimal(numero.replace(".", "").replace(",", ".")) for numero in _NUMERO.findall(texto)}


def _sentidos(texto: str) -> list[str | None]:
    return [encontrado.lastgroup for encontrado in _SENTIDO.finditer(texto)]


def texto_aceito(texto: str, metricas: dict[str, object]) -> bool:
    """Se o texto do modelo diz a leitura escolhida: mesmos números e sentidos, sem jargão.

    Sinônimo em outra ordem também é recusado: o custo é mostrar o texto da regra, que diz o
    mesmo, e nunca uma alta trocada por uma queda.
    """
    leitura = str(metricas["leitura_texto"])
    if _TERMOS_PROIBIDOS.search(texto) or len(texto) > len(leitura) + _FOLGA_DO_TEXTO:
        return False
    return _numeros(texto) == _numeros(leitura) and _sentidos(texto) == _sentidos(leitura)


def metricas_da_receita(
    filtro: DecomposicaoFiltroSchema,
    linhas: Sequence[DecomposicaoLinhaSchema],
    linhas_acima: Sequence[DecomposicaoLinhaSchema] = (),
) -> dict[str, object] | None:
    """O JSON de métricas do recorte, ou None se não há nenhum segmento para narrar.

    `linhas_acima` são as do recorte de cima (`filtro_acima`), que dão a comparação.
    """
    if not linhas:
        return None

    receita_base = sum((linha.receita_base for linha in linhas), Decimal(0))
    tarifa = sum((linha.efeito_tarifa for linha in linhas), Decimal(0))
    bandeira = sum((linha.efeito_bandeira for linha in linhas), Decimal(0))
    volume = sum((linha.efeito_volume for linha in linhas), Decimal(0))
    mix = sum((linha.efeito_mix for linha in linhas), Decimal(0))
    # A receita atual da ponte é a base mais os efeitos, e não a soma de receita_atual das
    # linhas: cada linha fecha só dentro da tolerância do contrato, e a tela mostra assim.
    variacao = tarifa + bandeira + volume + mix

    metricas: dict[str, object] = {
        "periodo_base": filtro.periodo_base,
        "periodo_atual": filtro.periodo_atual,
        "recorte": _recorte(filtro),
        "nivel_das_linhas": linhas[0].nivel,
        "n_segmentos": len(linhas),
        "receita_base": _reais(receita_base),
        "receita_atual": _reais(receita_base + variacao),
        "variacao_receita": _reais(variacao),
        "efeito_preco": _reais(tarifa + bandeira),
        "efeito_tarifa": _reais(tarifa),
        "efeito_bandeira": _reais(bandeira),
        "efeito_volume": _reais(volume),
        "efeito_mix": _reais(mix),
    }
    percentual = _pct(receita_base, variacao)
    if percentual is not None:
        metricas["variacao_receita_pct"] = percentual

    # O LLM lê o que ajudou e o que pesou contra sem fazer conta. Cada efeito fica no próprio
    # sentido: somar volume e mix, ou dar % da base, levou o texto a afirmar o que não houve
    # ("o preço subiu 12,3%", "a quantidade pesou contra" com volume em alta) (DEC-066).
    efeitos = (
        ("preço", tarifa + bandeira),
        ("quantidade vendida", volume),
        ("perfil de consumo", mix),
    )
    metricas["fatores_a_favor"] = [nome for nome, efeito in efeitos if efeito > 0]
    metricas["fatores_contra"] = [nome for nome, efeito in efeitos if efeito < 0]
    metricas["maior_fator"] = max(efeitos, key=lambda par: abs(par[1]))[0]

    # O que a tela não resume: a ponte mostra o total, e estas leituras dizem como ele se
    # distribui entre os segmentos e de que é feito o ganho de preço (DEC-066).
    metricas["n_segmentos_quantidade_em_queda"] = sum(
        1 for linha in linhas if linha.efeito_volume < 0
    )
    metricas["n_segmentos_alta_so_por_preco"] = sum(
        1
        for linha in linhas
        if linha.variacao_receita > 0 and linha.efeito_volume + linha.efeito_mix < 0
    )
    # Só é "parte do preço" com as duas parcelas a favor: com sinais opostos passaria de 100%.
    if tarifa >= 0 and bandeira > 0:
        metricas["bandeira_no_preco_pct"] = round(float(bandeira / (tarifa + bandeira) * 100), 1)

    quedas = sorted(
        (linha for linha in linhas if linha.variacao_receita < 0),
        key=lambda linha: (linha.variacao_receita, linha.segmento),
    )
    metricas["maiores_quedas"] = [_queda(linha) for linha in quedas[:MAX_QUEDAS]]
    metricas["n_segmentos_em_queda"] = len(quedas)
    if quedas:
        total_das_quedas = sum((linha.variacao_receita for linha in quedas), Decimal(0))
        metricas["maior_queda_participacao_pct"] = round(
            float(quedas[0].variacao_receita / total_das_quedas * 100), 1
        )

    if linhas_acima:
        base_acima = sum((linha.receita_base for linha in linhas_acima), Decimal(0))
        variacao_acima = sum(
            (
                linha.efeito_tarifa + linha.efeito_bandeira + linha.efeito_volume + linha.efeito_mix
                for linha in linhas_acima
            ),
            Decimal(0),
        )
        pct_acima = _pct(base_acima, variacao_acima)
        if pct_acima is not None:
            metricas["variacao_acima_pct"] = pct_acima
        vizinhos_em_queda = [linha.segmento for linha in linhas_acima if linha.variacao_receita < 0]
        metricas["n_vizinhos"] = len(linhas_acima)
        metricas["n_vizinhos_em_queda"] = len(vizinhos_em_queda)
        # Filtro só de classe: as linhas de cima são municípios, e a classe não é uma delas.
        nome = filtro.bairro or filtro.municipio
        metricas["unico_em_queda"] = len(
            linhas_acima
        ) >= MIN_SEGMENTOS_PARA_CONTAR and vizinhos_em_queda == [nome]

    metricas["leitura_principal"], metricas["leitura_texto"] = _leitura_principal(metricas, filtro)
    return metricas
