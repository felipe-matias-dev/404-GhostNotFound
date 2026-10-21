"""Carga dos CSVs da Gold no banco local.

É o mesmo caminho que a Gold real vai percorrer: o time de dados entrega os CSVs na
pasta configurada em VENERGY_API_GOLD_DIR, e cada linha é validada contra o contrato
(schemas.py) antes de ser gravada.

Uso: uv run python -m venergy_api.carga
"""

import csv
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, ValidationError
from sqlalchemy import Engine, delete, insert
from sqlalchemy.orm import Session

from venergy_api.config import get_settings
from venergy_api.database import Base, get_engine
from venergy_api.models import DimUc
from venergy_api.schemas import DimUcSchema


class GoldLoadError(Exception):
    """CSV da Gold fora do contrato. Quando acontece, nada é gravado no banco."""


@dataclass(frozen=True)
class GoldTable:
    model: type[Base]
    schema: type[BaseModel]

    @property
    def file_name(self) -> str:
        return f"{self.model.__tablename__}.csv"


# Uma entrada por tabela do contrato da Gold.
GOLD_TABLES = (GoldTable(model=DimUc, schema=DimUcSchema),)


def _describe(error: ValidationError) -> str:
    return "; ".join(f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in error.errors())


def read_rows(csv_path: Path, schema: type[BaseModel]) -> list[dict[str, object]]:
    """Lê o CSV e valida cada linha, parando na primeira que fugir do contrato."""
    # utf-8-sig aceita o BOM que Excel e algumas exportações colocam no início do arquivo.
    with csv_path.open(encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        missing = set(schema.model_fields) - set(reader.fieldnames or [])
        if missing:
            raise GoldLoadError(f"{csv_path.name}: colunas faltando: {', '.join(sorted(missing))}")

        rows = []
        # A linha 1 é o cabeçalho, então a primeira linha de dados é a 2.
        for line_number, raw_row in enumerate(reader, start=2):
            # No contrato, célula vazia é nulo. A conversão fica aqui, e não nos schemas,
            # porque é regra do formato CSV: os mesmos schemas validam o que entra pela API.
            row = {column: None if value == "" else value for column, value in raw_row.items()}
            try:
                rows.append(schema.model_validate(row).model_dump())
            except ValidationError as error:
                message = f"{csv_path.name}, linha {line_number}: {_describe(error)}"
                raise GoldLoadError(message) from error
    return rows


def load_gold(gold_dir: Path, engine: Engine) -> dict[str, int]:
    """Substitui as tabelas da Gold pelo conteúdo dos CSVs e devolve as linhas por tabela."""
    # Valida tudo antes de gravar: um arquivo ruim não pode deixar o banco pela metade.
    validated: dict[GoldTable, list[dict[str, object]]] = {}
    for table in GOLD_TABLES:
        csv_path = gold_dir / table.file_name
        if not csv_path.exists():
            raise GoldLoadError(f"arquivo não encontrado: {csv_path}")
        validated[table] = read_rows(csv_path, table.schema)

    # Cria as tabelas que faltarem, inclusive as do schema app (ordens de inspeção). O
    # delete abaixo só passa por GOLD_TABLES, então recarregar a Gold nunca apaga uma OI.
    Base.metadata.create_all(engine)
    # Apagar e inserir na mesma transação: rodar duas vezes não duplica, e uma falha
    # no meio desfaz tudo.
    with Session(engine) as session, session.begin():
        for table, rows in validated.items():
            session.execute(delete(table.model))
            if rows:
                session.execute(insert(table.model), rows)

    return {table.model.__tablename__: len(rows) for table, rows in validated.items()}


def main() -> None:
    try:
        counts = load_gold(get_settings().gold_dir, get_engine())
    except GoldLoadError as error:
        # Mensagem curta e código de saída 1: quem roda ou automatiza a carga sabe que falhou.
        raise SystemExit(f"Carga cancelada, banco não foi alterado. {error}") from error
    for table_name, count in counts.items():
        print(f"{table_name}: {count} linhas carregadas")


if __name__ == "__main__":
    main()
