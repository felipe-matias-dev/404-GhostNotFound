"""Rotas de receita: a evolução mensal, a comparação entre períodos e a ponte de receita."""

from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Query, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import ColumnElement, case, func, or_, select
from sqlalchemy.orm import InstrumentedAttribute, Session

from venergy_api.agente import RedatorInsightsDep
from venergy_api.database import SessionDep
from venergy_api.insight_receita import metricas_da_receita
from venergy_api.insights import CacheInsightsDep, chave_do_cache
from venergy_api.models import DimUc, FatoFaturamentoMensal, KpisMensais, ReceitaDecomposicao
from venergy_api.schemas import (
    ComparacaoFiltroSchema,
    ComparacaoReceitaSchema,
    DecomposicaoFiltroSchema,
    DecomposicaoLinhaSchema,
    ErroSchema,
    InsightReceitaSchema,
    KpisMensaisSchema,
    ParPeriodosSchema,
    PeriodoSchema,
    TotaisPeriodoSchema,
)

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


def _soma_no_periodo(
    coluna: InstrumentedAttribute[Decimal], no_periodo: ColumnElement[bool]
) -> ColumnElement[Decimal]:
    # CASE dentro do SUM: os dois períodos saem da mesma leitura, numa ida só ao banco.
    # Sem nenhuma linha no período, a soma é zero, e não nula.
    return func.coalesce(func.sum(case((no_periodo, coluna))), 0)


def _variacao_pct(base: Decimal, atual: Decimal) -> float | None:
    if base == 0:
        return None
    return float((atual - base) / base * 100)


@router.get("/comparacao")
def get_comparacao(
    filtro: Annotated[ComparacaoFiltroSchema, Query()], session: SessionDep
) -> ComparacaoReceitaSchema:
    """kWh e receita de dois períodos, da empresa inteira ou de um segmento, e a variação."""
    fato = FatoFaturamentoMensal
    na_base = fato.competencia.between(filtro.base_inicio, filtro.base_fim)
    no_atual = fato.competencia.between(filtro.atual_inicio, filtro.atual_fim)
    consulta = select(
        _soma_no_periodo(fato.kwh_faturado, na_base),
        _soma_no_periodo(fato.receita_faturada, na_base),
        _soma_no_periodo(fato.kwh_faturado, no_atual),
        _soma_no_periodo(fato.receita_faturada, no_atual),
    ).where(or_(na_base, no_atual))

    segmento = [
        (DimUc.municipio, filtro.municipio),
        (DimUc.bairro, filtro.bairro),
        (DimUc.classe, filtro.classe),
    ]
    filtros = [coluna == valor for coluna, valor in segmento if valor is not None]
    if filtros:
        # A fato não tem município, bairro nem classe: eles vêm da dimensão de UCs. Sem
        # filtro, a soma é a da fato pura, a mesma que dá a gold_kpis_mensais.
        consulta = consulta.join(DimUc, DimUc.cod_uc == fato.cod_uc).where(*filtros)

    kwh_base, receita_base, kwh_atual, receita_atual = session.execute(consulta).one()
    return ComparacaoReceitaSchema(
        base=TotaisPeriodoSchema(
            inicio=filtro.base_inicio,
            fim=filtro.base_fim,
            kwh_faturado=kwh_base,
            receita_faturada=receita_base,
        ),
        atual=TotaisPeriodoSchema(
            inicio=filtro.atual_inicio,
            fim=filtro.atual_fim,
            kwh_faturado=kwh_atual,
            receita_faturada=receita_atual,
        ),
        variacao_kwh=kwh_atual - kwh_base,
        variacao_receita=receita_atual - receita_base,
        variacao_kwh_pct=_variacao_pct(kwh_base, kwh_atual),
        variacao_receita_pct=_variacao_pct(receita_base, receita_atual),
    )


@router.get("/decomposicao/periodos")
def get_pares_de_periodos(session: SessionDep) -> list[ParPeriodosSchema]:
    """Os pares de períodos gravados na decomposição: o que o seletor da tela pode oferecer."""
    # Só os pares que a Gold gravou (DEC-028): pares de trechos diferentes não existem lá, e
    # pedir um deles devolveria uma lista vazia sem explicação. Ordem de texto AAAA-MM.
    decomposicao = ReceitaDecomposicao
    consulta = (
        select(decomposicao.periodo_base, decomposicao.periodo_atual)
        .distinct()
        .order_by(decomposicao.periodo_base, decomposicao.periodo_atual)
    )
    return [
        ParPeriodosSchema(periodo_base=base, periodo_atual=atual)
        for base, atual in session.execute(consulta)
    ]


