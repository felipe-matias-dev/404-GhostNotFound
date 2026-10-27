import csv
import re
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import BaseModel
from sqlalchemy import Engine, inspect, select, text
from sqlalchemy.orm import Session

from venergy_api import carga
from venergy_api.amostra import write_sample
from venergy_api.carga import AGENT_VIEWS_SQL, GoldLoadError, load_gold, read_rows
from venergy_api.models import DimUc
from venergy_api.schemas import RequiredText

VALID_ROW = {
    "cod_uc": "0001",
    "municipio": "Recife",
    "bairro": "Boa Viagem",
    "classe": "B1",
    "classe_cadastro": "Residencial",
    "cod_alimentador": "AL-01",
    "possui_gd": "true",
    "consumo_medio_kwh_12m": "152.4",
    "titular_mascarado": "M. S.",
    "documento_mascarado": "***.***.**1-23",
    "potencia_kwp": "3.3",
    "data_ligacao": "2018-06-01",
    "data_conexao_gd": "2022-03-15",
    "modalidade_gd": "geracao_propria_uc",
    "energia_injetada_kwh_mes": "396",
}


def write_gold_dim_uc(gold_dir: Path, rows: list[dict[str, str]]) -> None:
    # A carga exige o CSV de todas as tabelas da Gold: as outras vêm da amostra, e só a
    # gold_dim_uc recebe as linhas de cada teste.
    write_sample(gold_dir, force=True)
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

    assert counts["gold_dim_uc"] == 2
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


# As views que o GenAI pôs no views.sql: o teste acompanha o arquivo, e não uma lista à mão.
AGENT_VIEWS = set(
    re.findall(r"CREATE OR REPLACE VIEW gold\.(\w+)", AGENT_VIEWS_SQL.read_text("utf-8"))
)


def gold_views(engine: Engine) -> set[str]:
    with engine.connect() as connection:
        return set(
            connection.scalars(text("SELECT viewname FROM pg_views WHERE schemaname = 'gold'"))
        )


def test_load_creates_the_agent_views(tmp_path: Path, engine: Engine) -> None:
    write_sample(tmp_path / "gold", force=True)

    load_gold(tmp_path / "gold", engine)

    assert AGENT_VIEWS
    assert gold_views(engine) == AGENT_VIEWS


def test_reload_with_the_agent_views_in_place(tmp_path: Path, engine: Engine) -> None:
    # Sem tirar as views antes, o DROP das tabelas falha e o banco fica preso na Gold anterior.
    write_sample(tmp_path / "gold", force=True)
    load_gold(tmp_path / "gold", engine)

    load_gold(tmp_path / "gold", engine)

    assert gold_views(engine) == AGENT_VIEWS


def test_reload_drops_an_agent_view_that_left_the_views_file(
    tmp_path: Path, engine: Engine
) -> None:
    # Uma view renomeada ou removida pelo GenAI continua no banco até a próxima carga.
    write_sample(tmp_path / "gold", force=True)
    load_gold(tmp_path / "gold", engine)
    with engine.begin() as connection:
        connection.execute(
            text("CREATE VIEW gold.sem_antiga AS SELECT cod_uc FROM gold.gold_dim_uc")
        )

    load_gold(tmp_path / "gold", engine)

    assert gold_views(engine) == AGENT_VIEWS


def test_views_that_do_not_match_the_gold_cancel_the_load(
    tmp_path: Path, engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    write_gold_dim_uc(tmp_path / "gold", [VALID_ROW])
    load_gold(tmp_path / "gold", engine)
    # O GenAI ainda não regerou o arquivo depois de uma mudança no contrato.
    stale_views = tmp_path / "views.sql"
    stale_views.write_text(
        "CREATE OR REPLACE VIEW gold.sem_uc AS SELECT coluna_que_saiu FROM gold.gold_dim_uc;",
        encoding="utf-8",
    )
    monkeypatch.setattr(carga, "AGENT_VIEWS_SQL", stale_views)
    write_gold_dim_uc(tmp_path / "gold", [{**VALID_ROW, "cod_uc": "0002"}])

    with pytest.raises(GoldLoadError, match="views do agente não batem com a Gold"):
        load_gold(tmp_path / "gold", engine)

    # Nada mudou: a Gold anterior e as views antigas continuam no banco.
    assert [uc.cod_uc for uc in stored_ucs(engine)] == ["0001"]
    assert gold_views(engine) == AGENT_VIEWS


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


def test_unit_without_reading_loads_with_empty_average(tmp_path: Path, engine: Engine) -> None:
    write_gold_dim_uc(tmp_path / "gold", [{**VALID_ROW, "consumo_medio_kwh_12m": ""}])

    load_gold(tmp_path / "gold", engine)

    assert stored_ucs(engine)[0].consumo_medio_kwh_12m is None


class OptionalColumnSchema(BaseModel):
    # Coluna opcional genérica: a regra da célula vazia vale para qualquer tabela da Gold.
    cod_uc: str
    receita: float | None


def test_empty_cell_becomes_none(tmp_path: Path) -> None:
    csv_path = tmp_path / "opcional.csv"
    csv_path.write_text("cod_uc,receita\n0001,\n", encoding="utf-8")

    assert read_rows(csv_path, OptionalColumnSchema) == [{"cod_uc": "0001", "receita": None}]


class ListColumnSchema(BaseModel):
    # Mesmo formato dos motivos da fila de suspeitas: text[] no contrato.
    cod_uc: str
    motivos: list[RequiredText]


def test_list_cell_is_split_by_semicolon(tmp_path: Path) -> None:
    csv_path = tmp_path / "lista.csv"
    csv_path.write_text("cod_uc,motivos\n0001,consumo caiu;medidor antigo\n", encoding="utf-8")

    assert read_rows(csv_path, ListColumnSchema) == [
        {"cod_uc": "0001", "motivos": ["consumo caiu", "medidor antigo"]}
    ]


def test_rejects_empty_item_in_list_cell(tmp_path: Path) -> None:
    # Dois ; seguidos é erro de exportação: a carga avisa em vez de descartar o item vazio.
    csv_path = tmp_path / "lista.csv"
    csv_path.write_text("cod_uc,motivos\n0001,consumo caiu;;medidor antigo\n", encoding="utf-8")

    with pytest.raises(GoldLoadError, match="linha 2: motivos.1"):
        read_rows(csv_path, ListColumnSchema)


def test_rejects_empty_required_cell(tmp_path: Path, engine: Engine) -> None:
    write_gold_dim_uc(tmp_path / "gold", [{**VALID_ROW, "bairro": ""}])

    with pytest.raises(GoldLoadError, match="linha 2: bairro"):
        load_gold(tmp_path / "gold", engine)


@pytest.mark.parametrize(
    ("column", "valid", "invalid"),
    [
        ("periodo_base", "2024-01/2024-01", "2024-13/2024-13"),
        ("periodo_atual", "2025-01/2025-01", "2025-13/2025-13"),
    ],
)
def test_rejects_decomposition_period_outside_the_contract_format(
    tmp_path: Path, engine: Engine, column: str, valid: str, invalid: str
) -> None:
    # Um par mal escrito passaria pela carga e derrubaria a rota de pares com 500: a carga
    # é o lugar de recusá-lo.
    write_sample(tmp_path / "gold", force=True)
    csv_path = tmp_path / "gold" / "gold_receita_decomposicao.csv"
    csv_path.write_text(
        csv_path.read_text(encoding="utf-8").replace(valid, invalid, 1), encoding="utf-8"
    )

    with pytest.raises(GoldLoadError, match=column):
        load_gold(tmp_path / "gold", engine)
