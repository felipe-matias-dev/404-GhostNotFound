import sys
from pathlib import Path

from venergy_agent.config import AGENT_ROOT, REPO_ROOT
from venergy_agent.infrastructure.semantic_source import read_documents, view_definitions

VIEWS_SCHEMA = "semantic"
SOURCE_SCHEMA = "gold"
LAYER_PATH = AGENT_ROOT / "semantic" / "semantic_layer.yaml"
CONTRACT_PATH = REPO_ROOT / "contracts" / "gold_schema.yaml"
OUTPUT_PATH = AGENT_ROOT / "semantic" / "views.sql"

HEADER = (
    "-- Gerado por venergy_agent.infrastructure.views_sql a partir de\n"
    "-- semantic/semantic_layer.yaml\n"
    "-- e contracts/gold_schema.yaml. Não edite à mão.\n"
    "-- Regenerar: cd ai-agent && uv run python -m venergy_agent.infrastructure.views_sql\n"
)


def render_views_sql(layer_path: Path = LAYER_PATH, contract_path: Path = CONTRACT_PATH) -> str:
    layer, contract = read_documents(layer_path, contract_path)
    statements = []
    for definition in view_definitions(layer, contract):
        columns = ",\n    ".join(definition.columns)
        statements.append(
            f"CREATE OR REPLACE VIEW {VIEWS_SCHEMA}.{definition.name} AS\n"
            f"SELECT\n    {columns}\n"
            f"FROM {SOURCE_SCHEMA}.{definition.source_table};\n"
        )
    return HEADER + "\n" + "\n".join(statements)


def main(argv: list[str]) -> int:
    rendered = render_views_sql()
    if argv == ["--check"]:
        current = OUTPUT_PATH.read_text(encoding="utf-8") if OUTPUT_PATH.exists() else ""
        if current != rendered:
            print(f"{OUTPUT_PATH} está desatualizado. Regenere com este módulo.", file=sys.stderr)
            return 1
        return 0
    OUTPUT_PATH.write_text(rendered, encoding="utf-8")
    print(f"gravado: {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
