"""Rotas de receita: a evolução mensal, a comparação entre períodos e a ponte de receita."""

from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy import ColumnElement, case, func, or_, select
from sqlalchemy.orm import InstrumentedAttribute

from venergy_api.database import SessionDep
from venergy_api.models import DimUc, FatoFaturamentoMensal, KpisMensais, ReceitaDecomposicao
from venergy_api.schemas import (
    ComparacaoFiltroSchema,
    ComparacaoReceitaSchema,
    DecomposicaoFiltroSchema,
    DecomposicaoLinhaSchema,
    KpisMensaisSchema,
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


@router.get("/decomposicao")
def get_decomposicao(
    filtro: Annotated[DecomposicaoFiltroSchema, Query()], session: SessionDep
) -> list[DecomposicaoLinhaSchema]:
    """Ponte de receita por município, por bairro de um município ou por classe de um bairro.

    Ordenada da maior queda para a maior alta: o topo é onde a receita mais caiu.
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
            # os efeitos se somam entre segmentos, e preço + volume + mix continua fechando
            # com a variação. Recalcular seria uma fórmula própria do backend.
            func.sum(decomposicao.efeito_preco).label("efeito_preco"),
            func.sum(decomposicao.efeito_volume).label("efeito_volume"),
            func.sum(decomposicao.efeito_mix).label("efeito_mix"),
        )
        .where(*filtros)
        # O par de períodos entra no agrupamento: se a Gold trouxer mais de um par, cada
        # comparação sai separada, em vez de somar anos que não se comparam.
        .group_by(decomposicao.periodo_base, decomposicao.periodo_atual, coluna)
        .order_by(decomposicao.periodo_base, decomposicao.periodo_atual, variacao, coluna)
    )
    # Os labels da consulta são os nomes dos campos do schema.
    return [
        DecomposicaoLinhaSchema(nivel=nivel, **linha._mapping)
        for linha in session.execute(consulta)
    ]
