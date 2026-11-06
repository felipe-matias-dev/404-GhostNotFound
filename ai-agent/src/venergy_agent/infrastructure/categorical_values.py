import logging
from collections.abc import Awaitable, Callable, Mapping

import psycopg
from psycopg import sql

from venergy_agent.application.ports import SemanticLayerSource
from venergy_agent.domain.semantic import SemanticLayer

logger = logging.getLogger("venergy_agent.categorical_values")

CATEGORICAL_COLUMNS = (
    "municipio",
    "bairro",
    "classe_cadastro",
    "canal",
    "assunto",
    "tipo_medidor",
    "bandeira",
    "status_pagamento",
    "tipo",
    "causa",
)

MAX_LISTED_VALUES = 10

Loader = Callable[[Mapping[str, str]], Awaitable[Mapping[str, tuple[str, ...]]]]


def categorical_columns(layer: SemanticLayer) -> dict[str, str]:
    found: dict[str, str] = {}
    for view in layer.views:
        for column in view.columns:
            if (
                column.name in CATEGORICAL_COLUMNS
                and column.type == "text"
                and not column.allowed_values
            ):
                found.setdefault(column.name, view.name)
    return found


class WithCategoricalValues:
    def __init__(self, inner: SemanticLayerSource, loader: Loader) -> None:
        self._inner = inner
        self._loader = loader

    async def load(self) -> SemanticLayer:
        layer = await self._inner.load()
        try:
            values = await self._loader(categorical_columns(layer))
        except Exception as error:
            logger.warning("valores_categoricos_indisponiveis: %s", type(error).__name__)
            return layer
        listed = {
            column: options
            for column, options in values.items()
            if len(options) <= MAX_LISTED_VALUES
        }
        views = tuple(
            view.model_copy(
                update={
                    "columns": tuple(
                        column.model_copy(update={"allowed_values": listed[column.name]})
                        if column.name in listed and not column.allowed_values
                        else column
                        for column in view.columns
                    )
                }
            )
            for view in layer.views
        )
        hinted = {column: options for column, options in values.items() if column not in listed}
        return layer.model_copy(update={"views": views, "categorical_values": hinted})


def postgres_loader(database_url: str, schema: str, timeout_seconds: float) -> Loader:
    async def load(columns: Mapping[str, str]) -> Mapping[str, tuple[str, ...]]:
        values: dict[str, tuple[str, ...]] = {}
        async with await psycopg.AsyncConnection.connect(
            database_url, connect_timeout=max(1, int(timeout_seconds))
        ) as connection:
            await connection.execute("SET TRANSACTION READ ONLY")
            for column, view in columns.items():
                query = sql.SQL(
                    "SELECT DISTINCT {column} FROM {schema}.{view} "
                    "WHERE {column} IS NOT NULL ORDER BY 1"
                ).format(
                    column=sql.Identifier(column),
                    schema=sql.Identifier(schema),
                    view=sql.Identifier(view),
                )
                cursor = await connection.execute(query)
                values[column] = tuple(str(row[0]) for row in await cursor.fetchall())
            await connection.rollback()
        return values

    return load
