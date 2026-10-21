import csv
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import BaseModel
from sqlalchemy import Engine, inspect, select, text
from sqlalchemy.orm import Session

from venergy_api.carga import GoldLoadError, load_gold, read_rows
from venergy_api.models import DimUc

VALID_ROW = {
    "cod_uc": "0001",
    "municipio": "Recife",
    "bairro": "Boa Viagem",
    "classe": "B1",
    "cod_alimentador": "AL-01",
    "possui_gd": "true",
    "consumo_medio_kwh_12m": "152.4",
    "cod_cliente": "C0001",
    "subgrupo": "",
    "potencia_kw": "3.3",
}


def write_gold_dim_uc(gold_dir: Path, rows: list[dict[str, str]]) -> None:
    gold_dir.mkdir(exist_ok=True)
    with (gold_dir / "gold_dim_uc.csv").open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def stored_ucs(engine: Engine) -> list[DimUc]:
    with Session(engine) as session:
        return list(session.scalars(select(DimUc).order_by(DimUc.cod_uc)))


def test_loads_valid_csv_with_typed_values(tmp_path: Path, engine: Engine) -> None:
    write_gold_dim_uc(tmp_path / "gold", [VALID_ROW, {**VALID_ROW, "cod_uc": "0002"}])

    counts = load_gold(tmp_path / "gold", engine)

    assert counts == {"gold_dim_uc": 2}
    first = stored_ucs(engine)[0]
    assert first.cod_uc == "0001"
    assert first.possui_gd is True
    # Decimal com as 3 casas do contrato: somas no banco são exatas, sem resíduo de float.
    assert first.consumo_medio_kwh_12m == Decimal("152.400")


def test_loading_twice_does_not_duplicate_rows(tmp_path: Path, engine: Engine) -> None:
    write_gold_dim_uc(tmp_path / "gold", [VALID_ROW])

    load_gold(tmp_path / "gold", engine)
    load_gold(tmp_path / "gold", engine)

    assert len(stored_ucs(engine)) == 1


def test_reload_recreates_table_with_columns_added_to_the_contract(
    tmp_path: Path, engine: Engine
) -> None:
    # Simula um banco carregado antes de o contrato ganhar uma coluna.
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE gold.gold_dim_uc (cod_uc text PRIMARY KEY)"))
    write_gold_dim_uc(tmp_path / "gold", [VALID_ROW])

    load_gold(tmp_path / "gold", engine)

    columns = {column["name"] for column in inspect(engine).get_columns("gold_dim_uc", "gold")}
    assert "consumo_medio_kwh_12m" in columns
    assert stored_ucs(engine)[0].consumo_medio_kwh_12m == Decimal("152.400")


def test_rejects_csv_with_missing_column(tmp_path: Path, engine: Engine) -> None:
    row_without_classe = {key: value for key, value in VALID_ROW.items() if key != "classe"}
    write_gold_dim_uc(tmp_path / "gold", [row_without_classe])

    with pytest.raises(GoldLoadError, match="colunas faltando: classe"):
        load_gold(tmp_path / "gold", engine)


def test_invalid_row_keeps_previous_data_untouched(tmp_path: Path, engine: Engine) -> None:
    write_gold_dim_uc(tmp_path / "gold", [VALID_ROW])
    load_gold(tmp_path / "gold", engine)
    new_valid_row = {**VALID_ROW, "cod_uc": "0002"}
    invalid_row = {**VALID_ROW, "cod_uc": "0003", "classe": "X9"}
    write_gold_dim_uc(tmp_path / "gold", [new_valid_row, invalid_row])

    with pytest.raises(GoldLoadError, match="linha 3: classe"):
        load_gold(tmp_path / "gold", engine)

    assert [uc.cod_uc for uc in stored_ucs(engine)] == ["0001"]


class OptionalColumnSchema(BaseModel):
    # A gold_dim_uc ainda não tem coluna opcional confirmada no contrato.
    cod_uc: str
    receita: float | None


def test_empty_cell_becomes_none(tmp_path: Path) -> None:
    csv_path = tmp_path / "opcional.csv"
    csv_path.write_text("cod_uc,receita\n0001,\n", encoding="utf-8")

    assert read_rows(csv_path, OptionalColumnSchema) == [{"cod_uc": "0001", "receita": None}]


def test_rejects_empty_required_cell(tmp_path: Path, engine: Engine) -> None:
    write_gold_dim_uc(tmp_path / "gold", [{**VALID_ROW, "bairro": ""}])

    with pytest.raises(GoldLoadError, match="linha 2: bairro"):
        load_gold(tmp_path / "gold", engine)
