"""Tabelas do banco local, no formato das tabelas Gold."""

from sqlalchemy.orm import Mapped, mapped_column

from venergy_api.database import Base


class UcResumo(Base):
    """Resumo de uma unidade consumidora. Formato provisório, proposto ao contrato da Gold."""

    __tablename__ = "uc_resumo"

    # Texto, e não número: o código da UC é um identificador e pode ter zeros à esquerda.
    uc_id: Mapped[str] = mapped_column(primary_key=True)
    municipio: Mapped[str]
    bairro: Mapped[str]
    classe: Mapped[str]
    alimentador: Mapped[str]
    possui_gd: Mapped[bool]
    consumo_medio_kwh_12m: Mapped[float]
