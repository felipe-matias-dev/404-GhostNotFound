"""Rotas de indicadores: os da diretoria em dois períodos e em janelas corridas."""

from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy import (
    ColumnElement,
    Double,
    Integer,
    and_,
    case,
    cast,
    distinct,
    func,
    or_,
    select,
)
from sqlalchemy.orm import InstrumentedAttribute

from venergy_api.database import SessionDep
from venergy_api.indices import indices
from venergy_api.models import KpisMensais
from venergy_api.models import KpisSegmentoMensal as Segmento
from venergy_api.schemas import (
    ComparacaoIndicadoresSchema,
    IndicadoresComparacaoFiltroSchema,
    IndicadoresJanelaSchema,
    IndicadoresJanelasFiltroSchema,
    IndicadoresMensaisFiltroSchema,
    IndicadoresMensalSchema,
    IndicadoresPeriodoSchema,
    VariacaoIndicadoresSchema,
)

router = APIRouter(prefix="/indicadores", tags=["indicadores"])


def _recorte(
    municipio: str | None, bairro: str | None, classe: str | None
) -> list[ColumnElement[bool]]:
    return [
        coluna == valor
        for coluna, valor in [
            (Segmento.municipio, municipio),
            (Segmento.bairro, bairro),
            (Segmento.classe, classe),
        ]
        if valor is not None
    ]


def _meses_no_calendario(inicio: str, fim: str) -> int:
    ano_inicio, mes_inicio = map(int, inicio.split("-"))
    ano_fim, mes_fim = map(int, fim.split("-"))
    return (ano_fim - ano_inicio) * 12 + mes_fim - mes_inicio + 1


def _razao(numerador: ColumnElement, denominador: ColumnElement) -> ColumnElement:
    return cast(numerador / func.nullif(denominador, 0), Double)


def _indicadores(inicio: str, fim: str) -> dict[str, ColumnElement]:
    """Os indicadores de um período, como expressões agregadas da tabela de segmentos."""
    no_periodo = Segmento.competencia.between(inicio, fim)

    def soma(coluna: ColumnElement | InstrumentedAttribute) -> ColumnElement:
        return func.sum(coluna).filter(no_periodo)

    def total(coluna: ColumnElement | InstrumentedAttribute) -> ColumnElement:
        return func.coalesce(soma(coluna), 0)

    # Meses e última competência são lidos na tabela inteira, sem o recorte: um bairro sem
    # linha num mês conta 0 UC nesse mês, em vez de sumir do divisor.
    n_meses = select(func.count(distinct(Segmento.competencia))).where(no_periodo).scalar_subquery()
    ultima = select(func.max(Segmento.competencia)).where(no_periodo).scalar_subquery()
    kwh = soma(Segmento.kwh_faturado)
    colunas = {
        c.key: c
        for c in indices(
            Segmento.horas_interrompidas,
            Segmento.n_interrupcoes,
            Segmento.n_uc,
            n_meses,
            no_periodo,
        )
    }
    return {
        "n_meses": n_meses,
        "receita_faturada": total(Segmento.receita_faturada),
        "receita_energia": total(Segmento.receita_energia),
        "tributos": total(Segmento.tributos),
        "kwh_faturado": total(Segmento.kwh_faturado),
        "n_uc_medio": colunas["n_uc_medio"].element,
        "n_uc_fim": func.coalesce(
            func.sum(Segmento.n_uc).filter(Segmento.competencia == ultima), 0
        ),
        "tarifa_media": _razao(soma(Segmento.receita_energia), kwh),
        "tarifa_base_media": _razao(
            soma(Segmento.receita_energia - Segmento.receita_bandeira), kwh
        ),
        "horas_interrompidas": colunas["horas_interrompidas"].element,
        "n_interrupcoes": colunas["n_interrupcoes"].element,
        "dec": colunas["dec"].element,
        "fec": colunas["fec"].element,
        "n_chamados": total(Segmento.n_chamados),
        "n_notas": total(Segmento.n_notas),
        "satisfacao_media": _razao(soma(Segmento.soma_notas), soma(Segmento.n_notas)),
    }


def _soma_com_fatura(soma: ColumnElement) -> ColumnElement:
    """A soma só vale no recorte com fatura; sem ela, nula e não zero (DEC-030)."""
    return case((func.sum(Segmento.n_faturas) > 0, soma))


