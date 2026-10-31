"""Rota da fila de suspeitas: de onde o gerente de perdas escolhe as UCs para inspecionar."""

from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy import Integer, and_, any_, case, cast, func, select

from venergy_api.database import SessionDep
from venergy_api.models import DimUc, FilaSuspeita, OrdemInspecao
from venergy_api.ordens import STATUS_ATIVOS
from venergy_api.schemas import (
    DistribuicaoQuedaItemSchema,
    DistribuicaoQuedaSchema,
    FilaFiltroSchema,
    FilaItemSchema,
    FilaPaginaSchema,
    OrdemAtivaSchema,
    RecorteFiltroSchema,
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
    # Junção à esquerda: toda UC da fila aparece, com ou sem ordem. O índice único parcial
    # (no máximo uma OI ativa por UC) garante que a junção não duplica linhas.
    com_ordem_ativa = and_(
        OrdemInspecao.cod_uc == fila.cod_uc, OrdemInspecao.status.in_(STATUS_ATIVOS)
    )
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
        select(fila, OrdemInspecao.id, OrdemInspecao.status, queda)
        .outerjoin(OrdemInspecao, com_ordem_ativa)
        .order_by(ordenacao, fila.score_suspeita, fila.cod_uc)
        .offset((filtro.pagina - 1) * filtro.tamanho)
        .limit(filtro.tamanho)
    )
    predicados = _predicados_recorte(filtro)
    if predicados:
        total_consulta = total_consulta.join(DimUc, DimUc.cod_uc == fila.cod_uc).where(*predicados)
        consulta = consulta.join(DimUc, DimUc.cod_uc == fila.cod_uc).where(*predicados)
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
        )
        for suspeita, ordem_id, ordem_status, valor_queda in session.execute(consulta)
    ]
    return FilaPaginaSchema(
        itens=itens,
        total=session.scalar(total_consulta) or 0,
        pagina=filtro.pagina,
        tamanho=filtro.tamanho,
    )
