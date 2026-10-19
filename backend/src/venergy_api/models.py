"""Tabelas do banco local, no formato das tabelas Gold."""

from sqlalchemy.orm import Mapped, mapped_column

from venergy_api.database import Base


class DimUc(Base):
    """Dimensão de unidades consumidoras, uma linha por UC. Colunas provisórias até o contrato."""

    __tablename__ = "gold_dim_uc"

    # Texto, e não número: o código da UC é um identificador e pode ter zeros à esquerda.
    cod_uc: Mapped[str] = mapped_column(primary_key=True)
    municipio: Mapped[str]
    bairro: Mapped[str]
    classe: Mapped[str]
    cod_alimentador: Mapped[str]
    possui_gd: Mapped[bool]
    consumo_medio_kwh_12m: Mapped[float]