@router.get("/mensal")
def get_mensal(
    filtro: Annotated[IndicadoresMensaisFiltroSchema, Query()], session: SessionDep
) -> list[IndicadoresMensalSchema]:
    """Série mensal do recorte; mês sem fato no recorte vem nulo, e não zero (DEC-030)."""
    calendario = select(Segmento.competencia).distinct().subquery()
    agregacao = (
        select(
            Segmento.competencia,
            _soma_com_fatura(func.sum(Segmento.kwh_faturado)).label("kwh_faturado"),
            _soma_com_fatura(func.sum(Segmento.receita_faturada)).label("receita_faturada"),
            _soma_com_fatura(func.sum(Segmento.receita_energia)).label("receita_energia"),
            func.sum(Segmento.n_chamados).label("n_chamados"),
            _razao(func.sum(Segmento.soma_notas), func.sum(Segmento.n_notas)).label(
                "satisfacao_media"
            ),
            *indices(Segmento.horas_interrompidas, Segmento.n_interrupcoes, Segmento.n_uc, 1),
        )
        .where(*_recorte(filtro.municipio, filtro.bairro, filtro.classe))
        .group_by(Segmento.competencia)
        .subquery()
    )
    # O mês sem linha no recorte continua na série, com as somas nulas: o buraco fica visível,
    # e não vira zero (DEC-030).
    consulta = (
        select(
            calendario.c.competencia,
            agregacao.c.kwh_faturado,
            agregacao.c.receita_faturada,
            agregacao.c.receita_energia,
            case((KpisMensais.n_chamados.is_not(None), agregacao.c.n_chamados)).label("n_chamados"),
            agregacao.c.dec,
            agregacao.c.fec,
            agregacao.c.satisfacao_media,
        )
        .outerjoin(agregacao, calendario.c.competencia == agregacao.c.competencia)
        .outerjoin(KpisMensais, calendario.c.competencia == KpisMensais.competencia)
    )
    if filtro.inicio:
        consulta = consulta.where(calendario.c.competencia >= filtro.inicio)
    if filtro.fim:
        consulta = consulta.where(calendario.c.competencia <= filtro.fim)
    return [
        IndicadoresMensalSchema(**linha._mapping)
        for linha in session.execute(consulta.order_by(calendario.c.competencia))
    ]


@router.get("/comparacao")
def get_comparacao(
    filtro: Annotated[IndicadoresComparacaoFiltroSchema, Query()], session: SessionDep
) -> ComparacaoIndicadoresSchema:
    """Os indicadores da diretoria em dois períodos, da empresa inteira ou de um recorte."""
    base = _indicadores(filtro.base_inicio, filtro.base_fim)
    atual = _indicadores(filtro.atual_inicio, filtro.atual_fim)
    # Variação em % calculada no banco, sobre as mesmas expressões. Nula com base zero e com mês
    # faltando em um dos lados: 6 meses contra 12 pareceria uma queda de 50% que não existiu.
    completos = and_(
        base["n_meses"] == _meses_no_calendario(filtro.base_inicio, filtro.base_fim),
        atual["n_meses"] == _meses_no_calendario(filtro.atual_inicio, filtro.atual_fim),
    )
    variacao = {
        nome: case(
            (
                completos,
                cast((atual[nome] - base[nome]) / func.nullif(base[nome], 0) * 100, Double),
            )
        )
        for nome in VariacaoIndicadoresSchema.model_fields
    }
    colunas = [
        *(expr.label(f"base_{nome}") for nome, expr in base.items()),
        *(expr.label(f"atual_{nome}") for nome, expr in atual.items()),
        *(expr.label(f"variacao_{nome}") for nome, expr in variacao.items()),
    ]
    na_base = Segmento.competencia.between(filtro.base_inicio, filtro.base_fim)
    no_atual = Segmento.competencia.between(filtro.atual_inicio, filtro.atual_fim)
    consulta = (
        select(*colunas)
        .where(or_(na_base, no_atual))
        .where(*_recorte(filtro.municipio, filtro.bairro, filtro.classe))
    )
    linha = session.execute(consulta).one()._mapping

    def periodo(prefixo: str, inicio: str, fim: str) -> IndicadoresPeriodoSchema:
        valores = {k.removeprefix(prefixo): v for k, v in linha.items() if k.startswith(prefixo)}
        return IndicadoresPeriodoSchema(inicio=inicio, fim=fim, **valores)

    return ComparacaoIndicadoresSchema(
        base=periodo("base_", filtro.base_inicio, filtro.base_fim),
        atual=periodo("atual_", filtro.atual_inicio, filtro.atual_fim),
        variacao_pct=VariacaoIndicadoresSchema(
            **{
                k.removeprefix("variacao_"): v
                for k, v in linha.items()
                if k.startswith("variacao_")
            }
        ),
    )


