"""Rota da fila de suspeitas: de onde o gerente de perdas escolhe as UCs para inspecionar."""

from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy import and_, func, select

from venergy_api.database import SessionDep
from venergy_api.models import FilaSuspeita, OrdemInspecao
from venergy_api.ordens import STATUS_ATIVOS
from venergy_api.schemas import (
    FilaFiltroSchema,
    FilaItemSchema,
    FilaPaginaSchema,
    OrdemAtivaSchema,
)

router = APIRouter(prefix="/fila-suspeitas", tags=["fila de suspeitas"])


@router.get("")
def get_fila(filtro: Annotated[FilaFiltroSchema, Query()], session: SessionDep) -> FilaPaginaSchema:
    """A fila da mais para a menos suspeita, com a ordem ativa de cada UC."""
    fila = FilaSuspeita
    # Junção à esquerda: toda UC da fila aparece, com ou sem ordem. O índice único parcial
    # (no máximo uma OI ativa por UC) garante que a junção não duplica linhas.
    com_ordem_ativa = and_(
        OrdemInspecao.cod_uc == fila.cod_uc, OrdemInspecao.status.in_(STATUS_ATIVOS)
    )
    total_consulta = (
        select(func.count()).select_from(fila).outerjoin(OrdemInspecao, com_ordem_ativa)
    )
    consulta = (
        select(fila, OrdemInspecao.id, OrdemInspecao.status)
        .outerjoin(OrdemInspecao, com_ordem_ativa)
        # O desempate pelo cod_uc deixa a página estável: o contrato não garante posição única.
        .order_by(fila.score_suspeita, fila.cod_uc)
        .offset((filtro.pagina - 1) * filtro.tamanho)
        .limit(filtro.tamanho)
    )
    if filtro.sem_ordem_ativa:
        total_consulta = total_consulta.where(OrdemInspecao.id.is_(None))
        consulta = consulta.where(OrdemInspecao.id.is_(None))

    itens = [
        FilaItemSchema(
            cod_uc=suspeita.cod_uc,
            score_suspeita=suspeita.score_suspeita,
            motivos=suspeita.motivos,
            kwh_recuperavel_est=suspeita.kwh_recuperavel_est,
            ordem_ativa=(
                OrdemAtivaSchema(id=ordem_id, status=ordem_status) if ordem_id is not None else None
            ),
        )
        for suspeita, ordem_id, ordem_status in session.execute(consulta)
    ]
    return FilaPaginaSchema(
        itens=itens,
        total=session.scalar(total_consulta) or 0,
        pagina=filtro.pagina,
        tamanho=filtro.tamanho,
    )
