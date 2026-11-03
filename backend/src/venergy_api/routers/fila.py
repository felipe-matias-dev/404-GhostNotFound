"""Rota da fila de suspeitas: de onde o gerente de perdas escolhe as UCs para inspecionar."""

from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy import Date, Integer, and_, any_, case, cast, func, literal, or_, select, union_all
from sqlalchemy.dialects.postgresql import distinct_on

from venergy_api.database import SessionDep
from venergy_api.models import DimUc, FilaSuspeita, InspecaoUc, OrdemEvento, OrdemInspecao
from venergy_api.ordens import STATUS_ATIVOS, ResultadoOrdem, StatusOrdem
from venergy_api.schemas import (
    AcertoInspecoesSchema,
    DistribuicaoQuedaItemSchema,
    DistribuicaoQuedaSchema,
    FilaFiltroSchema,
    FilaItemSchema,
    FilaPaginaSchema,
    IndicadoresPerdasSchema,
    OrdemAtivaSchema,
    RecorteFilaSchema,
    RecorteFiltroSchema,
    RecortesFilaFiltroSchema,
    RecortesFilaSchema,
    UltimaInspecaoSchema,
)

router = APIRouter(prefix="/fila-suspeitas", tags=["fila de suspeitas"])


def queda_percentual():
    texto = func.substring(
        func.array_to_string(FilaSuspeita.motivos, "; "),
        r"Queda de ([0-9]{1,3})% no consumo médio",
    )
    numero = cast(texto, Integer)
    return case((numero.between(0, 100), numero), else_=None)


def leituras_estimadas_percentual():
    texto = func.substring(
        func.array_to_string(FilaSuspeita.motivos, "; "),
        r"(?:^|; )([0-9]{1,3})% das leituras das 12 últimas competências foram estimadas(?:; |$)",
    )
    numero = cast(texto, Integer)
    return case((numero.between(0, 100), numero), else_=None)


def _predicados_recorte(filtro: RecorteFiltroSchema):
    return [
        coluna == valor
        for coluna, valor in (
            (DimUc.municipio, filtro.municipio),
            (DimUc.bairro, filtro.bairro),
            (DimUc.classe, filtro.classe),
        )
        if valor is not None
    ]


# O portal é usado em Pernambuco: o dia da conclusão é o do relógio de lá, e não o do servidor.
FUSO_DO_PORTAL = "America/Recife"


def _ultima_inspecao():
    """A inspeção mais recente de cada UC, da Gold ou concluída no portal.

    NAO_REALIZADA não conta: a equipe não chegou a vistoriar. No empate de datas entre as duas
    fontes vale o portal, que é o registro mais novo do mesmo dia.
    """
    gold = select(
        InspecaoUc.cod_uc.label("cod_uc"),
        InspecaoUc.data_inspecao.label("data"),
        InspecaoUc.resultado.label("resultado"),
        literal("gold").label("origem"),
        literal(0).label("prioridade"),
    )
    conclusao = (
        select(
            OrdemEvento.ordem_id.label("ordem_id"),
            func.max(OrdemEvento.ocorrido_em).label("ocorrido_em"),
        )
        .where(OrdemEvento.status_novo == StatusOrdem.CONCLUIDA)
        .group_by(OrdemEvento.ordem_id)
        .subquery()
    )
    portal = (
        select(
            OrdemInspecao.cod_uc,
            cast(func.timezone(FUSO_DO_PORTAL, conclusao.c.ocorrido_em), Date),
            case(
                (
                    OrdemInspecao.resultado == ResultadoOrdem.IRREGULAR_CONFIRMADA,
                    "irregularidade_confirmada",
                ),
                else_="sem_irregularidade",
            ),
            literal("portal"),
            literal(1),
        )
        .join(conclusao, conclusao.c.ordem_id == OrdemInspecao.id)
        .where(
            OrdemInspecao.status == StatusOrdem.CONCLUIDA,
            OrdemInspecao.resultado.in_(
                [ResultadoOrdem.IRREGULAR_CONFIRMADA, ResultadoOrdem.REGULAR]
            ),
        )
    )
    todas = union_all(gold, portal).subquery("inspecoes_uc")
    return (
        select(todas.c.cod_uc, todas.c.data, todas.c.resultado, todas.c.origem)
        .ext(distinct_on(todas.c.cod_uc))
        .order_by(todas.c.cod_uc, todas.c.data.desc(), todas.c.prioridade.desc())
        .subquery("ultima_inspecao")
    )


def _com_ordem_ativa():
    # Junção à esquerda: toda UC da fila aparece, com ou sem ordem. O índice único parcial
    # (no máximo uma OI ativa por UC) garante que a junção não duplica linhas.
    return and_(
        OrdemInspecao.cod_uc == FilaSuspeita.cod_uc, OrdemInspecao.status.in_(STATUS_ATIVOS)
    )


