from venergy_agent.domain.errors import ErrorKind, QueryExecutionError
from venergy_agent.domain.sql import QueryResult
from venergy_agent.evaluation.references import check_references
from venergy_agent.infrastructure.sql_validator import SqlglotValidator

VIEWS = frozenset({"sem_uc"})
VALIDATOR = SqlglotValidator(dialect="postgres", max_rows=200, allowed_schema="gold")


class ScriptedExecutor:
    def __init__(self, results):
        self._results = results

    async def execute(self, query):
        result = self._results[query.sql.split("WHERE ")[-1].split(" LIMIT")[0]]
        if isinstance(result, Exception):
            raise result
        return result


def rows(*values):
    return QueryResult(
        columns=("total",),
        rows=tuple({"total": v} for v in values),
        row_count=len(values),
        truncated=False,
    )


def item(item_id, where, *, datasets=("amostra",), status="answered", allow_empty=False):
    return {
        "id": item_id,
        "expected_status": status,
        "datasets": list(datasets),
        "reference_sql": f"SELECT count(*) AS total FROM sem_uc WHERE {where}",
        "allow_empty_reference": allow_empty,
    }


async def test_reports_empty_and_failing_references_of_the_chosen_dataset_only():
    executor = ScriptedExecutor(
        {
            "a = 1": rows(3),
            "b = 1": QueryResult(columns=("total",), rows=(), row_count=0, truncated=False),
            "c = 1": QueryResult(columns=("total",), rows=(), row_count=0, truncated=False),
            "d = 1": QueryExecutionError(ErrorKind.UNKNOWN_OBJECT, "x"),
        }
    )
    items = [
        item("G1", "a = 1"),
        item("G2", "b = 1"),
        item("G3", "c = 1", allow_empty=True),
        item("G4", "d = 1"),
        item("G5", "e = 1", datasets=("gold_real",)),
        item("G6", "f = 1", status="clarify"),
    ]

    checked, problems = await check_references(items, "amostra", VALIDATOR, executor, VIEWS)

    assert checked == 4
    assert problems == ["G2: volta sem dados", "G4: não executa (QueryExecutionError)"]
