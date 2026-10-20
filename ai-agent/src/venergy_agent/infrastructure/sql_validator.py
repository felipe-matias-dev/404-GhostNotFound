import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError, SqlglotError
from sqlglot.optimizer.normalize_identifiers import normalize_identifiers
from sqlglot.optimizer.scope import traverse_scope

from venergy_agent.domain.errors import SqlRejected
from venergy_agent.domain.sql import ValidatedQuery

FORBIDDEN_NODES = (exp.DML, exp.DDL, exp.Command, exp.Set, exp.Copy, exp.Into, exp.Lock)
FORBIDDEN_FUNCTIONS = (
    exp.Anonymous,
    exp.CurrentUser,
    exp.SessionUser,
    exp.CurrentVersion,
    exp.CurrentDatabase,
    exp.CurrentCatalog,
    exp.CurrentSchema,
)


class SqlglotValidator:
    def __init__(self, dialect: str, max_rows: int, allowed_schema: str) -> None:
        self._dialect = dialect
        self._max_rows = max_rows
        self._allowed_schema = allowed_schema

    def validate(self, sql: str, allowed_views: frozenset[str]) -> ValidatedQuery:
        root = self._parse(sql)
        self._reject_forbidden_nodes(root)
        views = self._collect_views(root, allowed_views)
        root, applied_limit = self._apply_limit(root)
        return ValidatedQuery(
            sql=root.sql(dialect=self._dialect), views=views, applied_limit=applied_limit
        )

    def _parse(self, sql: str) -> exp.Query:
        try:
            statements = sqlglot.parse(sql, read=self._dialect)
        except ParseError as error:
            raise SqlRejected("syntax error") from error
        if len(statements) != 1 or statements[0] is None:
            raise SqlRejected("exactly one statement is required")
        root = statements[0]
        if not isinstance(root, exp.Query):
            raise SqlRejected("only SELECT or WITH ... SELECT is allowed")
        return normalize_identifiers(root, dialect=self._dialect)

    def _reject_forbidden_nodes(self, root: exp.Query) -> None:
        for node in root.walk():
            if isinstance(node, FORBIDDEN_NODES):
                raise SqlRejected(f"forbidden clause: {type(node).__name__}")
            if isinstance(node, FORBIDDEN_FUNCTIONS):
                raise SqlRejected(f"function not allowed: {node.sql(dialect=self._dialect)}")

    def _collect_views(self, root: exp.Query, allowed_views: frozenset[str]) -> frozenset[str]:
        try:
            scopes = traverse_scope(root)
        except SqlglotError as error:
            raise SqlRejected("could not resolve the tables of the query") from error

        resolved: set[int] = set()
        used: set[str] = set()
        for scope in scopes:
            for table in scope.tables:
                resolved.add(id(table))
                if table.args.get("catalog") or table.db not in ("", self._allowed_schema):
                    raise SqlRejected(f"table outside the allowed schema: {table.sql()}")
                if not table.name:
                    raise SqlRejected("table without name")
                if not table.db and table.name in scope.cte_sources:
                    continue
                if table.name not in allowed_views:
                    raise SqlRejected(f"table not allowed: {table.name}")
                table.set("db", exp.to_identifier(self._allowed_schema))
                used.add(table.name)

        if any(id(table) not in resolved for table in root.find_all(exp.Table)):
            raise SqlRejected("could not resolve the tables of the query")
        return frozenset(used)

    def _apply_limit(self, root: exp.Query) -> tuple[exp.Query, int]:
        current = root.args.get("limit")
        if current is None:
            return root.limit(self._max_rows), self._max_rows
        if isinstance(current, exp.Fetch):
            raise SqlRejected("FETCH is not supported, use LIMIT n")

        value = current.expression
        if not isinstance(value, exp.Literal) or value.is_string or not value.name.isdigit():
            raise SqlRejected("LIMIT must be an integer literal")
        requested = int(value.name)
        if requested <= self._max_rows:
            return root, requested
        current.set("expression", exp.Literal.number(self._max_rows))
        return root, self._max_rows
