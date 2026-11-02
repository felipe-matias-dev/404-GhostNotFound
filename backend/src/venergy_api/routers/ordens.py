"""Rotas das ordens de inspeção: o gerente de perdas gera OIs a partir da fila e as acompanha."""

from collections.abc import AsyncGenerator, AsyncIterator
from contextlib import aclosing
from functools import partial
from typing import Annotated, Any

import psycopg
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
    status,
)
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
    ResultadoOrdem,
    StatusOrdem,
    TransicaoInvalidaError,
    esta_atrasada,
    validar_transicao,
)
from venergy_api.planilha_campo import (
    MAX_BYTES,
    TIPO_XLSX,
    PlanilhaInvalida,
    ler_planilha,
    montar_planilha,
)
from venergy_api.schemas import (
    AtualizarOrdemSchema,
    CriarOrdensSchema,
    ErroSchema,
    LinhaConcluidaSchema,
    LinhaRejeitadaSchema,
    OrdemDetalheSchema,
    OrdemSchema,
    OrdensFiltroSchema,
    ResultadoPlanilhaSchema,
    TempoPorEtapaSchema,
)
from venergy_api.sessao import UsuarioDep, conferidor_da_sessao, exigir_perfil

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
        status.HTTP_429_TOO_MANY_REQUESTS: {
            "model": ErroSchema,
            "description": "Telas demais com o tempo real abertas, do usuário ou no servidor.",
        },
        status.HTTP_503_SERVICE_UNAVAILABLE: {"model": ErroSchema},
    },
)
async def acompanhar_ordens(request: Request, usuario: UsuarioDep) -> StreamingResponse:
    """Avisa a tela, sem ela perguntar, de que ordens foram criadas ou mudaram de status."""
    # Toda recusa sai antes de abrir o stream: o EventSource não reconecta depois de um status
    # que não seja 200, e a tela segue funcionando, só sem o tempo real. Abrir e abortar o
    # stream faria a tela reconectar e refazer as consultas a cada poucos segundos.
    if not loop_suporta_listen():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Avisos em tempo real indisponíveis neste servidor. No Windows, use --reload.",
        )
    vagas = request.app.state.vagas_avisos_ordens
    if not vagas.reservar(usuario.login):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Muitas telas com o tempo real abertas. Feche uma aba e recarregue.",
        )
    fluxo = fluxo_de_avisos(
        request.app.state.settings.database_url,
        INTERVALO_PING_SEGUNDOS,
        ao_fechar=partial(vagas.liberar, usuario.login),
        sessao_valida=conferidor_da_sessao(request),
    )
    # O primeiro item (o ping depois do LISTEN) é lido aqui, e não pelo StreamingResponse: um
    # gerador que já começou sempre devolve a vaga ao fechar, mesmo que o cliente saia antes
    # do primeiro byte, e um banco sem conexão livre vira 503 em vez de um stream quebrado.
    try:
        abertura = await anext(fluxo)
    except psycopg.OperationalError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Avisos em tempo real indisponíveis agora. A tela segue sem eles.",
        ) from error
    return StreamingResponse(
        _a_partir_de(abertura, fluxo),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


async def _a_partir_de(primeiro: str, resto: AsyncGenerator[str]) -> AsyncIterator[str]:
    async with aclosing(resto):
        yield primeiro
        async for item in resto:
            yield item


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


def _mudar_status(
    ordem: OrdemInspecao,
    novo: StatusOrdem,
    resultado: ResultadoOrdem | None,
    observacao: str | None,
    autor_login: str,
) -> None:
    """Valida a transição e registra a mudança. Quem chama trava a linha e faz o commit.

    É o caminho único de mudança de status: o PATCH e o upload da planilha de campo passam
    por aqui, e a regra da máquina de estados não existe em duas cópias.
    """
    validar_transicao(ordem.status, novo)
    ordem.eventos.append(
        OrdemEvento(
            status_anterior=ordem.status,
            status_novo=novo,
            observacao=observacao,
            autor_login=autor_login,
        )
    )
    ordem.status = novo
    ordem.resultado = resultado
    # A observação da OI é o que a equipe viu em campo ou o motivo do cancelamento. O motivo
    # de uma volta para GERADA fica só no evento, para não sobrescrevê-la.
    if observacao is not None and novo != StatusOrdem.GERADA:
        ordem.observacao = observacao


@router.post(
    "/planilha",
    responses={
        status.HTTP_403_FORBIDDEN: {"model": ErroSchema},
        # Descrição explícita: sem ela o FastAPI usa o nome do status HTTP, que o Python 3.13
        # mudou de "Unprocessable Entity" para "Unprocessable Content", e o contrato gerado
        # passaria a depender da versão do Python de quem o gera.
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "model": ErroSchema,
            "description": "Planilha inutilizável: não é XLSX, está corrompida ou passa do limite",
        },
    },
)
def enviar_planilha(
    arquivo: UploadFile, session: SessionDep, usuario: UsuarioDePerdasDep
) -> ResultadoPlanilhaSchema:
    """Conclui as OIs em campo com os resultados da planilha preenchida pela equipe.

    Aplica as linhas válidas e devolve as rejeitadas com o motivo: uma linha escrita errada à
    mão não pode travar o arquivo inteiro. Arquivo inutilizável é 422 e não grava nada.
    """
    # Lê um byte além do limite só para o leitor reconhecer arquivo grande demais.
    conteudo = arquivo.file.read(MAX_BYTES + 1)
    try:
        lida = ler_planilha(conteudo)
    except PlanilhaInvalida as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from error

    # Trava as OIs ativas até o commit, como no PATCH: o envio concorrente da mesma planilha
    # (ou um PATCH simultâneo) leria o mesmo status e concluiria a OI duas vezes.
    cod_ucs = [linha.cod_uc for linha in lida.validas]
    ativas = {
        ordem.cod_uc: ordem
        for ordem in session.scalars(
            select(OrdemInspecao)
            .where(OrdemInspecao.cod_uc.in_(cod_ucs), OrdemInspecao.status.in_(STATUS_ATIVOS))
            .with_for_update()
        )
    }
    ultimo_status = _ultimo_status_por_uc(session, [cod for cod in cod_ucs if cod not in ativas])

    concluidas: list[LinhaConcluidaSchema] = []
    rejeitadas = [
        LinhaRejeitadaSchema.model_validate(r, from_attributes=True) for r in lida.rejeitadas
    ]
    for linha in lida.validas:
        ordem = ativas.get(linha.cod_uc)
        motivo = _motivo_sem_ordem_em_campo(ordem, ultimo_status.get(linha.cod_uc))
        if motivo is None and linha.ordem_id not in (None, ordem.id):
            motivo = f"A planilha é da ordem {linha.ordem_id}, e a ordem em campo da UC é outra"
        if motivo is not None:
            rejeitadas.append(
                LinhaRejeitadaSchema(
                    aba=linha.aba, linha=linha.linha, cod_uc=linha.cod_uc, motivo=motivo
                )
            )
            continue
        _mudar_status(
            ordem, StatusOrdem.CONCLUIDA, linha.resultado, linha.observacao, usuario.login
        )
        concluidas.append(
            LinhaConcluidaSchema(
                aba=linha.aba,
                linha=linha.linha,
                cod_uc=linha.cod_uc,
                ordem_id=ordem.id,
                resultado=linha.resultado,
            )
        )
    if concluidas:
        avisar_mudanca_de_ordem(session, [linha.ordem_id for linha in concluidas])
    session.commit()
    return ResultadoPlanilhaSchema(
        linhas_lidas=lida.linhas_lidas, concluidas=concluidas, rejeitadas=rejeitadas
    )


