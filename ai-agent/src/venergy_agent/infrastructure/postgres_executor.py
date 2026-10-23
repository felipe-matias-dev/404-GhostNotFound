import math

import psycopg
from psycopg.rows import dict_row

from venergy_agent.domain.errors import ErrorKind, QueryExecutionError
from venergy_agent.domain.sql import QueryResult, ValidatedQuery

SQLSTATE_KINDS = {
    "42601": ErrorKind.SYNTAX,
    "42P01": ErrorKind.UNKNOWN_OBJECT,
    "42703": ErrorKind.UNKNOWN_OBJECT,
    "42804": ErrorKind.TYPE_MISMATCH,
    "42883": ErrorKind.TYPE_MISMATCH,
    "22P02": ErrorKind.TYPE_MISMATCH,
    "57014": ErrorKind.TIMEOUT,
}


class PostgresQueryExecutor:
    def __init__(self, database_url: str, timeout_seconds: float) -> None:
        self._database_url = database_url
        self._timeout_ms = str(max(1, math.ceil(timeout_seconds * 1000)))
        self._connect_timeout = max(1, math.ceil(timeout_seconds))

    async def execute(self, query: ValidatedQuery) -> QueryResult:
        async with await psycopg.AsyncConnection.connect(
            self._database_url, row_factory=dict_row, connect_timeout=self._connect_timeout
        ) as connection:
            try:
                await connection.execute("SET TRANSACTION READ ONLY")
                await connection.execute(
                    "SELECT set_config('statement_timeout', %s, true)", (self._timeout_ms,)
                )
                cursor = await connection.execute(query.sql)
                rows = tuple(await cursor.fetchall())
                columns = tuple(column.name for column in cursor.description)
                await connection.rollback()
                if len(set(columns)) != len(columns):
                    raise QueryExecutionError(
                        ErrorKind.SYNTAX,
                        "duas colunas têm o mesmo nome; dê nomes distintos com AS",
                    )
            except psycopg.Error as error:
                kind = SQLSTATE_KINDS.get(error.sqlstate or "")
                if kind is None:
                    raise
                raise QueryExecutionError(kind, str(error)) from error
        return QueryResult(
            columns=columns,
            rows=rows,
            row_count=len(rows),
            truncated=query.limit_imposed and len(rows) >= query.applied_limit,
        )
