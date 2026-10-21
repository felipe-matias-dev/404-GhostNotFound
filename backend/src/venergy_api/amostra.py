"""Gera uma amostra sintética da Gold para trabalhar sem o dataset confidencial.

Os valores são inventados (nenhum vem do dataset da V-Energy), mas seguem o contrato de
schemas.py e percorrem o mesmo caminho da Gold real: CSV → carga → banco.

Uso: uv run python -m venergy_api.amostra [--force]
"""

import argparse
import csv
from pathlib import Path

from pydantic import BaseModel

from venergy_api.carga import GOLD_TABLES
from venergy_api.config import get_settings
from venergy_api.database import Base
from venergy_api.models import DimUc
from venergy_api.schemas import DimUcSchema

FIELDS = list(DimUcSchema.model_fields)

# Cobre todas as classes de consumo, UCs com e sem painel solar e municípios citados pelas
# lideranças. Os códigos são fixos para que o time possa citá-los ("busque a UC 0003").
# O titular C0001 tem duas UCs (casa e comércio), caso que o contrato prevê. A potência só
# existe para UCs com painel solar. O subgrupo fica vazio: o domínio ainda não foi definido.
_JABOATAO = "Jaboatão dos Guararapes"
_CABO = "Cabo de Santo Agostinho"
_ROWS = [
    # cod_uc, municipio, bairro, classe, cod_alimentador, possui_gd, consumo_medio_kwh_12m,
    # cod_cliente, subgrupo, potencia_kw
    ("0001", "Recife", "Boa Viagem", "B1", "AL-01", False, 162.5, "C0001", None, None),
    ("0002", "Recife", "Casa Amarela", "B1", "AL-02", True, 48.0, "C0002", None, 3.3),
    ("0003", "Olinda", "Casa Caiada", "B1", "AL-03", True, 95.3, "C0003", None, 5.0),
    ("0004", _JABOATAO, "Piedade", "B3", "AL-04", False, 1240.0, "C0004", None, None),
    ("0005", "Paulista", "Janga", "B1", "AL-05", False, 210.7, "C0005", None, None),
    ("0006", _CABO, "Zona Rural", "B2", "AL-06", True, 380.0, "C0006", None, 10.0),
    ("0007", "Recife", "Santo Amaro", "B3", "AL-01", False, 2850.0, "C0001", None, None),
    ("0008", _JABOATAO, "Prazeres", "A4", "AL-07", False, 48500.0, "C0008", None, None),
]

# Montar pelo schema faz a própria amostra falhar se sair do contrato.
SAMPLE_UCS = tuple(DimUcSchema(**dict(zip(FIELDS, row, strict=True))) for row in _ROWS)

# Linhas por tabela da Gold. A carga exige um CSV para cada tabela de GOLD_TABLES, e o
# teste da amostra falha se alguma ficar de fora.
SAMPLE: dict[type[Base], tuple[BaseModel, ...]] = {DimUc: SAMPLE_UCS}


def _to_csv_row(row: BaseModel) -> dict[str, object]:
    # Booleanos em minúsculas, como o Spark exporta: "true"/"false".
    return {
        field: str(value).lower() if isinstance(value, bool) else value
        for field, value in row.model_dump().items()
    }


def write_sample(gold_dir: Path, *, force: bool) -> list[Path]:
    """Grava um CSV por tabela da Gold em gold_dir. Sem force, não sobrescreve nenhum."""
    csv_paths = {table: gold_dir / table.file_name for table in GOLD_TABLES}
    # Confere todos antes de gravar o primeiro: misturar amostra com a Gold real deixaria
    # números de origens diferentes lado a lado, pior do que não gravar nada.
    existing = [path for path in csv_paths.values() if path.exists()]
    if existing and not force:
        raise FileExistsError(
            f"{existing[0]} já existe e pode ser a Gold real. Use --force para sobrescrever."
        )

    gold_dir.mkdir(parents=True, exist_ok=True)
    for table, csv_path in csv_paths.items():
        with csv_path.open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=list(table.schema.model_fields))
            writer.writeheader()
            writer.writerows(_to_csv_row(row) for row in SAMPLE[table.model])
    return list(csv_paths.values())


def main() -> None:
    parser = argparse.ArgumentParser(description="Gera a amostra sintética da Gold.")
    parser.add_argument("--force", action="store_true", help="sobrescreve os CSVs existentes")
    args = parser.parse_args()

    gold_dir = get_settings().gold_dir
    try:
        csv_paths = write_sample(gold_dir, force=args.force)
    except FileExistsError as error:
        raise SystemExit(str(error)) from error
    print(f"Amostra sintética gravada em {gold_dir}: {', '.join(p.name for p in csv_paths)}")


if __name__ == "__main__":
    main()