@router.get("/indicadores")
def get_indicadores(
    filtro: Annotated[RecorteFiltroSchema, Query()], session: SessionDep
) -> IndicadoresPerdasSchema:
    """Suspeitas, ordens e o acerto das inspeções (portal e Gold) no recorte pedido."""
    predicados = _predicados_recorte(filtro)

    suspeitas = (
        select(
            func.count(),
            func.count().filter(OrdemInspecao.id.is_(None)),
            func.sum(FilaSuspeita.kwh_recuperavel_est).filter(OrdemInspecao.id.is_(None)),
        )
        .select_from(FilaSuspeita)
        .outerjoin(OrdemInspecao, _com_ordem_ativa())
    )
    ordens = select(
        func.count().filter(OrdemInspecao.status == StatusOrdem.GERADA),
        func.count().filter(OrdemInspecao.status == StatusOrdem.EM_CAMPO),
    )
    portal = select(
        func.count(),
        func.count().filter(OrdemInspecao.resultado == ResultadoOrdem.IRREGULAR_CONFIRMADA),
        func.count().filter(OrdemInspecao.resultado == ResultadoOrdem.REGULAR),
        func.count().filter(OrdemInspecao.resultado == ResultadoOrdem.NAO_REALIZADA),
        func.coalesce(func.sum(OrdemInspecao.kwh_recuperado), 0),
    ).where(OrdemInspecao.status == StatusOrdem.CONCLUIDA)
    gold = select(
        func.count(),
        func.count().filter(InspecaoUc.resultado == "irregularidade_confirmada"),
        func.count().filter(InspecaoUc.resultado == "sem_irregularidade"),
        literal(0),
        func.coalesce(func.sum(InspecaoUc.kwh_recuperado), 0),
    )
    if predicados:
        suspeitas = suspeitas.join(DimUc, DimUc.cod_uc == FilaSuspeita.cod_uc).where(*predicados)
        ordens = ordens.join(DimUc, DimUc.cod_uc == OrdemInspecao.cod_uc).where(*predicados)
        portal = portal.join(DimUc, DimUc.cod_uc == OrdemInspecao.cod_uc).where(*predicados)
        gold = gold.join(DimUc, DimUc.cod_uc == InspecaoUc.cod_uc).where(*predicados)

    total, sem_ordem, kwh_sem_ordem = session.execute(suspeitas).one()
    geradas, em_campo = session.execute(ordens).one()
    return IndicadoresPerdasSchema(
        suspeitas=total,
        suspeitas_sem_ordem_ativa=sem_ordem,
        kwh_recuperavel_est_sem_ordem=kwh_sem_ordem,
        ordens_geradas=geradas,
        ordens_em_campo=em_campo,
        portal=_acerto(*session.execute(portal).one()),
        gold=_acerto(*session.execute(gold).one()),
    )


def _acerto(inspecoes, irregulares, regulares, nao_realizadas, kwh_recuperado):
    decididas = irregulares + regulares
    return AcertoInspecoesSchema(
        inspecoes=inspecoes,
        irregulares=irregulares,
        regulares=regulares,
        nao_realizadas=nao_realizadas,
        taxa_irregularidade=irregulares / decididas if decididas else None,
        kwh_recuperado=kwh_recuperado,
    )


@router.get("/recortes")
def get_recortes(
    filtro: Annotated[RecortesFilaFiltroSchema, Query()], session: SessionDep
) -> RecortesFilaSchema:
    """Suspeitas por município ou bairro, para o mapa; o bairro leva o município junto."""
    nivel = filtro.nivel_da_resposta
    segmento = DimUc.bairro if nivel == "bairro" else DimUc.municipio
    colunas = [segmento, DimUc.municipio] if nivel == "bairro" else [segmento]
    kwh = func.sum(FilaSuspeita.kwh_recuperavel_est)
    consulta = (
        select(
            *colunas,
            func.count(),
            func.count().filter(OrdemInspecao.id.is_(None)),
            kwh,
        )
        .select_from(FilaSuspeita)
        .join(DimUc, DimUc.cod_uc == FilaSuspeita.cod_uc)
        .outerjoin(OrdemInspecao, _com_ordem_ativa())
        .where(*_predicados_recorte(filtro))
        .group_by(*colunas)
        .order_by(kwh.desc().nulls_last(), func.count().desc(), segmento)
    )
    return RecortesFilaSchema(
        nivel=nivel,
        recortes=[
            RecorteFilaSchema(
                segmento=linha[0],
                municipio=linha[1] if nivel == "bairro" else None,
                suspeitas=linha[-3],
                suspeitas_sem_ordem_ativa=linha[-2],
                kwh_recuperavel_est=linha[-1],
            )
            for linha in session.execute(consulta)
        ],
    )


@router.get("/distribuicao-queda")
def get_distribuicao_queda(
    filtro: Annotated[RecorteFiltroSchema, Query()], session: SessionDep
) -> DistribuicaoQuedaSchema:
    queda = queda_percentual()
    consulta = select(queda, func.count()).group_by(queda)
    predicados = _predicados_recorte(filtro)
    if predicados:
        consulta = consulta.join(DimUc, DimUc.cod_uc == FilaSuspeita.cod_uc).where(*predicados)
    rows = session.execute(consulta).all()
    return DistribuicaoQuedaSchema(
        itens=[
            DistribuicaoQuedaItemSchema(queda=valor, total=total)
            for valor, total in rows
            if valor is not None
        ],
        sem_queda_identificada=sum(total for valor, total in rows if valor is None),
    )


