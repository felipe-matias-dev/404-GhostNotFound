"""Tabelas do banco local: as da Gold (só leitura) e as da aplicação (ordens de inspeção)."""

from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum, ForeignKey, Index, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from venergy_api.database import Base
from venergy_api.ordens import STATUS_ATIVOS, ResultadoOrdem, StatusOrdem


class DimUc(Base):
    """Dimensão de unidades consumidoras, uma linha por UC. Colunas provisórias até o contrato."""

    __tablename__ = "gold_dim_uc"
    # Schema gold: recarregável a partir dos CSVs e o único que o agente de IA consegue ler.
    __table_args__ = {"schema": "gold"}

    # Texto, e não número: o código da UC é um identificador e pode ter zeros à esquerda.
    cod_uc: Mapped[str] = mapped_column(primary_key=True)
    municipio: Mapped[str]
    bairro: Mapped[str]
    classe: Mapped[str]
    cod_alimentador: Mapped[str]
    possui_gd: Mapped[bool]
    consumo_medio_kwh_12m: Mapped[float]


def _enum_como_texto(enum: type[StrEnum], nome_check: str) -> Enum:
    # VARCHAR com CHECK, e não ENUM nativo do Postgres: sem migrações, acrescentar um valor
    # a um ENUM nativo exige ALTER TYPE à mão; o CHECK é recriado junto com a tabela.
    # O nome é explícito porque o padrão vem do enum, e duas colunas com o mesmo enum na
    # mesma tabela gerariam dois CHECK com o mesmo nome, que o Postgres recusa.
    return Enum(enum, name=nome_check, native_enum=False, create_constraint=True, length=30)


# Valores fixos do código, nunca entrada de usuário: montar o SQL do índice com eles é seguro.
_FILTRO_ATIVAS = "status IN ({})".format(", ".join(f"'{s}'" for s in sorted(STATUS_ATIVOS)))


class OrdemInspecao(Base):
    """Pedido de vistoria em campo para uma UC, gerado pelo gerente de perdas a partir da fila."""

    __tablename__ = "ordem_inspecao"
    __table_args__ = (
        # No máximo uma OI ativa por UC: evita mandar duas equipes ao mesmo imóvel. Fica no
        # banco, e não só no Python, para valer também com dois cliques simultâneos.
        Index(
            "uq_ordem_inspecao_uc_ativa",
            "cod_uc",
            unique=True,
            postgresql_where=text(_FILTRO_ATIVAS),
        ),
        # Schema app: dados digitados no portal. O loader da Gold nunca apaga este schema.
        {"schema": "app"},
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    # Sem chave estrangeira para gold_dim_uc: a carga da Gold apaga e reinsere as UCs, e uma
    # FK travaria a carga ou apagaria as OIs junto. A existência da UC é checada na API.
    cod_uc: Mapped[str] = mapped_column(index=True)
    status: Mapped[StatusOrdem] = mapped_column(
        _enum_como_texto(StatusOrdem, "ck_ordem_inspecao_status"), default=StatusOrdem.GERADA
    )
    resultado: Mapped[ResultadoOrdem | None] = mapped_column(
        _enum_como_texto(ResultadoOrdem, "ck_ordem_inspecao_resultado")
    )
    observacao: Mapped[str | None]
    criada_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    atualizada_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    eventos: Mapped[list["OrdemEvento"]] = relationship(
        back_populates="ordem", order_by="OrdemEvento.id"
    )


class OrdemEvento(Base):
    """Uma mudança de status de uma OI: o histórico de quem passou por onde e quando."""

    __tablename__ = "ordem_evento"
    __table_args__ = {"schema": "app"}

    id: Mapped[int] = mapped_column(primary_key=True)
    ordem_id: Mapped[int] = mapped_column(ForeignKey("app.ordem_inspecao.id"), index=True)
    # Vazio no evento de criação, quando a OI ainda não tinha status.
    status_anterior: Mapped[StatusOrdem | None] = mapped_column(
        _enum_como_texto(StatusOrdem, "ck_ordem_evento_status_anterior")
    )
    status_novo: Mapped[StatusOrdem] = mapped_column(
        _enum_como_texto(StatusOrdem, "ck_ordem_evento_status_novo")
    )
    observacao: Mapped[str | None]
    ocorrido_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    ordem: Mapped[OrdemInspecao] = relationship(back_populates="eventos")
