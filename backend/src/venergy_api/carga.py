"""Carga dos CSVs da Gold no banco local.

É o mesmo caminho que a Gold real vai percorrer: o time de dados entrega os CSVs na
pasta configurada em VENERGY_API_GOLD_DIR, e cada linha é validada contra o contrato
(schemas.py) antes de ser gravada.

Uso: uv run python -m venergy_api.carga
"""

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import get_args, get_origin

from pydantic import BaseModel, ValidationError
from sqlalchemy import Connection, Engine, insert, text

from venergy_api.config import get_settings
from venergy_api.database import Base, get_engine
from venergy_api.models import (
    ContinuidadeAlimentadorMensal,
    DimUc,
    FatoFaturamentoMensal,
    FilaSuspeita,
    KpisMensais,
    KpisSegmentoMensal,
    ReceitaDecomposicao,
    ReconciliacaoFaturamento,
)
from venergy_api.schemas import (
    ContinuidadeAlimentadorMensalSchema,
    DimUcSchema,
    FaturamentoMensalSchema,
    FilaSuspeitaSchema,
    KpisMensaisSchema,
    KpisSegmentoMensalSchema,
    ReceitaDecomposicaoSchema,
    ReconciliacaoFaturamentoSchema,
)

# conventions.delivery.array_separator do contrato da Gold.
ARRAY_SEPARATOR = ";"

# Views da camada semântica do agente de IA: o GenAI gera o arquivo, e a carga o aplica a
# cada execução, porque as views dependem das tabelas que ela recria (spec do agente, D7).
# backend/src/venergy_api/carga.py → raiz do repositório, como em openapi.py.
AGENT_VIEWS_SQL = Path(__file__).resolve().parents[3] / "ai-agent" / "semantic" / "views.sql"


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
GOLD_TABLES = (
    GoldTable(model=DimUc, schema=DimUcSchema),
    GoldTable(model=FatoFaturamentoMensal, schema=FaturamentoMensalSchema),
    GoldTable(model=ReceitaDecomposicao, schema=ReceitaDecomposicaoSchema),
    GoldTable(model=KpisMensais, schema=KpisMensaisSchema),
    GoldTable(model=KpisSegmentoMensal, schema=KpisSegmentoMensalSchema),
    GoldTable(model=ReconciliacaoFaturamento, schema=ReconciliacaoFaturamentoSchema),
    GoldTable(model=ContinuidadeAlimentadorMensal, schema=ContinuidadeAlimentadorMensalSchema),
    GoldTable(model=FilaSuspeita, schema=FilaSuspeitaSchema),
)


def _describe(error: ValidationError) -> str:
    return "; ".join(f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in error.errors())


def _is_list(annotation: object) -> bool:
    """Se o campo é uma lista, inclusive dentro de um opcional (list[str] | None)."""
    return get_origin(annotation) is list or any(_is_list(arg) for arg in get_args(annotation))


def _parse_cell(value: str, is_list: bool) -> object:
    # Regras do formato CSV do contrato, por isso ficam aqui e não nos schemas: os mesmos
    # schemas validam o que entra pela API. Célula vazia é nulo, e uma coluna text[]
    # chega numa célula só, com os itens separados por ponto e vírgula.
    if value == "":
        return None
    if is_list:
        # Sem descartar item vazio ("a;;b"): o schema recusa, e o erro aponta a linha.
        return value.split(ARRAY_SEPARATOR)
    return value


def read_rows(csv_path: Path, schema: type[BaseModel]) -> list[dict[str, object]]:
    """Lê o CSV e valida cada linha, parando na primeira que fugir do contrato."""
    # utf-8-sig aceita o BOM que Excel e algumas exportações colocam no início do arquivo.
    with csv_path.open(encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        missing = set(schema.model_fields) - set(reader.fieldnames or [])
        if missing:
            raise GoldLoadError(f"{csv_path.name}: colunas faltando: {', '.join(sorted(missing))}")

        list_columns = {
            name for name, field in schema.model_fields.items() if _is_list(field.annotation)
        }
        rows = []
        # A linha 1 é o cabeçalho, então a primeira linha de dados é a 2.
        for line_number, raw_row in enumerate(reader, start=2):
            row = {
                column: _parse_cell(value, column in list_columns)
                for column, value in raw_row.items()
            }
            try:
                rows.append(schema.model_validate(row).model_dump())
            except ValidationError as error:
                message = f"{csv_path.name}, linha {line_number}: {_describe(error)}"
                raise GoldLoadError(message) from error
    return rows


def drop_agent_views(connection: Connection) -> None:
    """Apaga as views sem_* do agente no schema gold, para as tabelas poderem ser recriadas."""
    # Pelo catálogo, e não pelos nomes do views.sql: uma view que o GenAI renomeou ou tirou
    # do arquivo ainda estaria presa à tabela, e o DROP da tabela falharia.
    nomes = connection.scalars(
        text(r"SELECT viewname FROM pg_views WHERE schemaname = 'gold' AND viewname LIKE 'sem\_%'")
    ).all()
    if not nomes:
        return
    # Um DROP só, com todas: se uma view ler de outra, o Postgres resolve a ordem. Os nomes
    # vêm do catálogo, e não de entrada de usuário.
    quote = connection.dialect.identifier_preparer.quote
    connection.execute(text(f"DROP VIEW {', '.join(f'gold.{quote(nome)}' for nome in nomes)}"))


def load_gold(gold_dir: Path, engine: Engine) -> dict[str, int]:
    """Substitui as tabelas da Gold pelo conteúdo dos CSVs e devolve as linhas por tabela."""
    # Valida tudo antes de gravar: um arquivo ruim não pode deixar o banco pela metade.
    validated: dict[GoldTable, list[dict[str, object]]] = {}
    for table in GOLD_TABLES:
        csv_path = gold_dir / table.file_name
        if not csv_path.exists():
            raise GoldLoadError(f"arquivo não encontrado: {csv_path}")
        validated[table] = read_rows(csv_path, table.schema)
    if not AGENT_VIEWS_SQL.exists():
        raise GoldLoadError(f"views do agente não encontradas: {AGENT_VIEWS_SQL}")
    views_sql = AGENT_VIEWS_SQL.read_text(encoding="utf-8")

    gold_tables = [table.model.__table__ for table in GOLD_TABLES]
    # Tudo numa transação (no Postgres, DROP e CREATE também voltam atrás): rodar duas
    # vezes não duplica, e uma falha no meio desfaz tudo, inclusive o DROP.
    with engine.begin() as connection:
        # As views do agente prendem as tabelas: saem antes e voltam no fim. O drop_all
        # continua sem CASCADE, para uma dependência que ninguém previu falhar a carga em vez
        # de sumir em silêncio (DEC-014).
        drop_agent_views(connection)
        # Recria a Gold em vez de só apagar as linhas: sem migrações, o create_all não
        # acrescenta coluna em tabela que já existe, e cada mudança do contrato exigiria
        # apagar a tabela à mão. O drop só passa por GOLD_TABLES: nunca apaga uma OI.
        Base.metadata.drop_all(connection, tables=gold_tables)
        # Cria a Gold e o que faltar no schema app, sem mexer no que já está lá.
        Base.metadata.create_all(connection)
        for table, rows in validated.items():
            if rows:
                connection.execute(insert(table.model), rows)
        connection.exec_driver_sql(views_sql)

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
