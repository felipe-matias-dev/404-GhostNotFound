"""Índices de continuidade (DEC e FEC) de um período, calculados sobre componentes somados."""

from sqlalchemy import ColumnElement, Double, Integer, cast, func
from sqlalchemy.orm import InstrumentedAttribute


def indices(
    horas: InstrumentedAttribute[float],
    interrupcoes: InstrumentedAttribute[int],
    n_uc: InstrumentedAttribute[int],
    n_meses: int | ColumnElement[int],
    no_periodo: ColumnElement[bool] | None = None,
) -> list[ColumnElement]:
    """Colunas dos índices de um período: soma dos componentes ÷ média mensal de UCs.

    É a regra do contrato (gold_schema.yaml) e a mesma da camada semântica do agente. A conta
    mora aqui, e não no frontend: DEC e FEC não se somam nem se tiram a média entre recortes.
    Com `no_periodo`, só as linhas dele entram nas somas (FILTER), para vários períodos saírem
    da mesma leitura; `n_meses` pode então ser uma expressão SQL.
    """

    def soma(coluna: InstrumentedAttribute) -> ColumnElement:
        total = func.sum(coluna)
        return total if no_periodo is None else total.filter(no_periodo)

    total_horas = func.coalesce(soma(horas), 0.0)
    total_interrupcoes = func.coalesce(soma(interrupcoes), 0)
    total_uc = cast(soma(n_uc), Double)
    # soma ÷ (Σ n_uc ÷ meses) = soma × meses ÷ Σ n_uc; sem UC, o índice fica nulo.
    divisor = func.nullif(total_uc, 0)
    return [
        (total_horas * n_meses / divisor).label("dec"),
        (total_interrupcoes * n_meses / divisor).label("fec"),
        total_horas.label("horas_interrompidas"),
        total_interrupcoes.label("n_interrupcoes"),
        # Sem meses com dado o divisor vira 1, só para não dividir por zero.
        (total_uc / func.greatest(cast(n_meses, Integer), 1)).label("n_uc_medio"),
    ]
