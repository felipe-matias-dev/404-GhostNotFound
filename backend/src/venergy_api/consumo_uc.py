"""Consumo de uma UC nos últimos 12 meses contra o mesmo período do ano anterior."""

from collections.abc import Iterable
from decimal import Decimal

from venergy_api.models import FatoFaturamentoMensal
from venergy_api.schemas import ConsumoMesSchema, ConsumoUcSchema, Tendencia
from venergy_api.variacao import variacao_pct

MESES_DA_JANELA = 12

# Faixa do "estável" (DEC-036): o consumo varia mês a mês, e uma variação pequena não
# explica uma conta que o cliente achou alta. Suposição nossa: o case não define o corte.
LIMITE_DA_TENDENCIA = Decimal("0.10")


def deslocar_competencia(competencia: str, meses: int) -> str:
    """Soma (ou subtrai) meses a uma competência AAAA-MM."""
    ano, mes = int(competencia[:4]), int(competencia[5:])
    indice = ano * 12 + (mes - 1) + meses
    return f"{indice // 12:04d}-{indice % 12 + 1:02d}"


def inicio_da_consulta(referencia: str) -> str:
    """Primeira competência a ler: os 12 meses do ano anterior vêm antes da janela."""
    return deslocar_competencia(referencia, -(2 * MESES_DA_JANELA - 1))


def _tendencia(base: Decimal | None, atual: Decimal | None) -> Tendencia:
    # Sem fatura num dos meses, ou com a base em zero, não há com o que comparar.
    if base is None or atual is None or base == 0:
        return "sem_comparacao"
    # Decimal, e não a porcentagem em float: o limite exato (+10%) precisa cair do lado certo.
    variacao = (atual - base) / base
    if variacao > LIMITE_DA_TENDENCIA:
        return "subiu"
    if variacao < -LIMITE_DA_TENDENCIA:
        return "caiu"
    return "estavel"


def montar_consumo(
    referencia: str | None, faturas: Iterable[FatoFaturamentoMensal]
) -> ConsumoUcSchema:
    """Monta os 12 meses terminados na referência, cada um ao lado do mesmo mês do ano anterior."""
    if referencia is None:
        return ConsumoUcSchema(
            referencia=None,
            meses=[],
            kwh_12m=Decimal(0),
            kwh_12m_ano_anterior=Decimal(0),
            variacao_12m_pct=None,
            variacao_ultimo_mes_pct=None,
            tendencia="sem_comparacao",
        )

    por_competencia = {fatura.competencia: fatura for fatura in faturas}
    meses: list[ConsumoMesSchema] = []
    for deslocamento in range(-(MESES_DA_JANELA - 1), 1):
        competencia = deslocar_competencia(referencia, deslocamento)
        fatura = por_competencia.get(competencia)
        anterior = por_competencia.get(deslocar_competencia(competencia, -MESES_DA_JANELA))
        meses.append(
            ConsumoMesSchema(
                competencia=competencia,
                kwh_faturado=fatura.kwh_faturado if fatura else None,
                kwh_ano_anterior=anterior.kwh_faturado if anterior else None,
                receita_faturada=fatura.receita_faturada if fatura else None,
                bandeira=fatura.bandeira if fatura else None,
                dias_faturados=fatura.dias_faturados if fatura else None,
            )
        )

    # Soma em Decimal, ignorando os meses sem fatura. Sem nenhuma fatura no ano anterior, a
    # soma é zero e a porcentagem fica vazia (variacao_pct não divide por zero).
    kwh_12m = sum((mes.kwh_faturado or Decimal(0) for mes in meses), Decimal(0))
    kwh_12m_ano_anterior = sum((mes.kwh_ano_anterior or Decimal(0) for mes in meses), Decimal(0))
    ultimo = meses[-1]
    return ConsumoUcSchema(
        referencia=referencia,
        meses=meses,
        kwh_12m=kwh_12m,
        kwh_12m_ano_anterior=kwh_12m_ano_anterior,
        variacao_12m_pct=variacao_pct(kwh_12m_ano_anterior, kwh_12m),
        variacao_ultimo_mes_pct=(
            variacao_pct(ultimo.kwh_ano_anterior, ultimo.kwh_faturado)
            if ultimo.kwh_ano_anterior is not None and ultimo.kwh_faturado is not None
            else None
        ),
        tendencia=_tendencia(ultimo.kwh_ano_anterior, ultimo.kwh_faturado),
    )
