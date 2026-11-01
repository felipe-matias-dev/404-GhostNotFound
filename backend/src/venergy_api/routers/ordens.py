"""Rotas das ordens de inspeção: o gerente de perdas gera OIs a partir da fila e as acompanha."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy import Double, cast, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from venergy_api.auth import Perfil, UsuarioLogado
from venergy_api.avisos_ordens import (
    INTERVALO_PING_SEGUNDOS,
    avisar_mudanca_de_ordem,
    fluxo_de_avisos,
    loop_suporta_listen,
)
from venergy_api.database import SessionDep
from venergy_api.models import DimUc, OrdemEvento, OrdemInspecao
from venergy_api.ordens import (
    STATUS_ATIVOS,
    LimitesDeAtraso,
    StatusOrdem,
    TransicaoInvalidaError,
    esta_atrasada,
    validar_transicao,
)
from venergy_api.schemas import (
    AtualizarOrdemSchema,
    CriarOrdensSchema,
    ErroSchema,
    OrdemDetalheSchema,
    OrdemSchema,
    OrdensFiltroSchema,
    TempoPorEtapaSchema,
)
from venergy_api.sessao import exigir_perfil

router = APIRouter(prefix="/ordens-inspecao", tags=["ordens de inspeção"])

INDICE_UC_ATIVA = "uq_ordem_inspecao_uc_ativa"

# As etapas em que uma OI espera por alguém; CONCLUIDA e CANCELADA são finais e não têm duração.
ETAPAS_DO_RESUMO = (StatusOrdem.GERADA, StatusOrdem.EM_CAMPO)

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


def limites_de_atraso(request: Request) -> LimitesDeAtraso:
    configuracao = request.app.state.settings
    return LimitesDeAtraso(
        gerada_dias=configuracao.ordem_atraso_gerada_dias,
        em_campo_dias=configuracao.ordem_atraso_em_campo_dias,
    )


LimitesDep = Annotated[LimitesDeAtraso, Depends(limites_de_atraso)]


def _como_schema[S: OrdemSchema](
    modelo: type[S], ordem: OrdemInspecao, limites: LimitesDeAtraso
) -> S:
    schema = modelo.model_validate(ordem)
    atrasada = esta_atrasada(schema.status, schema.segundos_no_status, limites)
    return schema.model_copy(update={"atrasada": atrasada})


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
    pedido: CriarOrdensSchema,
    session: SessionDep,
    usuario: UsuarioDePerdasDep,
    limites: LimitesDep,
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
    return [_como_schema(OrdemSchema, ordem, limites) for ordem in ordens]


@router.get("")
def listar_ordens(
    session: SessionDep,
    filtro: Annotated[OrdensFiltroSchema, Query()],
    limites: LimitesDep,
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
    return [_como_schema(OrdemSchema, ordem, limites) for ordem in session.scalars(consulta)]


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
        status.HTTP_503_SERVICE_UNAVAILABLE: {"model": ErroSchema},
    },
)
async def acompanhar_ordens(request: Request) -> StreamingResponse:
    """Avisa a tela, sem ela perguntar, de que ordens foram criadas ou mudaram de status."""
    # Um 503 antes de abrir o stream: o EventSource não reconecta depois de um status que não
    # seja 200, e a tela segue funcionando, só sem o tempo real. Abrir e abortar o stream faria
    # a tela reconectar e refazer as consultas a cada poucos segundos.
    if not loop_suporta_listen():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Avisos em tempo real indisponíveis neste servidor. No Windows, use --reload.",
        )
    return StreamingResponse(
        fluxo_de_avisos(request.app.state.settings.database_url, INTERVALO_PING_SEGUNDOS),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# Declarada antes de /{ordem_id}, como /eventos.
@router.get("/tempos-por-etapa")
def tempos_por_etapa(session: SessionDep) -> list[TempoPorEtapaSchema]:
    """Mediana e p90 do tempo que as OIs passaram em cada etapa ativa, com o número de passagens.

    Calculado sobre o histórico (app.ordem_evento), que é dado do backend. Cada evento abre uma
    passagem pela etapa em que a OI entrou e ela termina no evento seguinte da mesma OI; a
    passagem em curso ainda não tem fim e fica de fora. Uma OI que volta para GERADA conta duas.
    """
    seguinte = func.lead(OrdemEvento.ocorrido_em).over(
        partition_by=OrdemEvento.ordem_id, order_by=OrdemEvento.id
    )
    passagens = select(
        OrdemEvento.status_novo.label("etapa"),
        cast(func.extract("epoch", seguinte - OrdemEvento.ocorrido_em), Double).label("segundos"),
    ).cte("passagens")
    resumo = (
        select(
            passagens.c.etapa,
            func.count().label("n"),
            func.percentile_cont(0.5).within_group(passagens.c.segundos).label("mediana"),
            func.percentile_cont(0.9).within_group(passagens.c.segundos).label("p90"),
        )
        .where(passagens.c.segundos.is_not(None))
        .group_by(passagens.c.etapa)
    )
    por_etapa = {linha.etapa: linha for linha in session.execute(resumo)}
    return [
        TempoPorEtapaSchema(
            etapa=etapa,
            n=por_etapa[etapa].n if etapa in por_etapa else 0,
            mediana_segundos=por_etapa[etapa].mediana if etapa in por_etapa else None,
            p90_segundos=por_etapa[etapa].p90 if etapa in por_etapa else None,
        )
        for etapa in ETAPAS_DO_RESUMO
    ]


def _buscar_ordem(session: Session, ordem_id: int, *, travar: bool = False) -> OrdemInspecao:
    ordem = session.get(OrdemInspecao, ordem_id, with_for_update=travar)
    if ordem is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ordem de inspeção {ordem_id} não encontrada",
        )
    return ordem


@router.get("/{ordem_id}", responses={status.HTTP_404_NOT_FOUND: {"model": ErroSchema}})
def obter_ordem(ordem_id: int, session: SessionDep, limites: LimitesDep) -> OrdemDetalheSchema:
    return _como_schema(OrdemDetalheSchema, _buscar_ordem(session, ordem_id), limites)


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
    limites: LimitesDep,
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
    return _como_schema(OrdemDetalheSchema, ordem, limites)
