"""Exporta o contrato OpenAPI da API para contracts/openapi.json, de onde o frontend gera o client.

Uso: uv run python -m venergy_api.openapi
"""

import json
from pathlib import Path

from venergy_api.config import Settings
from venergy_api.main import create_app

# backend/src/venergy_api/openapi.py → raiz do repositório.
CONTRACT_PATH = Path(__file__).resolve().parents[3] / "contracts" / "openapi.json"


def build_contract() -> str:
    # O contrato só descreve rotas e schemas: o banco nunca é acessado, então as configurações
    # obrigatórias recebem valores fixos e o export roda sem .env, em qualquer máquina e no CI.
    settings = Settings(_env_file=None, database_url="postgresql+psycopg://", gold_dir=Path())
    schema = create_app(settings).openapi()
    return json.dumps(schema, ensure_ascii=False, indent=2) + "\n"


def main() -> None:
    CONTRACT_PATH.parent.mkdir(parents=True, exist_ok=True)
    # newline="\n": no Windows o padrão grava CRLF, o hook mixed-line-ending converte para LF
    # e este export desfaz a conversão a cada commit. LF é o que o .gitattributes define.
    CONTRACT_PATH.write_text(build_contract(), encoding="utf-8", newline="\n")
    print(f"Contrato OpenAPI gravado em {CONTRACT_PATH}")


if __name__ == "__main__":
    main()
