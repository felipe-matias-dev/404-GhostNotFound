"""As métricas da tela de Rede que o redator de insights narra.

A tabela ordena os alimentadores do pior para o melhor, um por linha. O que ela não diz é quanto
das interrupções se concentra nos piores, quantas vezes o pior passa da média do lugar e, com a
base, em quantos o índice subiu: é o que diz onde a manutenção preventiva rende mais.
"""

import math
import re
from collections.abc import Sequence

from venergy_api.insights import com_candidatas, numero_br, variou
from venergy_api.insights import motivo_da_recusa as recusar
from venergy_api.schemas import RankingContinuidadeSchema, RankingFiltroSchema

MIN_ALIMENTADORES_PARA_CONCENTRAR = 5
# Os piores são o décimo de cima da tabela, ao menos um.
FRACAO_DOS_PIORES = 0.1

# O componente que soma cada índice: horas de interrupção no DEC, interrupções no FEC.
_COMPONENTE = {"dec": "horas_interrompidas", "fec": "n_interrupcoes"}
_NOME_DO_COMPONENTE = {"dec": "das horas de interrupção", "fec": "das interrupções"}
_TERMOS_PROIBIDOS = re.compile(
    r"\b(simultaneamente|desempenho|segmentos?|recorte|componentes?)\b|·|_",
    re.IGNORECASE,
)


def _lugar(filtro: RankingFiltroSchema) -> str:
    lugar = f"em {filtro.bairro or filtro.municipio}" if filtro.municipio else "na empresa"
    return f"{lugar} (classe {filtro.classe})" if filtro.classe else lugar


def motivo_da_recusa(
    texto: str, metricas: dict[str, object], escolhidas: Sequence[str] = ()
) -> str | None:
    """Por que o texto da IA não diz as leituras que ela escolheu, ou None se diz."""
    return recusar(texto, metricas, escolhidas, _TERMOS_PROIBIDOS)


def texto_aceito(texto: str, metricas: dict[str, object], escolhidas: Sequence[str] = ()) -> bool:
    return motivo_da_recusa(texto, metricas, escolhidas) is None


def metricas_da_continuidade(
    filtro: RankingFiltroSchema, ranking: RankingContinuidadeSchema
) -> dict[str, object] | None:
    """O JSON de métricas do ranking da tela, ou None se não há alimentador com índice."""
    criterio = ranking.criterio
    indice = criterio.upper()
    linhas = [linha for linha in ranking.alimentadores if getattr(linha, criterio) is not None]
    if not linhas:
        return None

    lugar = _lugar(filtro)
    componente = _COMPONENTE[criterio]
    total = sum(getattr(linha, componente) for linha in linhas)
    uc_medio = sum(linha.n_uc_medio or 0 for linha in linhas)
    pior = linhas[0]
    metricas: dict[str, object] = {
        "periodo": f"{ranking.inicio}/{ranking.fim}",
        "criterio": indice,
        "lugar": lugar,
        "n_alimentadores": len(linhas),
        "pior_alimentador": pior.cod_alimentador,
        "indice_do_pior": round(getattr(pior, criterio), 2),
    }
    leituras: list[tuple[str, str]] = []

    if len(linhas) >= MIN_ALIMENTADORES_PARA_CONCENTRAR and total > 0:
        n_piores = max(1, math.ceil(len(linhas) * FRACAO_DOS_PIORES))
        dos_piores = sum(getattr(linha, componente) for linha in linhas[:n_piores])
        participacao = round(dos_piores / total * 100, 1)
        metricas |= {"n_piores": n_piores, "participacao_dos_piores_pct": participacao}
        quem = "O alimentador de pior" if n_piores == 1 else f"Os {n_piores} alimentadores de pior"
        concentra = "concentra" if n_piores == 1 else "concentram"
        leituras.append(
            (
                "concentracao",
                f"{quem} {indice} {lugar} {concentra} {numero_br(participacao)}% "
                f"{_NOME_DO_COMPONENTE[criterio]}, entre {len(linhas)} alimentadores.",
            )
        )

    # O índice do lugar soma os componentes e só então divide, como a tela (DEC-021).
    if len(linhas) >= 2 and uc_medio > 0 and total > 0:
        razao = round(getattr(pior, criterio) / (total / uc_medio), 1)
        metricas["vezes_o_indice_do_lugar"] = razao
        leituras.append(
            (
                "pior_alimentador",
                f"O {pior.cod_alimentador} tem o pior {indice} {lugar}: "
                f"{numero_br(razao)} vezes o {indice} do conjunto.",
            )
        )

    com_base = [
        (linha.cod_alimentador, pct)
        for linha in linhas
        if linha.variacao_pct is not None
        and (pct := getattr(linha.variacao_pct, criterio)) is not None
    ]
    if com_base:
        em_alta = [par for par in com_base if par[1] > 0]
        metricas |= {"n_com_base": len(com_base), "n_em_alta": len(em_alta)}
        leituras.append(
            (
                "alimentadores_em_alta",
                f"O {indice} subiu em {len(em_alta)} dos {len(com_base)} alimentadores "
                "com comparação contra o período base.",
            )
        )
        if em_alta:
            cod, pct = max(em_alta, key=lambda par: par[1])
            metricas |= {"maior_alta": cod, "maior_alta_pct": round(pct, 1)}
            leituras.append(
                (
                    "maior_alta",
                    f"Onde o {indice} mais subiu foi no {cod}: {variou(round(pct, 1))} "
                    "contra o período base.",
                )
            )

    if not leituras:
        leituras.append(
            ("pior_alimentador", f"O {pior.cod_alimentador} tem o pior {indice} {lugar}.")
        )
    return com_candidatas(leituras, metricas)
