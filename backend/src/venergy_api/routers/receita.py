"""Rotas de receita: a evolução mensal que a diretoria acompanha no dashboard executivo."""

from fastapi import APIRouter
from sqlalchemy import select

from venergy_api.database import SessionDep
from venergy_api.models import KpisMensais
from venergy_api.schemas import KpisMensaisSchema

router = APIRouter(prefix="/receita", tags=["receita"])


@router.get("/mensal")
def get_receita_mensal(session: SessionDep) -> list[KpisMensaisSchema]:
    """Indicadores de cada competência, do mês mais antigo ao mais recente."""
    # A ordem sai do banco, e não do frontend: o gráfico só exibe. Competência em texto
    # AAAA-MM (DEC-011) ordena certo como texto.
    kpis = session.scalars(select(KpisMensais).order_by(KpisMensais.competencia))
    return [KpisMensaisSchema.model_validate(linha) for linha in kpis]