@router.get("/janelas")
def get_janelas(
    filtro: Annotated[IndicadoresJanelasFiltroSchema, Query()], session: SessionDep
) -> list[IndicadoresJanelaSchema]:
    """Janelas corridas de `meses` competências, da mais antiga para a mais recente."""
    meses = filtro.meses
    competencias = select(Segmento.competencia).distinct().cte("competencias")
    recorte_mensal = (
        select(
            Segmento.competencia,
            func.sum(Segmento.receita_faturada).label("receita_faturada"),
            func.sum(Segmento.receita_energia).label("receita_energia"),
            func.sum(Segmento.receita_energia - Segmento.receita_bandeira).label("energia_base"),
            func.sum(Segmento.kwh_faturado).label("kwh_faturado"),
            func.sum(Segmento.n_uc).label("n_uc"),
        )
        .where(*_recorte(filtro.municipio, filtro.bairro, filtro.classe))
        .group_by(Segmento.competencia)
        .cte("recorte_mensal")
    )
    mensal = (
        select(
            competencias.c.competencia,
            *(
                func.coalesce(coluna, 0).label(coluna.key)
                for coluna in recorte_mensal.c
                if coluna.key != "competencia"
            ),
        )
        .outerjoin(
            recorte_mensal,
            recorte_mensal.c.competencia == competencias.c.competencia,
        )
        .cte("mensal")
    )
    # n_uc é estoque: dentro de cada mês soma recortes, e a janela só o soma para dividir por
    # `meses`. A janela é por posição na série, e o filtro de baixo descarta as que têm buraco.
    frame = {"order_by": mensal.c.competencia, "rows": (-(meses - 1), 0)}

    def na_janela(coluna: ColumnElement) -> ColumnElement:
        return func.sum(coluna).over(**frame)

    janelas = select(
        func.min(mensal.c.competencia).over(**frame).label("inicio"),
        mensal.c.competencia.label("fim"),
        func.count().over(**frame).label("n"),
        na_janela(mensal.c.receita_faturada).label("receita_faturada"),
        na_janela(mensal.c.receita_energia).label("receita_energia"),
        na_janela(mensal.c.energia_base).label("energia_base"),
        na_janela(mensal.c.kwh_faturado).label("kwh_faturado"),
        na_janela(mensal.c.n_uc).label("soma_uc"),
    ).cte("janelas")
    inicio_esperado = func.to_char(
        func.to_date(janelas.c.fim + "-01", "YYYY-MM-DD")
        - func.make_interval(0, cast(meses - 1, Integer)),
        "YYYY-MM",
    )
    consulta = (
        select(
            janelas.c.inicio,
            janelas.c.fim,
            janelas.c.receita_faturada,
            janelas.c.receita_energia,
            janelas.c.kwh_faturado,
            cast(janelas.c.soma_uc, Double) / meses,
            _razao(janelas.c.receita_energia, janelas.c.kwh_faturado),
            _razao(janelas.c.energia_base, janelas.c.kwh_faturado),
        )
        .where(janelas.c.n == meses, janelas.c.inicio == inicio_esperado)
        .order_by(janelas.c.fim)
    )
    return [
        IndicadoresJanelaSchema(
            inicio=inicio,
            fim=fim,
            receita_faturada=receita,
            receita_energia=energia,
            kwh_faturado=kwh,
            n_uc_medio=n_uc_medio,
            tarifa_media=tarifa,
            tarifa_base_media=tarifa_base,
        )
        for inicio, fim, receita, energia, kwh, n_uc_medio, tarifa, tarifa_base in session.execute(
            consulta
        )
    ]
