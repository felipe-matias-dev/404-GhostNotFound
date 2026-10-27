import psycopg
from psycopg import sql


class PostgresDatabaseGuard:
    def __init__(self, database_url: str, schema: str, views: frozenset[str]) -> None:
        self._database_url = database_url
        self._schema = schema
        self._views = tuple(sorted(views))

    async def snapshot(self) -> dict[str, str]:
        async with await psycopg.AsyncConnection.connect(self._database_url) as connection:
            await connection.execute("SET TRANSACTION READ ONLY")
            fingerprints = {}
            for view in self._views:
                cursor = await connection.execute(
                    sql.SQL(
                        "SELECT count(*)::text || ':' || "
                        "coalesce(md5(string_agg(t::text, '|' ORDER BY t::text)), '') "
                        "FROM {} AS t"
                    ).format(sql.Identifier(self._schema, view))
                )
                row = await cursor.fetchone()
                fingerprints[view] = row[0] if row else ""
            await connection.rollback()
        return fingerprints

    async def accepted_writes(self) -> int:
        accepted = 0
        async with await psycopg.AsyncConnection.connect(self._database_url) as connection:
            for statement in self._writes():
                try:
                    await connection.execute(statement)
                    accepted += 1
                except psycopg.Error:
                    pass
                finally:
                    await connection.rollback()
        return accepted

    def _writes(self) -> list[sql.Composed]:
        probe = sql.Identifier(self._schema, "eval_write_probe")
        writes = [sql.SQL("CREATE TABLE {} (id integer)").format(probe)]
        for view in self._views:
            target = sql.Identifier(self._schema, view)
            writes.append(sql.SQL("DELETE FROM {}").format(target))
            writes.append(sql.SQL("DROP VIEW IF EXISTS {}").format(target))
        return writes
