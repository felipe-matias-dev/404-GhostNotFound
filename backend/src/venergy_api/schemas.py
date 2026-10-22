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

# Chaves e domínios compartilhados do contrato da Gold (conventions.shared_keys).
# Competência em texto AAAA-MM (DEC-011): não depende de como CSV, Delta e Postgres leem datas.
Competencia = Annotated[str, StringConstraints(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")]
Classe = Literal["B1", "B2", "B3", "A4"]
Bandeira = Literal["verde", "amarela", "vermelha_p1", "vermelha_p2"]

# Teto por pedido na ordem da capacidade mensal da equipe de campo (~200 inspeções):
# acima disso é engano de seleção, e o limite evita um pedido gigante travar o banco.
MAX_ORDENS_POR_PEDIDO = 200


class DimUcSchema(BaseModel):
    # Permite montar o schema direto de um objeto do banco (models.DimUc).
    model_config = ConfigDict(from_attributes=True)

    cod_uc: RequiredText
    municipio: RequiredText
    bairro: RequiredText
    classe: Classe
    cod_alimentador: RequiredText
    possui_gd: bool
    consumo_medio_kwh_12m: ExactNumber = Field(ge=0)
    # Sem valor padrão de propósito: a coluna precisa existir no CSV, mesmo vazia.
    cod_cliente: RequiredText | None
    subgrupo: RequiredText | None
    potencia_kw: float | None


class FaturamentoMensalSchema(BaseModel):
    """Faturamento de uma UC numa competência."""

    cod_uc: RequiredText
    competencia: Competencia
    kwh_faturado: ExactNumber
    receita_faturada: ExactNumber
    receita_arrecadada: ExactNumber | None
    # Vazia quando kwh_faturado é zero (ex.: painel solar compensando todo o consumo).
    tarifa_media: float | None
    bandeira: Bandeira | None


class ReceitaDecomposicaoSchema(BaseModel):
    """Variação da receita entre dois períodos, separada em efeito preço, volume e mix."""

    periodo_base: RequiredText
    periodo_atual: RequiredText
    municipio: RequiredText
    bairro: RequiredText
    classe: Classe
    receita_base: ExactNumber
    receita_atual: ExactNumber
    # Sem limite de sinal: queda de preço ou de volume é efeito negativo.
    efeito_preco: ExactNumber
    efeito_volume: ExactNumber
    efeito_mix: ExactNumber


class KpisMensaisSchema(BaseModel):
    """Indicadores executivos de uma competência."""

    model_config = ConfigDict(from_attributes=True)

    competencia: Competencia
    kwh_faturado: ExactNumber
    receita_faturada: ExactNumber
    dec: float | None
    fec: float | None
    n_chamados: int | None
    satisfacao_media: float | None


def _inicio_ate_o_fim(inicio: str | None, fim: str | None) -> None:
    # Na validação do schema, e não na rota: o erro sai no mesmo formato 422 do formato
    # inválido, e o client do frontend trata um só. Texto AAAA-MM compara na ordem do calendário.
    if inicio and fim and inicio > fim:
        raise ValueError(f"O início do período ({inicio}) é depois do fim ({fim})")


class PeriodoSchema(BaseModel):
    """Recorte de competências, inclusivo nas duas pontas. Sem limites, a série inteira."""

    inicio: Competencia | None = None
    fim: Competencia | None = None

    @model_validator(mode="after")
    def inicio_ate_o_fim(self) -> "PeriodoSchema":
        _inicio_ate_o_fim(self.inicio, self.fim)
        return self


class ComparacaoFiltroSchema(BaseModel):
    """Dois períodos e, se quiser, o segmento: município, bairro e classe."""

    base_inicio: Competencia
    base_fim: Competencia
    atual_inicio: Competencia
    atual_fim: Competencia
    municipio: RequiredText | None = None
    bairro: RequiredText | None = None
    classe: Classe | None = None

    @model_validator(mode="after")
    def periodos_e_segmento_validos(self) -> "ComparacaoFiltroSchema":
        _inicio_ate_o_fim(self.base_inicio, self.base_fim)
        _inicio_ate_o_fim(self.atual_inicio, self.atual_fim)
        # O mesmo nome de bairro pode existir em dois municípios: somar os dois daria um
        # número que ninguém pediu.
        if self.bairro and not self.municipio:
            raise ValueError("Informe o município junto com o bairro")
        return self


class TotaisPeriodoSchema(BaseModel):
    """kWh e receita faturados, somados num período."""

    inicio: Competencia
    fim: Competencia
    kwh_faturado: ExactNumber
    receita_faturada: ExactNumber


class ComparacaoReceitaSchema(BaseModel):
    """Totais de dois períodos e quanto o atual variou sobre a base."""

    base: TotaisPeriodoSchema
    atual: TotaisPeriodoSchema
    variacao_kwh: ExactNumber
    variacao_receita: ExactNumber
    # Em %, vazia quando a base é zero (ex.: bairro sem faturamento no período base): não
    # existe variação percentual sobre nada.
    variacao_kwh_pct: float | None
    variacao_receita_pct: float | None


class ContinuidadeAlimentadorMensalSchema(BaseModel):
    """DEC e FEC de um alimentador numa competência."""

    cod_alimentador: RequiredText
    competencia: Competencia
    dec: float
    fec: float
    n_uc: int
    n_interrupcoes: int
    horas_interrompidas: float


class FilaSuspeitaSchema(BaseModel):
    """Uma UC suspeita de perda não técnica, com o porquê e o quanto vale inspecionar."""

    cod_uc: RequiredText
    score_suspeita: float
    # Motivos legíveis para o gerente de perdas decidir; no CSV, separados por ";".
    motivos: list[RequiredText]
    kwh_recuperavel_est: ExactNumber | None


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
