import re

from venergy_agent.config import AGENT_ROOT
from venergy_agent.infrastructure.views_sql import main, render_views_sql

COMMITTED = AGENT_ROOT / "semantic" / "views.sql"


def test_committed_views_sql_matches_the_layer_and_the_contract():
    assert COMMITTED.read_text(encoding="utf-8") == render_views_sql()


def test_check_mode_passes_on_the_committed_file():
    assert main(["--check"]) == 0


def test_every_view_is_created_in_the_gold_schema():
    sql = render_views_sql()

    for name in ("sem_uc", "sem_faturamento_mensal", "sem_continuidade_alimentador_mensal"):
        assert f"CREATE OR REPLACE VIEW semantic.{name} AS" in sql


def test_column_marked_a_confirmar_never_reaches_the_view():
    assert "cod_cliente" not in render_views_sql()
    assert "subgrupo" not in render_views_sql()
    assert not re.search(r"\bpotencia_kw\b", render_views_sql())


def test_views_read_from_the_gold_tables():
    sql = render_views_sql()

    assert "FROM gold.gold_dim_uc;" in sql
    assert "FROM gold.gold_fato_faturamento_mensal;" in sql
    assert "FROM gold.gold_continuidade_alimentador_mensal;" in sql


def test_integer_counts_reach_the_views_as_numeric_so_a_division_never_truncates():
    sql = render_views_sql()

    assert "CAST(n_uc AS numeric) AS n_uc" in sql
    assert "CAST(n_interrupcoes AS numeric) AS n_interrupcoes" in sql
    assert "CAST(kwh_faturado AS numeric)" not in sql


def test_day_counts_stay_integer_so_they_can_still_be_added_to_a_date():
    sql = render_views_sql()

    for dias in ("dias_em_atraso", "dias_faturados", "soma_dias_em_atraso"):
        assert f"CAST({dias} AS numeric)" not in sql
        assert f"{dias}," in sql or f"{dias}\n" in sql
