"""Por que a conta de uma UC mudou: a diferença em R$ dividida por motivo.

É a decomposição preço × volume da receita da empresa (DEC-029) aplicada a uma fatura. O
backend calcula, e a tela só mostra: as partes somam exatamente a diferença das duas contas.
"""

from collections.abc import Iterable
from decimal import Decimal

from venergy_api.consumo_uc import MESES_DA_JANELA, deslocar_competencia
from venergy_api.models import FatoFaturamentoMensal
from venergy_api.schemas import VariacaoContaSchema

_CENTAVO = Decimal("0.01")


def _centavos(valor: Decimal) -> Decimal:
    return valor.quantize(_CENTAVO)


def montar_variacao_conta(
    referencia: str | None, faturas: Iterable[FatoFaturamentoMensal]
) -> VariacaoContaSchema | None:
    """Divide a diferença da conta do mês de referência contra o mesmo mês do ano anterior.

    Vazio quando não há com o que comparar: sem fatura num dos dois meses, ou sem energia na
    conta do ano anterior (painel solar que compensou tudo), porque aí não existe preço por kWh.
    """
    if referencia is None:
        return None
    por_competencia = {fatura.competencia: fatura for fatura in faturas}
    comparada_em = deslocar_competencia(referencia, -MESES_DA_JANELA)
    atual = por_competencia.get(referencia)
    anterior = por_competencia.get(comparada_em)
    if atual is None or anterior is None or anterior.kwh_faturado == 0:
        return None

    preco_anterior = anterior.receita_energia / anterior.kwh_faturado
    # Mais ou menos energia, ao preço do ano anterior. Os dias faturados não dividem esse
    # volume: na Gold real o kWh não acompanha os dias da fatura, e a divisão por dia dava
    # partes de dezenas de milhares de reais para uma conta que mudou menos de mil.
    consumo = _centavos((atual.kwh_faturado - anterior.kwh_faturado) * preco_anterior)
    # O acréscimo da bandeira além do que a conta do ano anterior já trazia por kWh.
    bandeira = _centavos(
        atual.receita_bandeira
        - atual.kwh_faturado * (anterior.receita_bandeira / anterior.kwh_faturado)
    )
    variacao_da_energia = atual.receita_energia - anterior.receita_energia
    # A tarifa fica com a sobra do arredondamento: assim as partes somam exatamente a
    # diferença que o atendente vê nas duas contas, sem uma linha "arredondamento".
    tarifa = variacao_da_energia - consumo - bandeira
    tributos = (atual.receita_faturada - anterior.receita_faturada) - variacao_da_energia

    return VariacaoContaSchema(
        competencia=referencia,
        competencia_comparada=comparada_em,
        conta=atual.receita_faturada,
        conta_comparada=anterior.receita_faturada,
        diferenca=atual.receita_faturada - anterior.receita_faturada,
        dias_faturados=atual.dias_faturados,
        dias_faturados_comparada=anterior.dias_faturados,
        consumo=consumo,
        tarifa=tarifa,
        bandeira=bandeira,
        tributos=tributos,
        leitura_estimada="estimada" in (atual.tipo_leitura, anterior.tipo_leitura),
    )
