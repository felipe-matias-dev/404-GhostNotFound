from typing import Self

from pydantic import BaseModel, ConfigDict, model_validator

from venergy_agent.domain.sql import DraftStatus


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
