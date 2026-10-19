"""Rotas de unidades consumidoras: a busca que o atendente faz com o número da conta."""

from fastapi import APIRouter, HTTPException, status

from venergy_api.database import SessionDep
from venergy_api.models import UcResumo
from venergy_api.schemas import UcResumoSchema

router = APIRouter(prefix="/unidades-consumidoras", tags=["unidades consumidoras"])


@router.get("/{uc_id}")
def get_unidade_consumidora(uc_id: str, session: SessionDep) -> UcResumoSchema:
    # Busca pela chave primária: o SQLAlchemy monta a consulta com parâmetro, sem
    # concatenar o texto digitado no SQL.
    uc = session.get(UcResumo, uc_id)
    if uc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unidade consumidora {uc_id} não encontrada",
        )
    return UcResumoSchema.model_validate(uc)
