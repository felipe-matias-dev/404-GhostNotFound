import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError

from venergy_agent.domain.errors import SqlRejected
from venergy_agent.domain.sql import ValidatedQuery

FORBIDDEN_NODES = (exp.DML, exp.DDL, exp.Command, exp.Set, exp.Copy)
FORBIDDEN_FUNCTION_PREFIXES = ("pg_", "lo_")
FORBIDDEN_FUNCTIONS = frozenset({"dblink", "dblink_exec", "set_config", "current_setting"})
ALLOWED_SCHEMAS = frozenset({"", "gold"})


class SqlglotValidator:
    def __init__(self, dialect: str, max_rows: int) -> None:
        self._dialect = dialect
        self._max_rows = max_rows

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
        return root

    def _reject_forbidden_nodes(self, root: exp.Query) -> None:
        for node in root.walk():
            if isinstance(node, FORBIDDEN_NODES):
                raise SqlRejected(f"forbidden statement: {type(node).__name__}")
            if isinstance(node, exp.Func):
                name = node.name if isinstance(node, exp.Anonymous) else node.sql_name()
                if self._is_forbidden_function(name):
                    raise SqlRejected(f"forbidden function: {name}")

    def _is_forbidden_function(self, name: str) -> bool:
        lowered = name.lower()
        return lowered.startswith(FORBIDDEN_FUNCTION_PREFIXES) or lowered in FORBIDDEN_FUNCTIONS

    def _collect_views(self, root: exp.Query, allowed_views: frozenset[str]) -> frozenset[str]:
        cte_names = {cte.alias_or_name for cte in root.find_all(exp.CTE)}
        used: set[str] = set()
        for table in root.find_all(exp.Table):
            if table.args.get("catalog") or table.db not in ALLOWED_SCHEMAS:
                raise SqlRejected(f"table outside the allowed schema: {table.sql()}")
            name = table.name
            if not name:
                raise SqlRejected("table without name")
            if not table.db and name in cte_names:
                continue
            if name not in allowed_views:
                raise SqlRejected(f"table not allowed: {name}")
            used.add(name)
        return frozenset(used)

    def _apply_limit(self, root: exp.Query) -> tuple[exp.Query, int]:
        current = root.args.get("limit")
        if current is None:
            return root.limit(self._max_rows), self._max_rows

        value = current.expression
        if not isinstance(value, exp.Literal) or value.is_string or not value.name.isdigit():
            raise SqlRejected("LIMIT must be an integer literal")
        requested = int(value.name)
        if requested <= self._max_rows:
            return root, requested
        current.set("expression", exp.Literal.number(self._max_rows))
        return root, self._max_rows
