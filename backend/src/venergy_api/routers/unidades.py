"""Rotas de unidades consumidoras: a busca que o atendente faz com o número da conta."""

from decimal import Decimal

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from venergy_api.database import SessionDep
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
    InspecaoUcSchema,
    InterrupcaoUcSchema,
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
    # Toda fatura não paga, e não só as dos últimos 12 meses: dívida antiga continua sendo
    # dívida. A situação já vem calculada pela Gold, contra a data de corte (em_aberto ainda
    # no prazo, em_atraso vencida). A mais antiga primeiro, que é a que o cliente deve há mais.
    fato = FatoFaturamentoMensal
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
