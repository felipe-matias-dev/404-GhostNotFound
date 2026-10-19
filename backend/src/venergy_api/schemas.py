"""Contrato dos dados: o formato que a Gold entrega e que a API devolve."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

RequiredText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class DimUcSchema(BaseModel):
    # Permite montar o schema direto de um objeto do banco (models.DimUc).
    model_config = ConfigDict(from_attributes=True)

    cod_uc: RequiredText
    municipio: RequiredText
    bairro: RequiredText
    classe: Literal["B1", "B2", "B3", "A4"]
    cod_alimentador: RequiredText
    possui_gd: bool
    consumo_medio_kwh_12m: float = Field(ge=0)
