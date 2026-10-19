"""Rotas de unidades consumidoras: a busca que o atendente faz com o número da conta."""

from fastapi import APIRouter, HTTPException, status

from venergy_api.database import SessionDep
from venergy_api.models import DimUc
from venergy_api.schemas import DimUcSchema

router = APIRouter(prefix="/unidades-consumidoras", tags=["unidades consumidoras"])


@router.get("/{cod_uc}")
def get_unidade_consumidora(cod_uc: str, session: SessionDep) -> DimUcSchema:
    # Busca pela chave primária: o SQLAlchemy monta a consulta com parâmetro, sem
    # concatenar o texto digitado no SQL.
    uc = session.get(DimUc, cod_uc)
    if uc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unidade consumidora {cod_uc} não encontrada",
        )
    return DimUcSchema.model_validate(uc)
