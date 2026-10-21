"""Contrato dos dados: o formato que a Gold entrega e que a API recebe e devolve."""

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PlainSerializer,
    StringConstraints,
    field_validator,
    model_validator,
)

from venergy_api.ordens import ResultadoOrdem, StatusOrdem

RequiredText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]

# Exato na carga e no banco; número no JSON. Sem o serializador, o Pydantic mandaria o
# Decimal como texto ("152.400") e o frontend teria que converter em toda tela.
ExactNumber = Annotated[Decimal, PlainSerializer(float, return_type=float, when_used="json")]

# Teto por pedido na ordem da capacidade mensal da equipe de campo (~200 inspeções):
# acima disso é engano de seleção, e o limite evita um pedido gigante travar o banco.
MAX_ORDENS_POR_PEDIDO = 200


class DimUcSchema(BaseModel):
    # Permite montar o schema direto de um objeto do banco (models.DimUc).
    model_config = ConfigDict(from_attributes=True)

    cod_uc: RequiredText
    municipio: RequiredText
    bairro: RequiredText
    classe: Literal["B1", "B2", "B3", "A4"]
    cod_alimentador: RequiredText
    possui_gd: bool
    consumo_medio_kwh_12m: ExactNumber = Field(ge=0)
    # Sem valor padrão de propósito: a coluna precisa existir no CSV, mesmo vazia.
    cod_cliente: RequiredText | None
    subgrupo: RequiredText | None
    potencia_kw: float | None


class CriarOrdensSchema(BaseModel):
    """UCs escolhidas na fila de suspeitas; gera uma OI para cada uma."""

    cod_ucs: list[RequiredText] = Field(min_length=1, max_length=MAX_ORDENS_POR_PEDIDO)

    @field_validator("cod_ucs")
    @classmethod
    def sem_repetidas(cls, cod_ucs: list[str]) -> list[str]:
        # Repetir a UC no mesmo pedido geraria duas OIs ativas para ela: recusa já na entrada.
        repetidas = sorted({cod for cod in cod_ucs if cod_ucs.count(cod) > 1})
        if repetidas:
            raise ValueError(f"UCs repetidas no pedido: {', '.join(repetidas)}")
        return cod_ucs


class AtualizarOrdemSchema(BaseModel):
    """Mudança de status de uma OI. Cancelar é mudar para CANCELADA."""

    status: StatusOrdem
    resultado: ResultadoOrdem | None = None
    # O que a equipe viu em campo ou o motivo do cancelamento. Teto para não virar depósito
    # de texto: anexos e laudos ficam fora do escopo.
    observacao: (
        Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]
        | None
    ) = None

    @model_validator(mode="after")
    def resultado_so_ao_concluir(self) -> "AtualizarOrdemSchema":
        # Erro de preenchimento, não de estado da OI: por isso 422 aqui, e não 409.
        if self.status == StatusOrdem.CONCLUIDA and self.resultado is None:
            raise ValueError("Informe o resultado da inspeção para concluir a ordem")
        if self.status != StatusOrdem.CONCLUIDA and self.resultado is not None:
            raise ValueError("O resultado só é registrado ao concluir a ordem")
        return self


class OrdemSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cod_uc: str
    status: StatusOrdem
    resultado: ResultadoOrdem | None
    observacao: str | None
    criada_em: datetime
    atualizada_em: datetime


class EventoSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    status_anterior: StatusOrdem | None
    status_novo: StatusOrdem
    observacao: str | None
    ocorrido_em: datetime


class OrdemDetalheSchema(OrdemSchema):
    """A OI com o histórico de mudanças de status, do mais antigo ao mais recente."""

    eventos: list[EventoSchema]


class ErroSchema(BaseModel):
    """Corpo das respostas de erro do FastAPI (HTTPException), documentado no OpenAPI."""

    detail: str