@router.get("")
def get_fila(filtro: Annotated[FilaFiltroSchema, Query()], session: SessionDep) -> FilaPaginaSchema:
    """A fila da mais para a menos suspeita, com a ordem ativa de cada UC."""
    queda = queda_percentual()
    fila = FilaSuspeita
    com_ordem_ativa = _com_ordem_ativa()
    ultima = _ultima_inspecao()
    total_consulta = (
        select(func.count()).select_from(fila).outerjoin(OrdemInspecao, com_ordem_ativa)
    )
    coluna = {
        "prioridade": fila.score_suspeita,
        "energia": fila.kwh_recuperavel_est,
        "ordem_ativa": OrdemInspecao.id.is_not(None),
        "queda": queda,
    }[filtro.ordenar_por]
    ordenacao = coluna.asc() if filtro.direcao == "asc" else coluna.desc()
    if filtro.ordenar_por in ("energia", "queda"):
        ordenacao = ordenacao.nulls_last()
    consulta = (
        select(
            fila,
            OrdemInspecao.id,
            OrdemInspecao.status,
            queda,
            ultima.c.data,
            ultima.c.resultado,
            ultima.c.origem,
        )
        .outerjoin(OrdemInspecao, com_ordem_ativa)
        .outerjoin(ultima, ultima.c.cod_uc == fila.cod_uc)
        .order_by(ordenacao, fila.score_suspeita, fila.cod_uc)
        .offset((filtro.pagina - 1) * filtro.tamanho)
        .limit(filtro.tamanho)
    )
    predicados = _predicados_recorte(filtro)
    if predicados:
        total_consulta = total_consulta.join(DimUc, DimUc.cod_uc == fila.cod_uc).where(*predicados)
        consulta = consulta.join(DimUc, DimUc.cod_uc == fila.cod_uc).where(*predicados)
    if filtro.sem_inspecao_meses is not None:
        limite = cast(func.current_date() - func.make_interval(0, filtro.sem_inspecao_meses), Date)
        recente = or_(ultima.c.data.is_(None), ultima.c.data < limite)
        total_consulta = total_consulta.outerjoin(ultima, ultima.c.cod_uc == fila.cod_uc).where(
            recente
        )
        consulta = consulta.where(recente)
    if filtro.sem_ordem_ativa:
        total_consulta = total_consulta.where(OrdemInspecao.id.is_(None))
        consulta = consulta.where(OrdemInspecao.id.is_(None))
    if filtro.queda_min is not None:
        total_consulta = total_consulta.where(queda >= filtro.queda_min)
        consulta = consulta.where(queda >= filtro.queda_min)
    if filtro.queda_max is not None:
        total_consulta = total_consulta.where(queda <= filtro.queda_max)
        consulta = consulta.where(queda <= filtro.queda_max)
    if filtro.medidor_eletromecanico:
        medidor = any_(fila.motivos) == "Medidor eletromecânico"
        total_consulta = total_consulta.where(medidor)
        consulta = consulta.where(medidor)
    if filtro.leituras_estimadas_min is not None or filtro.leituras_estimadas_max is not None:
        estimadas = leituras_estimadas_percentual()
        total_consulta = total_consulta.where(estimadas >= 25)
        consulta = consulta.where(estimadas >= 25)
        if filtro.leituras_estimadas_min is not None:
            total_consulta = total_consulta.where(estimadas >= filtro.leituras_estimadas_min)
            consulta = consulta.where(estimadas >= filtro.leituras_estimadas_min)
        if filtro.leituras_estimadas_max is not None:
            total_consulta = total_consulta.where(estimadas <= filtro.leituras_estimadas_max)
            consulta = consulta.where(estimadas <= filtro.leituras_estimadas_max)

    itens = [
        FilaItemSchema(
            cod_uc=suspeita.cod_uc,
            score_suspeita=suspeita.score_suspeita,
            motivos=suspeita.motivos,
            queda_percentual=valor_queda,
            kwh_recuperavel_est=suspeita.kwh_recuperavel_est,
            ordem_ativa=(
                OrdemAtivaSchema(id=ordem_id, status=ordem_status) if ordem_id is not None else None
            ),
            ultima_inspecao=(
                UltimaInspecaoSchema(data=data, resultado=resultado, origem=origem)
                if data is not None
                else None
            ),
        )
        for (
            suspeita,
            ordem_id,
            ordem_status,
            valor_queda,
            data,
            resultado,
            origem,
        ) in session.execute(consulta)
    ]
    return FilaPaginaSchema(
        itens=itens,
        total=session.scalar(total_consulta) or 0,
        pagina=filtro.pagina,
        tamanho=filtro.tamanho,
    )
