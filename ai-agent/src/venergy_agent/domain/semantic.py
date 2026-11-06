import re
from collections.abc import Mapping
from typing import Self

from pydantic import BaseModel, ConfigDict, model_validator

from venergy_agent.domain.sql import DraftStatus

PERCENT_ALIAS = re.compile(r"(?:^|_)(?:percentual|pct)(?:_|$)")
QUALIFIER_WORD = (
    r"\d{4}|\d{2}|base|atual|anterior|inicial|final|total|media|soma|ponderada|mensal|anual"
)
PERIOD_QUALIFIER = re.compile(rf"(?:{QUALIFIER_WORD})(?:_(?:{QUALIFIER_WORD}))*")


class ColumnSpec(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    type: str
    description: str
    unit: str | None = None
    allowed_values: tuple[str, ...] = ()

    @property
    def view_type(self) -> str:
        return "numeric" if self.type == "integer" and self.unit == "contagem" else self.type


class ViewSpec(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    description: str
    grain: str
    columns: tuple[ColumnSpec, ...]
    sample_rows: tuple[dict[str, object], ...] = ()


class Relation(BaseModel):
    model_config = ConfigDict(frozen=True)

    left_view: str
    left_column: str
    right_view: str
    right_column: str


class GlossaryTerm(BaseModel):
    model_config = ConfigDict(frozen=True)

    term: str
    synonyms: tuple[str, ...]
    maps_to: str


class BusinessRule(BaseModel):
    model_config = ConfigDict(frozen=True)

    text: str


class FewShotExample(BaseModel):
    model_config = ConfigDict(frozen=True)

    question: str
    sql: str | None
    expected_status: DraftStatus


class SemanticLayer(BaseModel):
    model_config = ConfigDict(frozen=True)

    version: str
    views: tuple[ViewSpec, ...]
    relations: tuple[Relation, ...] = ()
    glossary: tuple[GlossaryTerm, ...] = ()
    rules: tuple[BusinessRule, ...] = ()
    examples: tuple[FewShotExample, ...] = ()
    categorical_values: dict[str, tuple[str, ...]] = {}

    @property
    def allowed_views(self) -> frozenset[str]:
        return frozenset(view.name for view in self.views)

    @property
    def column_units(self) -> dict[str, str]:
        units: dict[str, set[str | None]] = {}
        for view in self.views:
            for column in view.columns:
                units.setdefault(column.name, set()).add(column.unit)
        return {
            name: unit
            for name, found in units.items()
            if len(found) == 1 and (unit := next(iter(found))) is not None
        }

    @model_validator(mode="after")
    def check_references(self) -> Self:
        names = [view.name for view in self.views]
        if len(names) != len(set(names)):
            raise ValueError("view names must be unique")

        columns_by_view = {
            view.name: {column.name for column in view.columns} for view in self.views
        }
        for relation in self.relations:
            for view, column in (
                (relation.left_view, relation.left_column),
                (relation.right_view, relation.right_column),
            ):
                if view not in columns_by_view:
                    raise ValueError(f"relation references unknown view: {view}")
                if column not in columns_by_view[view]:
                    raise ValueError(f"relation references unknown column: {view}.{column}")
        return self


def unit_of(column: str, units: Mapping[str, str]) -> str | None:
    if column in units:
        return units[column]
    if PERCENT_ALIAS.search(column):
        return "%"
    stem, _, qualifier = column.partition("_")
    if not PERIOD_QUALIFIER.fullmatch(qualifier):
        return None
    found = {unit for name, unit in units.items() if name.partition("_")[0] == stem}
    return next(iter(found)) if len(found) == 1 else None
