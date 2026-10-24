from dataclasses import dataclass
from itertools import combinations
from pathlib import Path
from typing import Any

import yaml

from venergy_agent.domain.semantic import (
    BusinessRule,
    ColumnSpec,
    FewShotExample,
    GlossaryTerm,
    Relation,
    SemanticLayer,
    ViewSpec,
)
from venergy_agent.domain.sql import DraftStatus

CONFIRMED_STATUSES = frozenset({"confirmada", "proposta"})
ENTITY_KEYS = frozenset({"cod_uc", "cod_alimentador"})
AGENT_CONSUMER = "agente"


class SemanticLayerError(ValueError):
    def __init__(self, problems: list[str]) -> None:
        super().__init__("\n".join(f"- {problem}" for problem in problems))
        self.problems = tuple(problems)


@dataclass(frozen=True)
class ViewDefinition:
    name: str
    source_table: str
    columns: tuple[str, ...]


def read_documents(layer_path: Path, contract_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    layer = yaml.safe_load(layer_path.read_text(encoding="utf-8"))
    contract = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
    return layer, contract


def view_definitions(layer: dict[str, Any], contract: dict[str, Any]) -> tuple[ViewDefinition, ...]:
    problems: list[str] = []
    tables = contract["tables"]
    definitions: list[ViewDefinition] = []
    for view in layer.get("views", []):
        name = view.get("name", "")
        source = view.get("source", "")
        if not name.startswith("sem_"):
            problems.append(f"view {name!r} deve começar com sem_")
        if source not in tables:
            problems.append(f"view {name!r}: tabela {source!r} não existe no contrato")
            continue

        table = tables[source]
        if AGENT_CONSUMER not in table.get("consumers", ()):
            problems.append(
                f"view {name!r}: a tabela {source} não tem {AGENT_CONSUMER} em consumers"
            )
        columns = {column["name"] for column in view.get("columns", [])}
        ordered = tuple(column["name"] for column in view.get("columns", []))
        primary_key = table["primary_key"]
        if not isinstance(primary_key, list):
            problems.append(f"view {name!r}: chave primária de {source} não está definida")
        else:
            for key in primary_key:
                if key not in columns:
                    problems.append(f"view {name!r}: falta a coluna da chave primária {key!r}")
                if table["columns"][key]["status"] not in CONFIRMED_STATUSES:
                    problems.append(f"view {name!r}: a chave {key!r} não está confirmada")

        for column in view.get("columns", []):
            column_name = column["name"]
            spec = table["columns"].get(column_name)
            if spec is None:
                problems.append(f"view {name!r}: coluna {column_name!r} não existe em {source}")
            elif spec["status"] not in CONFIRMED_STATUSES:
                problems.append(
                    f"view {name!r}: coluna {column_name!r} tem status {spec['status']!r}, "
                    "e só confirmada ou proposta entra"
                )
            elif spec.get("sensitive", False):
                problems.append(f"view {name!r}: coluna {column_name!r} é sensível")
        definitions.append(ViewDefinition(name=name, source_table=source, columns=ordered))

    if problems:
        raise SemanticLayerError(problems)
    return tuple(definitions)


def build_layer(layer: dict[str, Any], contract: dict[str, Any]) -> SemanticLayer:
    definitions = view_definitions(layer, contract)
    tables = contract["tables"]
    problems: list[str] = []

    views: list[ViewSpec] = []
    for view_doc in layer["views"]:
        source = tables[view_doc["source"]]
        view_columns = []
        for column in view_doc["columns"]:
            contract_column = source["columns"][column["name"]]
            allowed = tuple(contract_column.get("allowed", ()))
            view_columns.append(
                ColumnSpec(
                    name=column["name"],
                    type=contract_column["type"],
                    description=column["description"],
                    unit=column.get("unit"),
                    allowed_values=allowed,
                )
            )
        sample_rows = tuple(view_doc.get("sample_rows", ()))
        for row in sample_rows:
            for column in view_columns:
                if column.allowed_values and row.get(column.name) not in (
                    None,
                    *column.allowed_values,
                ):
                    problems.append(
                        f"{view_doc['name']}: exemplo com valor fora do contrato em "
                        f"{column.name}: {row[column.name]!r}"
                    )
        views.append(
            ViewSpec(
                name=view_doc["name"],
                description=view_doc["description"],
                grain=view_doc["grain"],
                columns=tuple(view_columns),
                sample_rows=sample_rows,
            )
        )

    if problems:
        raise SemanticLayerError(problems)

    return SemanticLayer(
        version=str(layer["version"]),
        views=tuple(views),
        relations=_relations(definitions, contract),
        glossary=tuple(
            GlossaryTerm(
                term=term["term"],
                synonyms=tuple(term.get("synonyms", ())),
                maps_to=term["maps_to"],
            )
            for term in layer.get("glossary", ())
        ),
        rules=tuple(BusinessRule(text=rule["text"]) for rule in layer.get("rules", ())),
        examples=tuple(
            FewShotExample(
                question=example["question"],
                sql=example.get("sql"),
                expected_status=DraftStatus(example["expected_status"]),
            )
            for example in layer.get("examples", ())
        ),
    )


def _relations(
    definitions: tuple[ViewDefinition, ...], contract: dict[str, Any]
) -> tuple[Relation, ...]:
    by_table = {definition.source_table: definition for definition in definitions}
    relations: set[Relation] = set()

    for definition in definitions:
        for foreign_key in contract["tables"][definition.source_table].get("foreign_keys", ()):
            referenced_table, referenced_column = foreign_key["references"].split(".")
            target = by_table.get(referenced_table)
            if target is None or referenced_column not in target.columns:
                continue
            for column in foreign_key["columns"]:
                if column in definition.columns:
                    relations.add(
                        Relation(
                            left_view=definition.name,
                            left_column=column,
                            right_view=target.name,
                            right_column=referenced_column,
                        )
                    )

    for key in sorted(ENTITY_KEYS):
        holders = [definition for definition in definitions if key in definition.columns]
        for left, right in combinations(holders, 2):
            relations.add(
                Relation(
                    left_view=left.name, left_column=key, right_view=right.name, right_column=key
                )
            )
    return _one_per_link(relations)


def _one_per_link(relations: set[Relation]) -> tuple[Relation, ...]:
    chosen: dict[tuple[tuple[str, str], ...], Relation] = {}
    for relation in sorted(relations, key=lambda item: item.model_dump_json()):
        link = tuple(
            sorted(
                [
                    (relation.left_view, relation.left_column),
                    (relation.right_view, relation.right_column),
                ]
            )
        )
        chosen.setdefault(link, relation)
    return tuple(chosen.values())


class YamlSemanticLayerSource:
    def __init__(self, layer_path: Path, contract_path: Path) -> None:
        self._layer_path = layer_path
        self._contract_path = contract_path

    async def load(self) -> SemanticLayer:
        layer, contract = read_documents(self._layer_path, self._contract_path)
        return build_layer(layer, contract)
