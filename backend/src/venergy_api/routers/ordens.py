"""Rotas das ordens de inspeção: o gerente de perdas gera OIs a partir da fila e as acompanha."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from venergy_api.database import SessionDep
from venergy_api.models import DimUc, OrdemEvento, OrdemInspecao
from venergy_api.ordens import STATUS_ATIVOS, StatusOrdem
from venergy_api.schemas import CriarOrdensSchema, ErroSchema, OrdemDetalheSchema, OrdemSchema

router = APIRouter(prefix="/ordens-inspecao", tags=["ordens de inspeção"])

INDICE_UC_ATIVA = "uq_ordem_inspecao_uc_ativa"


def _erro_ja_ativas(cod_ucs: list[str]) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=f"Já existe ordem ativa para as UCs: {', '.join(sorted(cod_ucs))}",
    )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_404_NOT_FOUND: {"model": ErroSchema},
        status.HTTP_409_CONFLICT: {"model": ErroSchema},
    },
)
def criar_ordens(pedido: CriarOrdensSchema, session: SessionDep) -> list[OrdemSchema]:
    """Gera uma OI por UC, tudo ou nada: se uma UC falhar, nenhuma OI é criada."""
    # Sem FK para a Gold (ver models.OrdemInspecao), a existência da UC é garantida aqui.
    encontradas = set(session.scalars(select(DimUc.cod_uc).where(DimUc.cod_uc.in_(pedido.cod_ucs))))
    faltando = [cod for cod in pedido.cod_ucs if cod not in encontradas]
    if faltando:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unidades consumidoras não encontradas: {', '.join(faltando)}",
        )

    # Checar antes dá uma mensagem que cita as UCs; o índice único no banco continua
    # sendo a garantia para duas requisições simultâneas, tratadas no except abaixo.
    ja_ativas = list(
        session.scalars(
            select(OrdemInspecao.cod_uc).where(
                OrdemInspecao.cod_uc.in_(pedido.cod_ucs),
                OrdemInspecao.status.in_(STATUS_ATIVOS),
            )
        )
    )
    if ja_ativas:
        raise _erro_ja_ativas(ja_ativas)

    ordens = [
        OrdemInspecao(cod_uc=cod, eventos=[OrdemEvento(status_novo=StatusOrdem.GERADA)])
        for cod in pedido.cod_ucs
    ]
    session.add_all(ordens)
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        if getattr(error.orig.diag, "constraint_name", None) == INDICE_UC_ATIVA:
            raise _erro_ja_ativas(pedido.cod_ucs) from error
        raise
    return [OrdemSchema.model_validate(ordem) for ordem in ordens]


@router.get("")
def listar_ordens(
    session: SessionDep,
    # Na URL continua ?status=; o nome interno evita esconder o módulo status do FastAPI.
    filtro_status: Annotated[StatusOrdem | None, Query(alias="status")] = None,
) -> list[OrdemSchema]:
    """Lista as OIs, das mais recentes para as mais antigas, opcionalmente por status."""
    # Pelo id, e não por criada_em: OIs do mesmo lote têm o mesmo horário (now() da
    # transação), e o id desempata de forma estável.
    consulta = select(OrdemInspecao).order_by(OrdemInspecao.id.desc())
    if filtro_status is not None:
        consulta = consulta.where(OrdemInspecao.status == filtro_status)
    return [OrdemSchema.model_validate(ordem) for ordem in session.scalars(consulta)]


@router.get("/{ordem_id}", responses={status.HTTP_404_NOT_FOUND: {"model": ErroSchema}})
def obter_ordem(ordem_id: int, session: SessionDep) -> OrdemDetalheSchema:
    ordem = session.get(OrdemInspecao, ordem_id)
    if ordem is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ordem de inspeção {ordem_id} não encontrada",
        )
    return OrdemDetalheSchema.model_validate(ordem)
