"""Tabelas do banco local, no formato das tabelas Gold."""

from sqlalchemy.orm import Mapped, mapped_column

from venergy_api.database import Base


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
