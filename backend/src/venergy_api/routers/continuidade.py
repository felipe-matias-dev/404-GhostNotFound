"""Rotas de continuidade: DEC e FEC por alimentador, o ranking dos piores e os recortes."""

from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy import select

from venergy_api.database import SessionDep
from venergy_api.models import ContinuidadeAlimentadorMensal
from venergy_api.schemas import ContinuidadeAlimentadorMensalSchema, ContinuidadeSerieFiltroSchema

router = APIRouter(prefix="/continuidade", tags=["continuidade"])


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
