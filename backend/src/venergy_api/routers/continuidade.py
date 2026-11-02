"""Rotas de continuidade: DEC e FEC por alimentador e recorte, a série mensal e as ocorrências."""

from typing import Annotated, Any

from fastapi import APIRouter, Query
from sqlalchemy import (
    ColumnElement,
    Double,
    Select,
    cast,
    distinct,
    func,
    or_,
    select,
)
from sqlalchemy.orm import InstrumentedAttribute, Session

from venergy_api.database import SessionDep
from venergy_api.indices import indices
from venergy_api.models import (
    ContinuidadeAlimentadorMensal,
    DimUc,
    InterrupcaoUc,
    KpisSegmentoMensal,
)
from venergy_api.schemas import (
    ContinuidadeAlimentadorMensalSchema,
    ContinuidadeMensalFiltroSchema,
    ContinuidadeMensalSchema,
    ContinuidadeSerieFiltroSchema,
    DuracaoOcorrenciasSchema,
    GrupoOcorrenciasSchema,
    IndicesContinuidadeSchema,
    OcorrenciasFiltroSchema,
    RankingAlimentadorSchema,
    RankingContinuidadeSchema,
    RankingFiltroSchema,
    RecorteContinuidadeSchema,
    RecortesContinuidadeSchema,
    RecortesFiltroSchema,
    ResumoOcorrenciasFiltroSchema,
    ResumoOcorrenciasSchema,
    TotalOcorrenciasSchema,
    UcAtingidaSchema,
    UcsAtingidasFiltroSchema,
    UcsAtingidasSchema,
    VariacaoContinuidadeSchema,
)
from venergy_api.variacao import meses_no_calendario

router = APIRouter(prefix="/continuidade", tags=["continuidade"])

Tabela = type[ContinuidadeAlimentadorMensal] | type[KpisSegmentoMensal]


def contar_meses(
    session: Session, competencia: InstrumentedAttribute[str], inicio: str, fim: str
) -> int:
    """Meses com dado no período, na tabela inteira: o divisor da média mensal de UCs."""
    # Contados sem o filtro do recorte, para um bairro sem linha num mês contar 0 UC nesse
    # mês, e não sumir do divisor. Texto AAAA-MM compara na ordem do calendário (DEC-011).
    consulta = select(func.count(distinct(competencia))).where(competencia.between(inicio, fim))
    return session.scalar(consulta) or 0


def _pior_primeiro(criterio: str, colunas: list[ColumnElement]) -> list[ColumnElement]:
    # Pelo índice escolhido e, no empate, pelo outro. Nulo (sem UC atendida) vai para o fim.
    dec, fec = colunas[0], colunas[1]
    principal, secundario = (dec, fec) if criterio == "dec" else (fec, dec)
    return [principal.desc().nulls_last(), secundario.desc().nulls_last()]


def _recorte_segmento(
    municipio: str | None, bairro: str | None, classe: str | None
) -> list[ColumnElement[bool]]:
    tabela = KpisSegmentoMensal
    return [
        coluna == valor
        for coluna, valor in [
            (tabela.municipio, municipio),
            (tabela.bairro, bairro),
            (tabela.classe, classe),
        ]
        if valor is not None
    ]


