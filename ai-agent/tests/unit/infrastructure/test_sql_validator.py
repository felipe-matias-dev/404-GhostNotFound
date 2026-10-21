import pytest

from venergy_agent.domain.errors import SqlRejected
from venergy_agent.infrastructure.sql_validator import SqlglotValidator

ALLOWED = frozenset({"sem_uc", "sem_faturamento_mensal"})


@pytest.fixture
def validator():
    return SqlglotValidator(dialect="postgres", max_rows=200, allowed_schema="gold")


@pytest.mark.parametrize(
    "sql",
    [
        "DROP TABLE sem_uc",
        "DELETE FROM sem_uc",
        "UPDATE sem_uc SET municipio = 'X'",
        "INSERT INTO sem_uc (cod_uc) VALUES ('1')",
        "CREATE TABLE x (a int)",
        "ALTER TABLE sem_uc ADD COLUMN y int",
        "TRUNCATE sem_uc",
        "SET search_path TO gold",
        "COPY sem_uc TO '/tmp/x'",
        "SELECT 1; DROP TABLE sem_uc",
        "SELECT * FROM sem_uc; DELETE FROM sem_uc",
        "WITH x AS (DELETE FROM sem_uc RETURNING *) SELECT * FROM x",
        "WITH x AS (INSERT INTO sem_uc (cod_uc) VALUES ('1') RETURNING *) SELECT * FROM x",
        "SELECT pg_read_file('/etc/passwd')",
        "SELECT pg_sleep(60)",
        "SELECT set_config('search_path', 'x', false)",
        "SELECT dblink('host=x', 'select 1')",
        "SELECT * FROM gold_dim_uc",
        "SELECT * FROM app.ordem_inspecao",
        "SELECT * FROM otherdb.gold.sem_uc",
        "SELECT * FROM sem_uc WHERE cod_uc IN (SELECT cod_uc FROM tabela_secreta)",
        "SELECT * FROM sem_uc LIMIT 'x'",
        "",
        "   ",
        "SELEC * FROM sem_uc",
        "SELECT * FROM gold_dim_uc WHERE EXISTS "
        "(WITH gold_dim_uc AS (SELECT 1) SELECT 1 FROM gold_dim_uc)",
        "SELECT query_to_xml('select * from gold.gold_dim_uc', true, true, '')",
        "SELECT table_to_xml('gold.gold_dim_uc', true, true, '')",
        "SELECT * FROM sem_uc, LATERAL query_to_xml('select 1', true, true, '') x",
        "SELECT current_setting('search_path')",
        "SELECT version()",
        "SELECT current_user",
        "SELECT current_database()",
        "SELECT current_schema",
        "SELECT current_catalog",
        "SELECT session_user",
        "SELECT * FROM sem_uc FOR UPDATE",
        "SELECT * FROM sem_uc FOR SHARE",
        "SELECT * INTO sem_uc FROM sem_faturamento_mensal",
    ],
)
def test_rejects_unsafe_or_invalid_sql(validator, sql):
    with pytest.raises(SqlRejected):
        validator.validate(sql, ALLOWED)


def test_fetch_first_is_rejected_asking_for_limit(validator):
    with pytest.raises(SqlRejected, match="FETCH.*LIMIT"):
        validator.validate("SELECT cod_uc FROM sem_uc FETCH FIRST 5000 ROWS ONLY", ALLOWED)


def test_accepts_common_date_and_text_functions(validator):
    query = validator.validate(
        "SELECT date_trunc('month', f.competencia), extract(year FROM f.competencia), "
        "to_char(f.competencia, 'YYYY-MM'), round(avg(f.kwh), 2), lower(f.cod_uc) "
        "FROM sem_faturamento_mensal f GROUP BY 1, 2, 3, 5",
        ALLOWED,
    )

    assert query.views == frozenset({"sem_faturamento_mensal"})


def test_unquoted_identifiers_are_case_folded_like_postgres(validator):
    query = validator.validate("SELECT COD_UC FROM GOLD.SEM_UC", ALLOWED)

    assert query.views == frozenset({"sem_uc"})


def test_views_are_qualified_with_the_allowed_schema_but_ctes_are_not(validator):
    query = validator.validate(
        "WITH base AS (SELECT cod_uc FROM sem_uc) SELECT b.cod_uc FROM base b", ALLOWED
    )

    assert "FROM gold.sem_uc" in query.sql
    assert "FROM base AS b" in query.sql


def test_only_the_configured_schema_is_allowed():
    validator = SqlglotValidator(dialect="postgres", max_rows=200, allowed_schema="semantic")

    assert validator.validate("SELECT 1 FROM semantic.sem_uc", ALLOWED).views == {"sem_uc"}
    with pytest.raises(SqlRejected):
        validator.validate("SELECT 1 FROM gold.sem_uc", ALLOWED)


def test_accepts_single_select_on_allowed_view(validator):
    query = validator.validate("SELECT municipio FROM sem_uc", ALLOWED)

    assert query.views == frozenset({"sem_uc"})
    assert query.applied_limit == 200
    assert query.limit_imposed is True
    assert query.sql.upper().endswith("LIMIT 200")


def test_accepts_with_select_and_cte_names_are_not_tables(validator):
    query = validator.validate(
        "WITH base AS (SELECT cod_uc FROM sem_uc) SELECT * FROM base", ALLOWED
    )

    assert query.views == frozenset({"sem_uc"})


def test_accepts_join_between_allowed_views(validator):
    query = validator.validate(
        "SELECT u.cod_uc, f.competencia FROM sem_uc u "
        "JOIN sem_faturamento_mensal f ON f.cod_uc = u.cod_uc",
        ALLOWED,
    )

    assert query.views == frozenset({"sem_uc", "sem_faturamento_mensal"})


def test_accepts_schema_qualified_gold_view(validator):
    query = validator.validate("SELECT count(*) FROM gold.sem_uc", ALLOWED)

    assert query.views == frozenset({"sem_uc"})


def test_accepts_union_of_allowed_views(validator):
    query = validator.validate(
        "SELECT cod_uc FROM sem_uc UNION SELECT cod_uc FROM sem_faturamento_mensal", ALLOWED
    )

    assert query.views == frozenset({"sem_uc", "sem_faturamento_mensal"})


def test_select_without_table_is_accepted(validator):
    query = validator.validate("SELECT 1 /* DROP TABLE sem_uc */", ALLOWED)

    assert query.views == frozenset()


def test_existing_limit_within_maximum_is_kept(validator):
    query = validator.validate("SELECT cod_uc FROM sem_uc LIMIT 10", ALLOWED)

    assert query.applied_limit == 10
    assert query.limit_imposed is False
    assert query.sql.upper().endswith("LIMIT 10")


def test_limit_above_maximum_is_reduced(validator):
    query = validator.validate("SELECT cod_uc FROM sem_uc LIMIT 5000", ALLOWED)

    assert query.applied_limit == 200
    assert query.limit_imposed is True
    assert query.sql.upper().endswith("LIMIT 200")
