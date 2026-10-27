"""Variação percentual entre dois valores: a mesma regra na receita e na visão 360."""

from decimal import Decimal


def variacao_pct(base: Decimal, atual: Decimal) -> float | None:
    """Quanto o atual variou sobre a base, em %. Vazio quando a base é zero.

    Não existe variação percentual sobre nada: devolver zero ou infinito esconderia que a
    comparação não faz sentido.
    """
    if base == 0:
        return None
    return float((atual - base) / base * 100)