def _indices_por_linha(
    session: Session,
    tabela: Tabela,
    chaves: list[InstrumentedAttribute[str]],
    filtros: list[ColumnElement[bool]],
    filtro: RankingFiltroSchema,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Índices do período atual por linha e, com base, os da base e a variação de cada linha.

    Os dois períodos saem da mesma leitura, com a mesma conta de `indices()` filtrada por
    período (FILTER), como em /indicadores/comparacao. Devolve o envelope do período base e
    as linhas, do pior para o melhor no período atual.
    """
    no_atual = tabela.competencia.between(filtro.inicio, filtro.fim)
    n_meses = contar_meses(session, tabela.competencia, filtro.inicio, filtro.fim)
    componentes = (tabela.horas_interrompidas, tabela.n_interrupcoes, tabela.n_uc)
    atual = indices(*componentes, n_meses, no_atual)
    colunas: list[ColumnElement] = [*chaves, *atual]
    periodo = no_atual
    envelope: dict[str, Any] = {"n_meses": n_meses}
    com_base = filtro.base_inicio is not None and filtro.base_fim is not None
    if com_base:
        na_base = tabela.competencia.between(filtro.base_inicio, filtro.base_fim)
        n_meses_base = contar_meses(
            session, tabela.competencia, filtro.base_inicio, filtro.base_fim
        )
        base = {c.key: c.element for c in indices(*componentes, n_meses_base, na_base)}
        colunas += [expr.label(f"base_{nome}") for nome, expr in base.items()]
        colunas.append(func.count().filter(na_base).label("linhas_base"))
        # Variação nula com mês faltando em um dos lados (DEC-054): 6 meses contra 12
        # pareceria uma queda de 50% que não existiu. Com base zero ou nula, nula também.
        completos = n_meses == meses_no_calendario(
            filtro.inicio, filtro.fim
        ) and n_meses_base == meses_no_calendario(filtro.base_inicio, filtro.base_fim)
        if completos:
            do_atual = {c.key: c.element for c in atual}
            colunas += [
                cast(
                    (do_atual[nome] - base[nome]) / func.nullif(base[nome], 0) * 100, Double
                ).label(f"variacao_{nome}")
                for nome in VariacaoContinuidadeSchema.model_fields
            ]
        periodo = or_(no_atual, na_base)
        envelope |= {
            "base_inicio": filtro.base_inicio,
            "base_fim": filtro.base_fim,
            "n_meses_base": n_meses_base,
        }
    # Soma os componentes das linhas do filtro e só então divide: DEC de recorte não é média
    # dos DEC dos alimentadores (DEC-021). Linha só da base não entra: o ranking é do atual.
    consulta = (
        select(*colunas)
        .where(periodo, *filtros)
        .group_by(*chaves)
        .having(func.count().filter(no_atual) > 0)
        .order_by(*_pior_primeiro(filtro.criterio, atual), *chaves)
    )
    linhas = []
    for linha in session.execute(consulta):
        valores = dict(linha._mapping)
        saida = {k: v for k, v in valores.items() if not k.startswith(("base_", "variacao_"))}
        saida.pop("linhas_base", None)
        if com_base:
            saida["base"] = (
                IndicesContinuidadeSchema(
                    **{
                        k.removeprefix("base_"): v
                        for k, v in valores.items()
                        if k.startswith("base_")
                    }
                )
                if valores["linhas_base"]
                else None
            )
            saida["variacao_pct"] = VariacaoContinuidadeSchema(
                **{
                    nome: valores.get(f"variacao_{nome}")
                    for nome in VariacaoContinuidadeSchema.model_fields
                }
            )
        linhas.append(saida)
    return envelope, linhas


@router.get("/alimentadores/mensal")
def get_serie_alimentadores(
    filtro: Annotated[ContinuidadeSerieFiltroSchema, Query()], session: SessionDep
) -> list[ContinuidadeAlimentadorMensalSchema]:
    """DEC e FEC de cada alimentador por competência, como a Gold calculou."""
    # Os índices mensais são lidos da Gold, e não refeitos: o mês é o grão dela.
    tabela = ContinuidadeAlimentadorMensal
    consulta = select(tabela).order_by(tabela.cod_alimentador, tabela.competencia)
    if filtro.inicio:
        consulta = consulta.where(tabela.competencia >= filtro.inicio)
    if filtro.fim:
        consulta = consulta.where(tabela.competencia <= filtro.fim)
    if filtro.cod_alimentador:
        consulta = consulta.where(tabela.cod_alimentador.in_(filtro.cod_alimentador))
    return [
        ContinuidadeAlimentadorMensalSchema.model_validate(linha, from_attributes=True)
        for linha in session.scalars(consulta)
    ]


@router.get("/alimentadores/ranking")
def get_ranking_alimentadores(
    filtro: Annotated[RankingFiltroSchema, Query()], session: SessionDep
) -> RankingContinuidadeSchema:
    """Os piores alimentadores do período, pelo DEC ou pelo FEC, no recorte escolhido."""
    # Sem recorte, a tabela por alimentador da Gold; com recorte, a de segmentos agregada por
    # alimentador. A conta é a mesma, e sem recorte as duas dão o mesmo índice.
    tabela: Tabela = KpisSegmentoMensal if filtro.com_recorte else ContinuidadeAlimentadorMensal
    filtros = _recorte_segmento(filtro.municipio, filtro.bairro, filtro.classe)
    envelope, linhas = _indices_por_linha(
        session, tabela, [tabela.cod_alimentador], filtros, filtro
    )
    return RankingContinuidadeSchema(
        inicio=filtro.inicio,
        fim=filtro.fim,
        criterio=filtro.criterio,
        **envelope,
        alimentadores=[RankingAlimentadorSchema(**linha) for linha in linhas],
    )


@router.get("/recortes")
def get_recortes(
    filtro: Annotated[RecortesFiltroSchema, Query()], session: SessionDep
) -> RecortesContinuidadeSchema:
    """DEC e FEC por município, por bairro ou por alimentador, dentro do filtro."""
    tabela = KpisSegmentoMensal
    # O breadcrumb da tela só acrescenta filtros: o nível padrão é o próximo abaixo, como em
    # /receita/decomposicao. Com `nivel=bairro` sem município, a lista plana de todos os
    # bairros, cada um com o seu município (o nome se repete entre municípios).
    nivel = filtro.nivel_da_resposta
    chaves: list[InstrumentedAttribute[str]]
    if nivel == "alimentador":
        chaves = [tabela.cod_alimentador]
    elif nivel == "bairro":
        chaves = [tabela.bairro, tabela.municipio]
    else:
        chaves = [tabela.municipio]
    filtros = _recorte_segmento(filtro.municipio, filtro.bairro, filtro.classe)
    envelope, linhas = _indices_por_linha(session, tabela, chaves, filtros, filtro)

    def recorte(linha: dict[str, Any]) -> RecorteContinuidadeSchema:
        segmento = linha.pop(chaves[0].key)
        municipio = linha.pop("municipio") if nivel == "bairro" else None
        return RecorteContinuidadeSchema(segmento=segmento, municipio=municipio, **linha)

    return RecortesContinuidadeSchema(
        inicio=filtro.inicio,
        fim=filtro.fim,
        criterio=filtro.criterio,
        nivel=nivel,
        **envelope,
        recortes=[recorte(linha) for linha in linhas],
    )


@router.get("/mensal")
def get_mensal(
    filtro: Annotated[ContinuidadeMensalFiltroSchema, Query()], session: SessionDep
) -> list[ContinuidadeMensalSchema]:
    """DEC e FEC do recorte, ou de um alimentador dentro dele, em cada competência."""
    tabela = KpisSegmentoMensal
    filtros = _recorte_segmento(filtro.municipio, filtro.bairro, filtro.classe)
    if filtro.cod_alimentador:
        filtros.append(tabela.cod_alimentador == filtro.cod_alimentador)
    no_periodo = tabela.competencia.between(filtro.inicio, filtro.fim)
    calendario = select(tabela.competencia).where(no_periodo).distinct().subquery()
    agregacao = (
        select(
            tabela.competencia,
            *indices(tabela.horas_interrompidas, tabela.n_interrupcoes, tabela.n_uc, 1),
            func.sum(tabela.n_uc).label("n_uc"),
        )
        .where(no_periodo, *filtros)
        .group_by(tabela.competencia)
        .subquery()
    )
    # O mês sem linha no recorte continua na série, com as somas nulas: o buraco fica visível,
    # e não vira zero (DEC-030).
    consulta = (
        select(
            calendario.c.competencia,
            agregacao.c.dec,
            agregacao.c.fec,
            agregacao.c.horas_interrompidas,
            agregacao.c.n_interrupcoes,
            agregacao.c.n_uc,
        )
        .outerjoin(agregacao, calendario.c.competencia == agregacao.c.competencia)
        .order_by(calendario.c.competencia)
    )
    return [ContinuidadeMensalSchema(**linha._mapping) for linha in session.execute(consulta)]


def _ocorrencias(filtro: OcorrenciasFiltroSchema, *colunas: Any) -> Select:
    """As ocorrências do período no recorte, que vem do cadastro da UC (gold_dim_uc)."""
    ocorrencia = InterrupcaoUc
    filtros = [
        coluna == valor
        for coluna, valor in [
            (DimUc.municipio, filtro.municipio),
            (DimUc.bairro, filtro.bairro),
            (DimUc.classe, filtro.classe),
            (ocorrencia.cod_alimentador, filtro.cod_alimentador),
        ]
        if valor is not None
    ]
    # LEFT JOIN: a chave estrangeira do contrato é lógica, e uma UC fora do cadastro não some
    # das contagens sem recorte; com recorte geográfico ou de classe, ela fica fora.
    return (
        select(*colunas)
        .select_from(ocorrencia)
        .outerjoin(DimUc, DimUc.cod_uc == ocorrencia.cod_uc)
        .where(ocorrencia.competencia.between(filtro.inicio, filtro.fim), *filtros)
    )


def _horas(coluna: ColumnElement) -> ColumnElement:
    return func.coalesce(func.sum(coluna), 0.0)


@router.get("/ocorrencias/resumo")
def get_resumo_ocorrencias(
    filtro: Annotated[ResumoOcorrenciasFiltroSchema, Query()], session: SessionDep
) -> ResumoOcorrenciasSchema:
    """Por que a luz cai: causas, tipos, UCs atingidas e reincidentes e a duração."""
    ocorrencia = InterrupcaoUc
    duracao = ocorrencia.duracao_horas
    por_uc = (
        _ocorrencias(filtro, ocorrencia.cod_uc, func.count().label("n"))
        .group_by(ocorrencia.cod_uc)
        .subquery()
    )
    reincidentes = session.scalar(
        select(func.count()).select_from(por_uc).where(por_uc.c.n >= filtro.reincidencia_min)
    )
    total = (
        session.execute(
            _ocorrencias(
                filtro,
                func.count().label("n_interrupcoes"),
                _horas(duracao).label("horas_interrompidas"),
                func.count(distinct(ocorrencia.cod_uc)).label("ucs_atingidas"),
                func.percentile_cont(0.5).within_group(duracao).label("mediana_h"),
                func.percentile_cont(0.9).within_group(duracao).label("p90_h"),
                func.max(duracao).label("maxima_h"),
                func.count().filter(duracao >= filtro.longa_h).label("n_longas"),
            )
        )
        .one()
        ._mapping
    )

    def grupos(coluna: InstrumentedAttribute) -> list[GrupoOcorrenciasSchema]:
        horas = _horas(duracao)
        consulta = (
            _ocorrencias(
                filtro,
                coluna.label("nome"),
                func.count().label("n_interrupcoes"),
                horas.label("horas_interrompidas"),
            )
            .group_by(coluna)
            .order_by(horas.desc(), coluna.asc().nulls_last())
        )
        return [GrupoOcorrenciasSchema(**linha._mapping) for linha in session.execute(consulta)]

    return ResumoOcorrenciasSchema(
        inicio=filtro.inicio,
        fim=filtro.fim,
        reincidencia_min=filtro.reincidencia_min,
        longa_h=filtro.longa_h,
        total=TotalOcorrenciasSchema(
            n_interrupcoes=total["n_interrupcoes"],
            horas_interrompidas=total["horas_interrompidas"],
            ucs_atingidas=total["ucs_atingidas"],
            ucs_reincidentes=reincidentes or 0,
        ),
        por_causa=grupos(ocorrencia.causa),
        por_tipo=grupos(ocorrencia.tipo),
        duracao=DuracaoOcorrenciasSchema(
            mediana_h=total["mediana_h"],
            p90_h=total["p90_h"],
            maxima_h=total["maxima_h"],
            n_longas=total["n_longas"],
        ),
    )


@router.get("/ocorrencias/ucs")
def get_ucs_atingidas(
    filtro: Annotated[UcsAtingidasFiltroSchema, Query()], session: SessionDep
) -> UcsAtingidasSchema:
    """As UCs mais atingidas no período e no recorte, das mais horas para as menos."""
    ocorrencia = InterrupcaoUc
    horas = _horas(ocorrencia.duracao_horas)
    consulta = _ocorrencias(
        filtro,
        ocorrencia.cod_uc,
        DimUc.municipio,
        DimUc.bairro,
        func.count().label("n_interrupcoes"),
        horas.label("horas_interrompidas"),
        func.max(ocorrencia.duracao_horas).label("maior_duracao_h"),
        func.count().over().label("total"),
    ).group_by(ocorrencia.cod_uc, DimUc.municipio, DimUc.bairro)
    pagina = session.execute(
        consulta.order_by(horas.desc(), func.count().desc(), ocorrencia.cod_uc)
        .limit(filtro.tamanho)
        .offset((filtro.pagina - 1) * filtro.tamanho)
    ).all()
    # Página além da última: o total vem de uma contagem à parte, para não voltar zero.
    total = (
        pagina[0].total
        if pagina
        else session.scalar(select(func.count()).select_from(consulta.subquery())) or 0
    )
    return UcsAtingidasSchema(
        pagina=filtro.pagina,
        tamanho=filtro.tamanho,
        total=total,
        ucs=[
            UcAtingidaSchema(**{k: v for k, v in linha._mapping.items() if k != "total"})
            for linha in pagina
        ],
    )