def _ultimo_status_por_uc(session: Session, cod_ucs: list[str]) -> dict[str, StatusOrdem]:
    """O status da OI mais recente de cada UC, para explicar por que não há OI em campo."""
    ultimo: dict[str, StatusOrdem] = {}
    consulta = (
        select(OrdemInspecao.cod_uc, OrdemInspecao.status)
        .where(OrdemInspecao.cod_uc.in_(cod_ucs))
        .order_by(OrdemInspecao.id.desc())
    )
    for cod_uc, status_ordem in session.execute(consulta):
        ultimo.setdefault(cod_uc, status_ordem)
    return ultimo


def _motivo_sem_ordem_em_campo(
    ordem: OrdemInspecao | None, ultimo_status: StatusOrdem | None
) -> str | None:
    if ordem is None:
        if ultimo_status is StatusOrdem.CONCLUIDA:
            return "Ordem já concluída"
        if ultimo_status is StatusOrdem.CANCELADA:
            return "A última ordem da UC foi cancelada"
        return "Nenhuma ordem de inspeção para a UC"
    if ordem.status is StatusOrdem.GERADA:
        return "A ordem ainda não foi enviada a campo"
    return None


@router.get(
    "/planilha",
    response_class=Response,
    responses={
        status.HTTP_200_OK: {
            "content": {TIPO_XLSX: {"schema": {"type": "string", "format": "binary"}}}
        },
        status.HTTP_403_FORBIDDEN: {"model": ErroSchema},
    },
)
def exportar_planilha(session: SessionDep, _usuario: UsuarioDePerdasDep) -> Response:
    """Baixa as OIs em campo na planilha que a equipe preenche e o upload lê de volta."""
    consulta = (
        select(OrdemInspecao.id, OrdemInspecao.cod_uc, DimUc.municipio, DimUc.bairro)
        .outerjoin(DimUc, DimUc.cod_uc == OrdemInspecao.cod_uc)
        .where(OrdemInspecao.status == StatusOrdem.EM_CAMPO)
        .order_by(OrdemInspecao.id)
    )
    conteudo = montar_planilha(tuple(linha) for linha in session.execute(consulta))
    return Response(
        content=conteudo,
        media_type=TIPO_XLSX,
        headers={"Content-Disposition": 'attachment; filename="ordens-em-campo.xlsx"'},
    )


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
        _mudar_status(ordem, mudanca.status, mudanca.resultado, mudanca.observacao, usuario.login)
    except TransicaoInvalidaError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    avisar_mudanca_de_ordem(session, [ordem.id])
    session.commit()
    return _como_schema(OrdemDetalheSchema, ordem, limites)
