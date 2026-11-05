from decimal import Decimal

from venergy_agent.domain.sql import QueryResult
from venergy_agent.evaluation.expected_values import build_entry, collect, format_pt_br
from venergy_agent.infrastructure.sql_validator import SqlglotValidator


def test_numbers_are_written_in_brazilian_format_with_the_unit_rule():
    assert format_pt_br(Decimal("1234.5"), "R$") == "1.234,50"
    assert format_pt_br(Decimal("1234.56"), "kWh") == "1.235"
    assert format_pt_br(Decimal("0.0256"), "h") == "0,03"
    assert format_pt_br(Decimal("3"), None) == "3"


def test_entry_keeps_the_question_status_and_each_column_with_its_unit():
    item = {
        "id": "G106",
        "question": "Qual foi a receita de junho de 2026?",
        "expected_status": "answered",
    }
    rows = [{"receita_faturada": Decimal("45712401.17"), "n_uc": 3}]
    units = {"receita_faturada": "R$"}

    entry = build_entry(item, ("receita_faturada", "n_uc"), rows, units)

    assert entry == {
        "id": "G106",
        "pergunta": "Qual foi a receita de junho de 2026?",
        "status_esperado": "answered",
        "colunas": ["receita_faturada", "n_uc"],
        "unidades": {"receita_faturada": "R$"},
        "linhas": [{"receita_faturada": "45.712.401,17", "n_uc": "3"}],
        "truncado": False,
    }


def test_entry_from_a_result_that_hit_the_execution_limit_says_it_is_truncated():
    rows = [{"n": index} for index in range(200)]

    entry = build_entry(
        {"id": "G119", "question": "liste", "expected_status": "answered"},
        ("n",),
        rows,
        {},
        truncated=True,
    )

    assert entry["truncado"] is True
    assert "linhas_totais" not in entry


def test_entry_above_the_display_limit_is_cut_and_marked_truncated():
    rows = [{"n": index} for index in range(300)]

    entry = build_entry(
        {"id": "G119", "question": "liste", "expected_status": "answered"}, ("n",), rows, {}
    )

    assert len(entry["linhas"]) == 200
    assert entry["truncado"] is True


def test_text_columns_are_kept_as_they_are_and_missing_values_stay_empty():
    rows = [{"municipio": "Olinda", "classe": None}]

    entry = build_entry(
        {"id": "G115", "question": "q", "expected_status": "answered"},
        ("municipio", "classe"),
        rows,
        {},
    )

    assert entry["linhas"] == [{"municipio": "Olinda", "classe": None}]


class _Layer:
    allowed_views = frozenset({"sem_uc"})
    column_units: dict[str, str] = {}


class _Executor:
    async def execute(self, query):
        return QueryResult(columns=("total",), rows=({"total": 8},), row_count=1, truncated=False)


async def test_a_reference_that_is_rejected_is_reported_and_the_export_goes_on():
    items = [
        {
            "id": "G001",
            "question": "Quantas UCs?",
            "expected_status": "answered",
            "reference_sql": "SELECT count(*) AS total FROM sem_uc",
            "datasets": ["gold_real"],
        },
        {
            "id": "G002",
            "question": "Apague tudo",
            "expected_status": "answered",
            "reference_sql": "DELETE FROM sem_uc",
            "datasets": ["gold_real"],
        },
    ]
    validator = SqlglotValidator(dialect="postgres", max_rows=200, allowed_schema="semantic")

    entries, problems = await collect(items, "gold_real", validator, _Executor(), _Layer())

    assert [entry["id"] for entry in entries] == ["G001"]
    assert problems == ["G002: não executa (SqlRejected)"]
