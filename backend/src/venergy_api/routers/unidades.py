"""Rotas de unidades consumidoras: a busca que o atendente faz com o número da conta."""

from collections.abc import Sequence
from decimal import Decimal

from fastapi import APIRouter, HTTPException, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from venergy_api.agente import RedatorInsightsDep
from venergy_api.consumo_uc import inicio_da_consulta, montar_consumo
from venergy_api.conta_uc import montar_variacao_conta
from venergy_api.database import SessionDep
from venergy_api.insight_uc import metricas_da_uc, texto_aceito
from venergy_api.insights import CacheInsightsDep, narrar
from venergy_api.models import (
    AtendimentoUc,
    DimUc,
    FatoFaturamentoMensal,
    InspecaoUc,
    InterrupcaoUc,
    MedidorUc,
)
from venergy_api.schemas import (
    AtendimentoUcSchema,
    DimUcSchema,
    ErroSchema,
    FaturaNaoPagaSchema,
    FaturasNaoPagasSchema,
    InsightSchema,
    InspecaoUcSchema,
    InterrupcaoUcSchema,
    LocalidadeSchema,
    MedidorUcSchema,
    Uc360Schema,
)

router = APIRouter(prefix="/unidades-consumidoras", tags=["unidades consumidoras"])


def _buscar_uc(session: Session, cod_uc: str) -> DimUc:
    # Busca pela chave primária: o SQLAlchemy monta a consulta com parâmetro, sem
    # concatenar o texto digitado no SQL.
    uc = session.get(DimUc, cod_uc)
    if uc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unidade consumidora {cod_uc} não encontrada",
        )
    return uc


def _faturas_da_janela(
    session: Session, cod_uc: str
) -> tuple[str | None, Sequence[FatoFaturamentoMensal]]:
    """A última competência da Gold e as faturas da UC na janela que termina nela."""
    # A janela termina na última competência da Gold, e não na da própria UC nem no mês de
    # hoje (DEC-044): o dado é uma extração única, e uma UC que parou de faturar não pode
    # passar por "recente" só porque a última fatura dela é a última que ela tem.
    fato = FatoFaturamentoMensal
    referencia = session.scalar(select(func.max(fato.competencia)))
    if referencia is None:
        return None, []
    faturas = session.scalars(
        select(fato).where(
            fato.cod_uc == cod_uc, fato.competencia >= inicio_da_consulta(referencia)
        )
    ).all()
    return referencia, faturas


@router.get("/localidades")
def get_localidades(session: SessionDep) -> list[LocalidadeSchema]:
    localidades = session.execute(
        select(DimUc.municipio, DimUc.bairro).distinct().order_by(DimUc.municipio, DimUc.bairro)
    )
    return [
        LocalidadeSchema(municipio=municipio, bairro=bairro) for municipio, bairro in localidades
    ]


@router.get(
    "/{cod_uc}",
    # Declarado para o client gerado do OpenAPI tipar o erro, e não só o sucesso.
    responses={status.HTTP_404_NOT_FOUND: {"model": ErroSchema}},
)
def get_unidade_consumidora(cod_uc: str, session: SessionDep) -> DimUcSchema:
    return DimUcSchema.model_validate(_buscar_uc(session, cod_uc))


@router.get(
    "/{cod_uc}/visao-360",
    responses={status.HTTP_404_NOT_FOUND: {"model": ErroSchema}},
)
def get_visao_360(cod_uc: str, session: SessionDep) -> Uc360Schema:
    """Cadastro, medidor e histórico da UC: o que o atendente precisa com o cliente na linha."""
    uc = _buscar_uc(session, cod_uc)
    medidor = session.get(MedidorUc, cod_uc)
    fato = FatoFaturamentoMensal
    referencia, faturas = _faturas_da_janela(session, cod_uc)
    # Toda fatura não paga, e não só as dos últimos 12 meses: dívida antiga continua sendo
    # dívida. A situação já vem calculada pela Gold, contra a data de corte (em_aberto ainda
    # no prazo, em_atraso vencida). A mais antiga primeiro, que é a que o cliente deve há mais.
    nao_pagas = session.scalars(
        select(fato)
        .where(fato.cod_uc == cod_uc, fato.status_pagamento.in_(("em_aberto", "em_atraso")))
        .order_by(fato.competencia)
    ).all()
    # Soma em Decimal: em float, 0,10 + 0,20 não dá 0,30 (DEC-010).
    valor_total = sum((fatura.receita_faturada for fatura in nao_pagas), Decimal(0))
    # Todo o histórico, e não só os últimos 12 meses: são poucas linhas por UC (cerca de 4
    # interrupções e 7 chamados em 4 anos) e o atendente precisa do que o cliente já abriu.
    # O desempate pela chave deixa a ordem estável quando duas datas coincidem.
    interrupcoes = session.scalars(
        select(InterrupcaoUc)
        .where(InterrupcaoUc.cod_uc == cod_uc)
        .order_by(InterrupcaoUc.data_abertura.desc(), InterrupcaoUc.cod_ocorrencia)
    )
    atendimentos = session.scalars(
        select(AtendimentoUc)
        .where(AtendimentoUc.cod_uc == cod_uc)
        .order_by(AtendimentoUc.data_abertura.desc(), AtendimentoUc.protocolo)
    )
    inspecoes = session.scalars(
        select(InspecaoUc)
        .where(InspecaoUc.cod_uc == cod_uc)
        .order_by(InspecaoUc.data_inspecao.desc(), InspecaoUc.cod_inspecao)
    )
    return Uc360Schema(
        cadastro=DimUcSchema.model_validate(uc),
        consumo=montar_consumo(referencia, faturas),
        variacao_conta=montar_variacao_conta(referencia, faturas),
        faturas_nao_pagas=FaturasNaoPagasSchema(
            quantidade=len(nao_pagas),
            valor_total=valor_total,
            itens=[FaturaNaoPagaSchema.model_validate(fatura) for fatura in nao_pagas],
        ),
        medidor=MedidorUcSchema.model_validate(medidor) if medidor is not None else None,
        interrupcoes=[InterrupcaoUcSchema.model_validate(item) for item in interrupcoes],
        atendimentos=[AtendimentoUcSchema.model_validate(item) for item in atendimentos],
        inspecoes=[InspecaoUcSchema.model_validate(item) for item in inspecoes],
    )


def consultar_metricas_da_uc(session: Session, cod_uc: str) -> dict[str, object] | None:
    _buscar_uc(session, cod_uc)
    referencia, faturas = _faturas_da_janela(session, cod_uc)
    return metricas_da_uc(
        montar_consumo(referencia, faturas), montar_variacao_conta(referencia, faturas)
    )


@router.get(
    "/{cod_uc}/insight",
    responses={status.HTTP_404_NOT_FOUND: {"model": ErroSchema}},
)
async def get_insight(
    cod_uc: str,
    session: SessionDep,
    redator: RedatorInsightsDep,
    cache: CacheInsightsDep,
) -> InsightSchema:
    """Um insight de IA para o atendente: se o consumo da UC subiu mesmo, e se é de um mês só."""
    # As mesmas contas da visão 360, fora do laço de eventos: a sessão do backend é síncrona.
    metricas = await run_in_threadpool(consultar_metricas_da_uc, session, cod_uc)
    if metricas is None:
        return InsightSchema(texto=None, metricas=None)
    return await narrar(
        "unidade_consumidora",
        metricas,
        redator,
        cache,
        lambda texto, escolhidas: texto_aceito(texto, metricas, escolhidas),
    )
