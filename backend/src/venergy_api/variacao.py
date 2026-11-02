"""Variação entre dois valores ou dois períodos: as mesmas regras em todas as telas."""

from decimal import Decimal


def variacao_pct(base: Decimal, atual: Decimal) -> float | None:
    """Quanto o atual variou sobre a base, em %. Vazio quando a base é zero.

    Não existe variação percentual sobre nada: devolver zero ou infinito esconderia que a
    comparação não faz sentido.
    """
    if base == 0:
        return None
    return float((atual - base) / base * 100)


def meses_no_calendario(inicio: str, fim: str) -> int:
    """Meses de calendário de `inicio` a `fim` (AAAA-MM), inclusive.

    Uma variação entre períodos só vale com todos os meses dos dois lados na Gold (DEC-054):
    comparar com isto o número de meses com dado diz se o período está completo.
    """
    ano_inicio, mes_inicio = map(int, inicio.split("-"))
    ano_fim, mes_fim = map(int, fim.split("-"))
    return (ano_fim - ano_inicio) * 12 + mes_fim - mes_inicio + 1
