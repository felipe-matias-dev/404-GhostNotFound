"""O backend espelha o contrato da Gold (contracts/gold_schema.yaml).

O contrato é a fonte de verdade de nomes, tipos, nulidade e chaves. Quando o time de dados
muda o YAML, estes testes apontam o que o backend precisa acompanhar, antes de a carga
falhar com a Gold real.
"""

from pathlib import Path
from typing import Any, Literal, get_args, get_origin

import pytest
import yaml
from sqlalchemy.dialects import postgresql

from venergy_api.carga import GOLD_TABLES, GoldTable

CONTRACT_PATH = Path(__file__).resolve().parents[2] / "contracts" / "gold_schema.yaml"
CONTRACT = yaml.safe_load(CONTRACT_PATH.read_text(encoding="utf-8"))
CONTRACT_TYPES = CONTRACT["conventions"]["types"]

backend_tables = pytest.mark.parametrize(
    "table", GOLD_TABLES, ids=[table.model.__tablename__ for table in GOLD_TABLES]
)


def contract_columns(table: GoldTable) -> dict[str, dict[str, Any]]:
    return CONTRACT["tables"][table.model.__tablename__]["columns"]


def normalize_type(sql_type: str) -> str:
    # "NUMERIC(16, 3)" e "numeric(16,3)" são o mesmo tipo. VARCHAR sem tamanho e TEXT
    # também: no Postgres, os dois guardam texto de qualquer tamanho.
    normalized = sql_type.lower().replace(" ", "")
    return "text" if normalized == "varchar" else normalized


def literal_values(annotation: object) -> set[object]:
    """Valores de um Literal, inclusive dentro de um opcional (Literal[...] | None)."""
    if get_origin(annotation) is Literal:
        return set(get_args(annotation))
    return {value for arg in get_args(annotation) for value in literal_values(arg)}


@backend_tables
def test_columns_match_the_contract(table: GoldTable) -> None:
    expected = set(contract_columns(table))

    assert {column.name for column in table.model.__table__.columns} == expected
    # O schema valida cada linha do CSV: uma coluna fora dele seria ignorada na carga.
    assert set(table.schema.model_fields) == expected


@backend_tables
def test_primary_key_matches_the_contract(table: GoldTable) -> None:
    expected = CONTRACT["tables"][table.model.__tablename__]["primary_key"]

    assert [column.name for column in table.model.__table__.primary_key] == expected


@backend_tables
def test_nullability_matches_the_contract(table: GoldTable) -> None:
    columns = table.model.__table__.columns
    expected = {name: spec["nullable"] for name, spec in contract_columns(table).items()}

    assert {column.name: column.nullable for column in columns} == expected


@backend_tables
def test_database_types_match_the_contract(table: GoldTable) -> None:
    dialect = postgresql.dialect()
    expected = {
        name: normalize_type(CONTRACT_TYPES[spec["type"]])
        for name, spec in contract_columns(table).items()
    }

    assert {
        column.name: normalize_type(column.type.compile(dialect=dialect))
        for column in table.model.__table__.columns
    } == expected


@backend_tables
def test_allowed_values_match_the_contract(table: GoldTable) -> None:
    fields = table.schema.model_fields
    for name, spec in contract_columns(table).items():
        if "allowed" in spec:
            assert literal_values(fields[name].annotation) == set(spec["allowed"]), name
