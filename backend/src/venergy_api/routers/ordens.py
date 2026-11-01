"""Rotas das ordens de inspeção: o gerente de perdas gera OIs a partir da fila e as acompanha."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from venergy_api.auth import Perfil, UsuarioLogado
from venergy_api.avisos_ordens import (
    INTERVALO_PING_SEGUNDOS,
    avisar_mudanca_de_ordem,
    fluxo_de_avisos,
)
from venergy_api.database import SessionDep
from venergy_api.models import DimUc, OrdemEvento, OrdemInspecao
from venergy_api.ordens import STATUS_ATIVOS, StatusOrdem, TransicaoInvalidaError, validar_transicao
from venergy_api.schemas import (
    AtualizarOrdemSchema,
    CriarOrdensSchema,
    ErroSchema,
    OrdemDetalheSchema,
    OrdemSchema,
    OrdensFiltroSchema,
)
from venergy_api.sessao import exigir_perfil

router = APIRouter(prefix="/ordens-inspecao", tags=["ordens de inspeção"])

INDICE_UC_ATIVA = "uq_ordem_inspecao_uc_ativa"

# O FastAPI não descreve SSE sozinho: cada mensagem `ordens` traz este objeto no campo data.
EVENTO_ORDENS_SSE: dict[str, Any] = {
    "type": "object",
    "required": ["ordem_ids"],
    "properties": {"ordem_ids": {"type": ["array", "null"], "items": {"type": "integer"}}},
}

# Gerar e mudar ordem é a única escrita do sistema, e é trabalho do gerente de perdas. Os
# outros perfis só consultam; o menu esconde os botões, e esta barreira vale para quem chama a API.
# A mesma dependência que barra com 403 entrega quem agiu, para o histórico guardar o autor.
UsuarioDePerdasDep = Annotated[UsuarioLogado, Depends(exigir_perfil(Perfil.PERDAS))]


def _erro_ja_ativas(cod_ucs: list[str]) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=f"Já existe ordem ativa para as UCs: {', '.join(sorted(cod_ucs))}",
    )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_403_FORBIDDEN: {"model": ErroSchema},
        status.HTTP_404_NOT_FOUND: {"model": ErroSchema},
        status.HTTP_409_CONFLICT: {"model": ErroSchema},
    },
)
def criar_ordens(
    pedido: CriarOrdensSchema, session: SessionDep, usuario: UsuarioDePerdasDep
) -> list[OrdemSchema]:
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
        OrdemInspecao(
            cod_uc=cod,
            eventos=[OrdemEvento(status_novo=StatusOrdem.GERADA, autor_login=usuario.login)],
        )
        for cod in pedido.cod_ucs
    ]
    session.add_all(ordens)
    try:
        # O flush dá o id às ordens, e o aviso só sai com o commit: se o índice único recusar
        # a gravação, nenhuma tela é avisada.
        session.flush()
        avisar_mudanca_de_ordem(session, [ordem.id for ordem in ordens])
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
    filtro: Annotated[OrdensFiltroSchema, Query()],
) -> list[OrdemSchema]:
    """Lista as OIs, das mais recentes para as mais antigas, opcionalmente por status."""
    # Pelo id, e não por criada_em: OIs do mesmo lote têm o mesmo horário (now() da
    # transação), e o id desempata de forma estável.
    consulta = select(OrdemInspecao).order_by(OrdemInspecao.id.desc())
    if filtro.status is not None:
        consulta = consulta.where(OrdemInspecao.status == filtro.status)
    predicados = [
        coluna == valor
        for coluna, valor in (
            (DimUc.municipio, filtro.municipio),
            (DimUc.bairro, filtro.bairro),
            (DimUc.classe, filtro.classe),
        )
        if valor is not None
    ]
    if predicados:
        consulta = consulta.join(DimUc, DimUc.cod_uc == OrdemInspecao.cod_uc).where(*predicados)
    return [OrdemSchema.model_validate(ordem) for ordem in session.scalars(consulta)]


# Declarada antes de /{ordem_id}: do contrário, "eventos" seria lido como o id de uma ordem (422).
@router.get(
    "/eventos",
    response_class=StreamingResponse,
    responses={
        status.HTTP_200_OK: {
            "description": (
                "Eventos SSE: `ordens`, com os ids das ordens que mudaram (ou `null`, se foram "
                "muitas), e ping de comentário. A tela refaz a consulta ao receber."
            ),
            "content": {"text/event-stream": {"schema": EVENTO_ORDENS_SSE}},
        },
    },
)
async def acompanhar_ordens(request: Request) -> StreamingResponse:
    """Avisa a tela, sem ela perguntar, de que ordens foram criadas ou mudaram de status."""
    return StreamingResponse(
        fluxo_de_avisos(request.app.state.settings.database_url, INTERVALO_PING_SEGUNDOS),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _buscar_ordem(session: Session, ordem_id: int, *, travar: bool = False) -> OrdemInspecao:
    ordem = session.get(OrdemInspecao, ordem_id, with_for_update=travar)
    if ordem is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ordem de inspeção {ordem_id} não encontrada",
        )
    return ordem


@router.get("/{ordem_id}", responses={status.HTTP_404_NOT_FOUND: {"model": ErroSchema}})
def obter_ordem(ordem_id: int, session: SessionDep) -> OrdemDetalheSchema:
    return OrdemDetalheSchema.model_validate(_buscar_ordem(session, ordem_id))


@router.patch(
    "/{ordem_id}",
    responses={
        status.HTTP_403_FORBIDDEN: {"model": ErroSchema},
        status.HTTP_404_NOT_FOUND: {"model": ErroSchema},
        status.HTTP_409_CONFLICT: {"model": ErroSchema},
    },
)
def atualizar_ordem(
    ordem_id: int,
    mudanca: AtualizarOrdemSchema,
    session: SessionDep,
    usuario: UsuarioDePerdasDep,
) -> OrdemDetalheSchema:
    """Muda o status da OI (inclusive cancelar) e registra a mudança no histórico."""
    # Trava a linha até o commit (SELECT ... FOR UPDATE): sem isso, duas mudanças
    # simultâneas leriam o mesmo status atual e as duas passariam pela validação.
    ordem = _buscar_ordem(session, ordem_id, travar=True)
    try:
        validar_transicao(ordem.status, mudanca.status)
    except TransicaoInvalidaError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error

    ordem.eventos.append(
        OrdemEvento(
            status_anterior=ordem.status,
            status_novo=mudanca.status,
            observacao=mudanca.observacao,
            autor_login=usuario.login,
        )
    )
    ordem.status = mudanca.status
    ordem.resultado = mudanca.resultado
    # A observação da OI é o que a equipe viu em campo ou o motivo do cancelamento. O motivo
    # de uma volta para GERADA fica só no evento, para não sobrescrevê-la.
    if mudanca.observacao is not None and mudanca.status != StatusOrdem.GERADA:
        ordem.observacao = mudanca.observacao
    avisar_mudanca_de_ordem(session, [ordem.id])
    session.commit()
    return OrdemDetalheSchema.model_validate(ordem)
