"""As métricas da tela de Perdas que o redator de insights narra.

A tela mostra os indicadores da fila, o mapa e a lista de suspeitas. O que ela não diz é para
onde mandar a equipe: quanto da energia a recuperar se concentra em poucos lugares, se as
inspeções do portal acertam mais ou menos que o histórico e quanto da fila está parado.

Só números agregados vão ao modelo, nunca uma UC: a fila é uma lista de suspeitos e fica fora do
agente (DEC-022). O insight não lista nem cita suspeitas, só os totais que a tela já mostra.
"""

import re
from collections.abc import Sequence
from decimal import Decimal

from venergy_api.insights import com_candidatas, numero_br
from venergy_api.insights import motivo_da_recusa as recusar
from venergy_api.schemas import IndicadoresPerdasSchema, RecorteFiltroSchema, RecortesFilaSchema

MAX_LUGARES = 3
# Com menos lugares que isso, "os 3 maiores" seria quase o recorte inteiro.
MIN_LUGARES_PARA_CONCENTRAR = 5
# Menos vistorias decididas que isso dariam uma taxa de acaso.
MIN_VISTORIAS_PARA_TAXA = 5

_PLURAL = {"municipio": "municípios", "bairro": "bairros"}
_TERMOS_PROIBIDOS = re.compile(
    r"\b(simultaneamente|desempenho|segmentos?|recorte|suspeitos?|fraudadores?)\b|·|_",
    re.IGNORECASE,
)


def _recorte(filtro: RecorteFiltroSchema) -> str:
    partes = [filtro.municipio or "todos os municípios"]
    if filtro.bairro:
        partes.append(filtro.bairro)
    if filtro.classe:
        partes.append(f"classe {filtro.classe}")
    return ", ".join(partes)


def _lista(nomes: Sequence[str]) -> str:
    return nomes[0] if len(nomes) == 1 else f"{', '.join(nomes[:-1])} e {nomes[-1]}"


def motivo_da_recusa(
    texto: str, metricas: dict[str, object], escolhidas: Sequence[str] = ()
) -> str | None:
    """Por que o texto da IA não diz as leituras que ela escolheu, ou None se diz."""
    return recusar(texto, metricas, escolhidas, _TERMOS_PROIBIDOS)


def texto_aceito(texto: str, metricas: dict[str, object], escolhidas: Sequence[str] = ()) -> bool:
    return motivo_da_recusa(texto, metricas, escolhidas) is None


def metricas_de_perdas(
    filtro: RecorteFiltroSchema,
    indicadores: IndicadoresPerdasSchema,
    recortes: RecortesFilaSchema,
) -> dict[str, object] | None:
    """O JSON de métricas da tela de Perdas, ou None se a fila do recorte está vazia."""
    if indicadores.suspeitas == 0:
        return None
    metricas: dict[str, object] = {
        "recorte": _recorte(filtro),
        "suspeitas": indicadores.suspeitas,
        "suspeitas_sem_ordem": indicadores.suspeitas_sem_ordem_ativa,
    }
    leituras: list[tuple[str, str]] = []
    nomes: dict[str, list[str]] = {}

    lugares = [r for r in recortes.recortes if r.kwh_recuperavel_est]
    total = sum((r.kwh_recuperavel_est for r in lugares), Decimal(0))
    if len(lugares) >= MIN_LUGARES_PARA_CONCENTRAR and total > 0:
        maiores = lugares[:MAX_LUGARES]
        participacao = round(
            float(sum((r.kwh_recuperavel_est for r in maiores), Decimal(0)) / total * 100), 1
        )
        plural = _PLURAL[recortes.nivel]
        metricas |= {
            "n_lugares": len(lugares),
            "n_maiores": len(maiores),
            "maiores_lugares": [r.segmento for r in maiores],
            "participacao_dos_maiores_pct": participacao,
        }
        nomes["concentracao"] = [r.segmento for r in maiores]
        # Sem "os 3 … de 13": os nomes já dizem quais e quantos são, e a IA tirava as contagens
        # ao citá-los, o que a conferência recusava.
        leituras.append(
            (
                "concentracao",
                f"{_lista([r.segmento for r in maiores])}, os {plural} com mais energia a "
                f"recuperar, concentram {numero_br(participacao)}% do kWh estimado da fila.",
            )
        )

    portal, gold = indicadores.portal, indicadores.gold
    decididas = portal.irregulares + portal.regulares
    if (
        decididas >= MIN_VISTORIAS_PARA_TAXA
        and portal.taxa_irregularidade is not None
        and gold.taxa_irregularidade is not None
    ):
        taxa = round(portal.taxa_irregularidade * 100, 1)
        historico = round(gold.taxa_irregularidade * 100, 1)
        metricas |= {
            "vistorias_do_portal": decididas,
            "taxa_irregularidade_portal_pct": taxa,
            "taxa_irregularidade_historico_pct": historico,
        }
        if taxa == historico:
            comparacao = f"igual aos {numero_br(historico)}% do histórico"
        else:
            lado = "acima" if taxa > historico else "abaixo"
            comparacao = f"{lado} dos {numero_br(historico)}% do histórico"
        leituras.append(
            (
                "acerto_das_inspecoes",
                f"As vistorias do portal confirmaram irregularidade em {numero_br(taxa)}% "
                f"dos casos, {comparacao}.",
            )
        )

    if indicadores.suspeitas_sem_ordem_ativa and indicadores.kwh_recuperavel_est_sem_ordem:
        kwh = int(indicadores.kwh_recuperavel_est_sem_ordem)
        metricas["kwh_mes_sem_ordem"] = kwh
        leituras.append(
            (
                "fila_parada",
                f"{numero_br(indicadores.suspeitas_sem_ordem_ativa, 0)} das "
                f"{numero_br(indicadores.suspeitas, 0)} suspeitas ainda não têm ordem de "
                f"inspeção; juntas, estimam {numero_br(kwh, 0)} kWh por mês.",
            )
        )

    if not leituras:
        return None
    return com_candidatas(leituras, metricas, nomes)
