"""Rotas de unidades consumidoras: a busca que o atendente faz com o número da conta."""

from fastapi import APIRouter, HTTPException, status
from sqlalchemy.orm import Session

from venergy_api.database import SessionDep
from venergy_api.models import DimUc, MedidorUc
from venergy_api.schemas import DimUcSchema, ErroSchema, MedidorUcSchema, Uc360Schema

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
    return Uc360Schema(
        cadastro=DimUcSchema.model_validate(uc),
        medidor=MedidorUcSchema.model_validate(medidor) if medidor is not None else None,
    )
