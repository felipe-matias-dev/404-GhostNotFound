"""Rotas de receita: a evolução mensal que a diretoria acompanha no dashboard executivo."""

from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy import select

from venergy_api.database import SessionDep
from venergy_api.models import KpisMensais
from venergy_api.schemas import KpisMensaisSchema, PeriodoSchema

router = APIRouter(prefix="/receita", tags=["receita"])


@router.get("/mensal")
def get_receita_mensal(
    periodo: Annotated[PeriodoSchema, Query()], session: SessionDep
) -> list[KpisMensaisSchema]:
    """Indicadores de cada competência do período, do mês mais antigo ao mais recente."""
    # A ordem sai do banco, e não do frontend: o gráfico só exibe. Competência em texto
    # AAAA-MM (DEC-011) ordena e compara certo como texto, inclusive no recorte.
    consulta = select(KpisMensais).order_by(KpisMensais.competencia)
    if periodo.inicio:
        consulta = consulta.where(KpisMensais.competencia >= periodo.inicio)
    if periodo.fim:
        consulta = consulta.where(KpisMensais.competencia <= periodo.fim)
    return [KpisMensaisSchema.model_validate(linha) for linha in session.scalars(consulta)]
