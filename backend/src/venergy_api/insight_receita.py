"""As métricas da tela de Receita que o redator de insights narra.

O JSON sai dos números que a Gold já calculou, somados como a tela soma (DEC-035). O LLM só
narra: o agente descarta o texto se algum número dele não for exatamente um valor deste JSON
(DEC-019). Por isso os valores já vêm arredondados como a tela os mostra, em R$ com 2 casas e
em % com 1: com os 15 dígitos de um float, "−3,9%" no texto nunca bateria com −3.912621359.
"""

from collections.abc import Sequence
from decimal import ROUND_HALF_UP, Decimal

from venergy_api.schemas import DecomposicaoFiltroSchema, DecomposicaoLinhaSchema
from venergy_api.variacao import variacao_pct

MAX_QUEDAS = 3

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


def metricas_da_receita(
    filtro: DecomposicaoFiltroSchema, linhas: Sequence[DecomposicaoLinhaSchema]
) -> dict[str, object] | None:
    """O JSON de métricas do recorte, ou None se não há nenhum segmento para narrar."""
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
    return metricas
