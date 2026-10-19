import csv
from pathlib import Path

import pytest
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from venergy_api.carga import GoldLoadError, load_gold
from venergy_api.models import UcResumo

VALID_ROW = {
    "uc_id": "0001",
    "municipio": "Recife",
    "bairro": "Boa Viagem",
    "classe": "B1",
    "alimentador": "AL-01",
    "possui_gd": "true",
    "consumo_medio_kwh_12m": "152.4",
}


def write_uc_resumo(gold_dir: Path, rows: list[dict[str, str]]) -> None:
    gold_dir.mkdir(exist_ok=True)
    with (gold_dir / "uc_resumo.csv").open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def stored_ucs(engine: Engine) -> list[UcResumo]:
    with Session(engine) as session:
        return list(session.scalars(select(UcResumo).order_by(UcResumo.uc_id)))


def test_loads_valid_csv_with_typed_values(tmp_path: Path, engine: Engine) -> None:
    write_uc_resumo(tmp_path / "gold", [VALID_ROW, {**VALID_ROW, "uc_id": "0002"}])

    counts = load_gold(tmp_path / "gold", engine)

    assert counts == {"uc_resumo": 2}
    first = stored_ucs(engine)[0]
    assert first.uc_id == "0001"
    assert first.possui_gd is True
    assert first.consumo_medio_kwh_12m == 152.4


def test_loading_twice_does_not_duplicate_rows(tmp_path: Path, engine: Engine) -> None:
    write_uc_resumo(tmp_path / "gold", [VALID_ROW])

    load_gold(tmp_path / "gold", engine)
    load_gold(tmp_path / "gold", engine)

    assert len(stored_ucs(engine)) == 1


def test_rejects_csv_with_missing_column(tmp_path: Path, engine: Engine) -> None:
    row_without_classe = {key: value for key, value in VALID_ROW.items() if key != "classe"}
    write_uc_resumo(tmp_path / "gold", [row_without_classe])

    with pytest.raises(GoldLoadError, match="colunas faltando: classe"):
        load_gold(tmp_path / "gold", engine)


def test_invalid_row_keeps_previous_data_untouched(tmp_path: Path, engine: Engine) -> None:
    write_uc_resumo(tmp_path / "gold", [VALID_ROW])
    load_gold(tmp_path / "gold", engine)
    new_valid_row = {**VALID_ROW, "uc_id": "0002"}
    invalid_row = {**VALID_ROW, "uc_id": "0003", "classe": "X9"}
    write_uc_resumo(tmp_path / "gold", [new_valid_row, invalid_row])

    with pytest.raises(GoldLoadError, match="linha 3: classe"):
        load_gold(tmp_path / "gold", engine)

    assert [uc.uc_id for uc in stored_ucs(engine)] == ["0001"]
