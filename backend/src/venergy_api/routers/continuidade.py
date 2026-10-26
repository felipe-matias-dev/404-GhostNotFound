"""Rotas de continuidade: DEC e FEC por alimentador, o ranking dos piores e os recortes."""

from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy import ColumnElement, Double, cast, distinct, func, select
from sqlalchemy.orm import InstrumentedAttribute, Session

from venergy_api.database import SessionDep
from venergy_api.models import ContinuidadeAlimentadorMensal
from venergy_api.schemas import (
    ContinuidadeAlimentadorMensalSchema,
    ContinuidadeSerieFiltroSchema,
    RankingAlimentadorSchema,
    RankingContinuidadeSchema,
    RankingFiltroSchema,
)

router = APIRouter(prefix="/continuidade", tags=["continuidade"])


def contar_meses(
    session: Session, competencia: InstrumentedAttribute[str], inicio: str, fim: str
) -> int:
    """Meses com dado no período, na tabela inteira: o divisor da média mensal de UCs."""
    # Contados sem o filtro do recorte, para um bairro sem linha num mês contar 0 UC nesse
    # mês, e não sumir do divisor. Texto AAAA-MM compara na ordem do calendário (DEC-011).
    consulta = select(func.count(distinct(competencia))).where(competencia.between(inicio, fim))
    return session.scalar(consulta) or 0


def indices(
    horas: InstrumentedAttribute[float],
    interrupcoes: InstrumentedAttribute[int],
    n_uc: InstrumentedAttribute[int],
    n_meses: int,
) -> list[ColumnElement]:
    """Colunas dos índices de um período: soma dos componentes ÷ média mensal de UCs.

    É a regra do contrato (gold_schema.yaml) e a mesma da camada semântica do agente. A conta
    mora aqui, e não no frontend: DEC e FEC não se somam nem se tiram a média entre recortes.
    """
    total_horas = func.sum(horas)
    total_interrupcoes = func.sum(interrupcoes)
    total_uc = cast(func.sum(n_uc), Double)
    # soma ÷ (Σ n_uc ÷ meses) = soma × meses ÷ Σ n_uc; sem UC, o índice fica nulo.
    divisor = func.nullif(total_uc, 0)
    return [
        (total_horas * n_meses / divisor).label("dec"),
        (total_interrupcoes * n_meses / divisor).label("fec"),
        total_horas.label("horas_interrompidas"),
        total_interrupcoes.label("n_interrupcoes"),
        # Sem meses com dado não há linha a agrupar, então o max() só evita dividir por zero.
        (total_uc / max(n_meses, 1)).label("n_uc_medio"),
    ]


@router.get("/alimentadores/mensal")
def get_serie_alimentadores(
    filtro: Annotated[ContinuidadeSerieFiltroSchema, Query()], session: SessionDep
) -> list[ContinuidadeAlimentadorMensalSchema]:
    """DEC e FEC de cada alimentador por competência, como a Gold calculou."""
    # Os índices mensais são lidos da Gold, e não refeitos: o mês é o grão dela.
    tabela = ContinuidadeAlimentadorMensal
    consulta = select(tabela).order_by(tabela.cod_alimentador, tabela.competencia)
    if filtro.inicio:
        consulta = consulta.where(tabela.competencia >= filtro.inicio)
    if filtro.fim:
        consulta = consulta.where(tabela.competencia <= filtro.fim)
    if filtro.cod_alimentador:
        consulta = consulta.where(tabela.cod_alimentador.in_(filtro.cod_alimentador))
    return [
        ContinuidadeAlimentadorMensalSchema.model_validate(linha, from_attributes=True)
        for linha in session.scalars(consulta)
    ]


@router.get("/alimentadores/ranking")
def get_ranking_alimentadores(
    filtro: Annotated[RankingFiltroSchema, Query()], session: SessionDep
) -> RankingContinuidadeSchema:
    """Os piores alimentadores do período, pelo DEC ou pelo FEC."""
    tabela = ContinuidadeAlimentadorMensal
    n_meses = contar_meses(session, tabela.competencia, filtro.inicio, filtro.fim)
    colunas = indices(tabela.horas_interrompidas, tabela.n_interrupcoes, tabela.n_uc, n_meses)
    dec, fec = colunas[0], colunas[1]
    principal, secundario = (dec, fec) if filtro.criterio == "dec" else (fec, dec)
    consulta = (
        select(tabela.cod_alimentador, *colunas)
        .where(tabela.competencia.between(filtro.inicio, filtro.fim))
        .group_by(tabela.cod_alimentador)
        .order_by(
            principal.desc().nulls_last(),
            secundario.desc().nulls_last(),
            tabela.cod_alimentador,
        )
    )
    return RankingContinuidadeSchema(
        inicio=filtro.inicio,
        fim=filtro.fim,
        criterio=filtro.criterio,
        n_meses=n_meses,
        alimentadores=[
            RankingAlimentadorSchema(**linha._mapping) for linha in session.execute(consulta)
        ],
    )
