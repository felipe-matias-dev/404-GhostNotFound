"""O backend espelha o contrato da Gold (contracts/gold_schema.yaml).

O contrato é a fonte de verdade de nomes, tipos, nulidade e chaves. Quando o time de dados
muda o YAML, estes testes apontam o que o backend precisa acompanhar, antes de a carga
falhar com a Gold real.
"""

from datetime import date
from decimal import Decimal
from pathlib import Path
from types import UnionType
from typing import Annotated, Any, Literal, Union, get_args, get_origin

import pytest
import yaml
from sqlalchemy.dialects import postgresql

from venergy_api.carga import GOLD_TABLES, GoldTable

CONTRACT_PATH = Path(__file__).resolve().parents[2] / "contracts" / "gold_schema.yaml"
CONTRACT = yaml.safe_load(CONTRACT_PATH.read_text(encoding="utf-8"))
CONTRACT_TYPES = CONTRACT["conventions"]["types"]
# Tipo Python que o schema usa para cada tipo do contrato. Dinheiro e energia em Decimal,
# nunca float (DEC-010): é o que a carga entrega ao banco.
CONTRACT_PYTHON_TYPES = {
    "text": str,
    "integer": int,
    "boolean": bool,
    "date": date,
    "money": Decimal,
    "energy_kwh": Decimal,
    "ratio": float,
    "text_array": list,
}

# Dependem da Silver: o contrato ainda não define as colunas nem a chave delas.
PENDING_TABLES = {"gold_interrupcoes_uc", "gold_atendimentos_uc", "gold_medidor_uc"}

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


def accepts_none(annotation: object) -> bool:
    return type(None) in get_args(annotation)


def python_type(annotation: object) -> object:
    """Tipo base de um campo do schema, sem o None do opcional e sem as restrições."""
    origin = get_origin(annotation)
    if origin in (Union, UnionType):
        (base,) = [arg for arg in get_args(annotation) if arg is not type(None)]
        return python_type(base)
    if origin is Annotated:
        return python_type(get_args(annotation)[0])
    if origin is Literal:
        return type(get_args(annotation)[0])
    if origin is list:
        return list
    return annotation


def test_pending_tables_are_the_ones_without_a_key_in_the_contract() -> None:
    # Falha quando o time de dados definir a chave de uma pendente: é a hora de o backend
    # implementá-la e tirá-la desta lista.
    without_key = {
        name for name, spec in CONTRACT["tables"].items() if spec["primary_key"] == "a_confirmar"
    }

    assert without_key == PENDING_TABLES


def test_backend_loads_every_contract_table_that_is_not_pending() -> None:
    loaded = {table.model.__tablename__ for table in GOLD_TABLES}

    assert loaded == set(CONTRACT["tables"]) - PENDING_TABLES


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
def test_schema_types_and_nullability_match_the_contract(table: GoldTable) -> None:
    # O schema valida cada linha do CSV antes de ela chegar ao banco: um tipo ou uma
    # nulidade errados ali deixariam passar dado fora do contrato, mesmo com a tabela certa.
    expected = {
        name: (CONTRACT_PYTHON_TYPES[spec["type"]], spec["nullable"])
        for name, spec in contract_columns(table).items()
    }

    assert {
        name: (python_type(field.annotation), accepts_none(field.annotation))
        for name, field in table.schema.model_fields.items()
    } == expected


@backend_tables
def test_allowed_values_match_the_contract(table: GoldTable) -> None:
    fields = table.schema.model_fields
    for name, spec in contract_columns(table).items():
        if "allowed" in spec:
            assert literal_values(fields[name].annotation) == set(spec["allowed"]), name