def consultar_decomposicao(
    filtro: DecomposicaoFiltroSchema, session: Session
) -> list[DecomposicaoLinhaSchema]:
    """A ponte do nível abaixo do filtro, da maior queda para a maior alta.

    Fica fora da rota para a tela e o insight de IA lerem exatamente os mesmos números.
    """
    decomposicao = ReceitaDecomposicao
    # O breadcrumb da tela só acrescenta filtros: o nível da resposta é o próximo abaixo.
    if filtro.bairro:
        nivel, coluna = "classe", decomposicao.classe
    elif filtro.municipio:
        nivel, coluna = "bairro", decomposicao.bairro
    else:
        nivel, coluna = "municipio", decomposicao.municipio

    filtros = [
        coluna_filtro == valor
        for coluna_filtro, valor in [
            (decomposicao.periodo_base, filtro.periodo_base),
            (decomposicao.periodo_atual, filtro.periodo_atual),
            (decomposicao.municipio, filtro.municipio),
            (decomposicao.bairro, filtro.bairro),
            (decomposicao.classe, filtro.classe),
        ]
        if valor is not None
    ]
    receita_base = func.sum(decomposicao.receita_base)
    receita_atual = func.sum(decomposicao.receita_atual)
    variacao = receita_atual - receita_base
    consulta = (
        select(
            coluna.label("segmento"),
            decomposicao.periodo_base,
            decomposicao.periodo_atual,
            receita_base.label("receita_base"),
            receita_atual.label("receita_atual"),
            variacao.label("variacao_receita"),
            # Soma dos efeitos já calculados pela Gold, e não o PVM refeito no nível de cima:
            # os efeitos se somam entre segmentos, e preço + volume + mix fecha com a variação
            # dentro da tolerância do contrato (R$ 0,02 por linha somada). Recalcular seria
            # uma fórmula própria do backend.
            func.sum(decomposicao.efeito_preco).label("efeito_preco"),
            func.sum(decomposicao.efeito_tarifa).label("efeito_tarifa"),
            func.sum(decomposicao.efeito_bandeira).label("efeito_bandeira"),
            func.sum(decomposicao.efeito_volume).label("efeito_volume"),
            func.sum(decomposicao.efeito_mix).label("efeito_mix"),
        )
        .where(*filtros)
        # O par de períodos é filtro e também sai na resposta. As linhas com e sem GD do mesmo
        # segmento somam juntas.
        .group_by(decomposicao.periodo_base, decomposicao.periodo_atual, coluna)
        .order_by(decomposicao.periodo_base, decomposicao.periodo_atual, variacao, coluna)
    )
    # Os labels da consulta são os nomes dos campos do schema.
    return [
        DecomposicaoLinhaSchema(nivel=nivel, **linha._mapping)
        for linha in session.execute(consulta)
    ]


@router.get("/decomposicao")
def get_decomposicao(
    filtro: Annotated[DecomposicaoFiltroSchema, Query()], session: SessionDep
) -> list[DecomposicaoLinhaSchema]:
    """Ponte de receita de um par de períodos, por município, por bairro ou por classe.

    Ordenada da maior queda para a maior alta: o topo é onde a receita mais caiu.
    """
    return consultar_decomposicao(filtro, session)


@router.get("/insight", responses={status.HTTP_503_SERVICE_UNAVAILABLE: {"model": ErroSchema}})
async def get_insight(
    filtro: Annotated[DecomposicaoFiltroSchema, Query()],
    session: SessionDep,
    redator: RedatorInsightsDep,
    cache: CacheInsightsDep,
) -> InsightReceitaSchema:
    """Um insight de IA sobre a ponte de receita do recorte que a tela está mostrando."""
    # A sessão do backend é síncrona: a consulta sai do laço de eventos para não travar as
    # outras requisições, como na gravação da auditoria.
    linhas = await run_in_threadpool(consultar_decomposicao, filtro, session)
    metricas = metricas_da_receita(filtro, linhas)
    if metricas is None:
        return InsightReceitaSchema(texto=None, metricas=None)

    chave = chave_do_cache("receita", metricas)
    texto = cache.obter(chave)
    if texto is None:
        insight = await redator.narrate("receita", metricas)
        # None: o redator descartou o texto (número fora das métricas) ou o provedor falhou.
        # A tela aparece sem insight, e a falha não fica no cache.
        if insight is not None:
            texto = insight.text
            cache.guardar(chave, texto)
    return InsightReceitaSchema(texto=texto, metricas=metricas)
