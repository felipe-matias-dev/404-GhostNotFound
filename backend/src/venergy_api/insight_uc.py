"""As métricas da Unidade consumidora que o redator de insights narra.

A tela mostra a conta, o consumo mês a mês e por que a conta mudou. O que ela não diz é a resposta
direta ao cliente que acha a conta alta: se ele gastou mais energia mesmo e se o mês é uma
exceção ou repete os 12 meses. Nenhum dado do titular entra aqui, só números da conta e do consumo.
"""

import re
from collections.abc import Sequence
from decimal import ROUND_HALF_UP, Decimal

from venergy_api.insights import com_candidatas, numero_br, variou
from venergy_api.insights import motivo_da_recusa as recusar
from venergy_api.schemas import ConsumoUcSchema, VariacaoContaSchema

_TERMOS_PROIBIDOS = re.compile(
    r"\b(simultaneamente|desempenho|segmentos?|recorte|kwh_faturado)\b|·|_",
    re.IGNORECASE,
)


def _pct(valor: float | None) -> float | None:
    return None if valor is None else round(valor, 1)


def _reais(valor: Decimal) -> float:
    return float(valor.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def motivo_da_recusa(
    texto: str, metricas: dict[str, object], escolhidas: Sequence[str] = ()
) -> str | None:
    """Por que o texto da IA não diz as leituras que ela escolheu, ou None se diz."""
    return recusar(texto, metricas, escolhidas, _TERMOS_PROIBIDOS)


def texto_aceito(texto: str, metricas: dict[str, object], escolhidas: Sequence[str] = ()) -> bool:
    return motivo_da_recusa(texto, metricas, escolhidas) is None


def _leituras_do_consumo(mes: float | None, ano: float | None) -> list[tuple[str, str]]:
    if mes is not None and ano is not None:
        if mes > 0 and ano <= 0:
            return [
                (
                    "mes_fora_do_padrao",
                    f"O consumo do último mês {variou(mes)}, mas nos 12 meses {variou(ano)}: "
                    "é um mês fora do padrão, não uma tendência.",
                )
            ]
        if mes * ano > 0:
            return [
                (
                    "tendencia",
                    f"O consumo {variou(mes)} no último mês e {variou(ano)} nos 12 meses: "
                    "o movimento se repete, não é de um mês só.",
                )
            ]
        return [
            (
                "consumo_do_mes_e_do_ano",
                f"O consumo do último mês {variou(mes)}, e nos 12 meses {variou(ano)}.",
            )
        ]
    if ano is not None:
        return [("consumo_do_ano", f"Nos 12 meses, o consumo {variou(ano)} contra o ano anterior.")]
    return []


def metricas_da_uc(
    consumo: ConsumoUcSchema, conta: VariacaoContaSchema | None
) -> dict[str, object] | None:
    """O JSON de métricas da UC, ou None se não há com o que comparar o consumo nem a conta."""
    mes = _pct(consumo.variacao_ultimo_mes_pct)
    ano = _pct(consumo.variacao_12m_pct)
    metricas: dict[str, object] = {"referencia": consumo.referencia}
    if mes is not None:
        metricas["variacao_consumo_mes_pct"] = mes
    if ano is not None:
        metricas |= {"variacao_consumo_12m_pct": ano, "meses_comparados": consumo.meses_comparados}

    leituras: list[tuple[str, str]] = []
    if conta is not None and conta.diferenca > 0 and mes is not None:
        diferenca = _reais(conta.diferenca)
        metricas |= {
            "competencia_comparada": conta.competencia_comparada,
            "diferenca_conta": diferenca,
        }
        subiu = f"A conta subiu R$ {numero_br(diferenca, 2)}"
        if mes <= 0:
            leituras.append(
                (
                    "conta_sem_consumo",
                    f"{subiu}, mas o consumo do mês {variou(mes)} contra o mesmo mês do ano "
                    "anterior: o cliente não gastou mais energia.",
                )
            )
        else:
            leituras.append(
                (
                    "conta_com_consumo",
                    f"{subiu}, e o consumo do mês {variou(mes)} contra o mesmo mês do ano "
                    "anterior.",
                )
            )
    leituras += _leituras_do_consumo(mes, ano)
    if conta is not None and conta.leitura_estimada:
        leituras.append(
            (
                "leitura_estimada",
                "Uma das leituras foi estimada: a próxima leitura real corrige o consumo.",
            )
        )
    if not leituras:
        return None
    return com_candidatas(leituras, metricas)
