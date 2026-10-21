from pathlib import Path

import pytest
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session

from venergy_api.amostra import SAMPLE, write_sample
from venergy_api.carga import load_gold
from venergy_api.models import FatoFaturamentoMensal, KpisMensais


def test_generated_sample_passes_the_gold_load(tmp_path: Path, engine: Engine) -> None:
    write_sample(tmp_path / "gold", force=False)

    counts = load_gold(tmp_path / "gold", engine)

    # A carga exige um CSV por tabela da Gold: se faltar amostra de uma, ela falha antes.
    assert counts == {model.__tablename__: len(rows) for model, rows in SAMPLE.items()}


def test_kpis_match_the_sum_of_the_billing_in_the_database(tmp_path: Path, engine: Engine) -> None:
    # A mesma conferência vale para a Gold real: o painel da diretoria tem que bater com a
    # soma do faturamento das UCs, mês a mês, depois de passar por CSV, carga e banco.
    write_sample(tmp_path / "gold", force=False)
    load_gold(tmp_path / "gold", engine)

    with Session(engine) as session:
        billing = session.execute(
            select(
                FatoFaturamentoMensal.competencia,
                func.sum(FatoFaturamentoMensal.kwh_faturado),
                func.sum(FatoFaturamentoMensal.receita_faturada),
            ).group_by(FatoFaturamentoMensal.competencia)
        )
        kpis = session.execute(
            select(KpisMensais.competencia, KpisMensais.kwh_faturado, KpisMensais.receita_faturada)
        )
        assert set(kpis) == set(billing)


def test_does_not_overwrite_existing_csv_without_force(tmp_path: Path) -> None:
    existing = tmp_path / "gold" / "gold_dim_uc.csv"
    existing.parent.mkdir()
    existing.write_text("conteúdo da Gold real", encoding="utf-8")

    with pytest.raises(FileExistsError, match="--force"):
        write_sample(tmp_path / "gold", force=False)

    assert existing.read_text(encoding="utf-8") == "conteúdo da Gold real"
