"""Carga dos CSVs da Gold no banco local.

É o mesmo caminho que a Gold real vai percorrer: o time de dados entrega os CSVs na
pasta configurada em VENERGY_API_GOLD_DIR, e cada linha é validada contra o contrato
(schemas.py) antes de ser gravada.

Uso: uv run python -m venergy_api.carga
"""

import csv
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from itertools import batched
from pathlib import Path
from typing import get_args, get_origin

from pydantic import BaseModel, ValidationError
from sqlalchemy import Connection, Engine, insert
from sqlalchemy.exc import ProgrammingError

from venergy_api.config import get_settings
from venergy_api.database import Base, get_engine
from venergy_api.estrutura_app import garantir_estrutura_do_app
from venergy_api.models import (
    AtendimentoUc,
    ContinuidadeAlimentadorMensal,
    DimUc,
    FatoFaturamentoMensal,
    FilaSuspeita,
    InspecaoUc,
    InterrupcaoUc,
    KpisMensais,
    KpisSegmentoMensal,
    MedidorUc,
    ReceitaDecomposicao,
    ReconciliacaoFaturamento,
)
from venergy_api.schemas import (
    AtendimentoUcSchema,
    ContinuidadeAlimentadorMensalSchema,
    DimUcSchema,
    FaturamentoMensalSchema,
    FilaSuspeitaSchema,
    InspecaoUcSchema,
    InterrupcaoUcSchema,
    KpisMensaisSchema,
    KpisSegmentoMensalSchema,
    MedidorUcSchema,
    ReceitaDecomposicaoSchema,
    ReconciliacaoFaturamentoSchema,
)
from venergy_api.visoes_agente import (
    AGENT_VIEWS_SQL,
    drop_agent_views,
    garantir_permissoes_do_agente,
)

# conventions.delivery.array_separator do contrato da Gold.
ARRAY_SEPARATOR = ";"

# Linhas por INSERT. A memória da carga é a de um lote, e não a do arquivo: a Gold real tem
# milhões de linhas, e guardar todas derrubou a carga numa máquina de 8 GB.
TAMANHO_LOTE = 10_000

# Views da camada semântica do agente de IA: o GenAI gera o arquivo, e a carga o aplica a
# cada execução, porque as views dependem das tabelas que ela recria (spec do agente, D7).
# backend/src/venergy_api/carga.py → raiz do repositório, como em openapi.py.


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
    GoldTable(model=InterrupcaoUc, schema=InterrupcaoUcSchema),
    GoldTable(model=AtendimentoUc, schema=AtendimentoUcSchema),
    GoldTable(model=MedidorUc, schema=MedidorUcSchema),
    GoldTable(model=InspecaoUc, schema=InspecaoUcSchema),
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


def iter_rows(csv_path: Path, schema: type[BaseModel]) -> Iterator[dict[str, object]]:
    """Lê o CSV uma linha por vez, validando cada uma, e para na primeira que fugir do contrato."""
    # Um gerador, e não uma lista: a Gold real tem milhões de linhas, e guardar todas na
    # memória derrubou a carga numa máquina de 8 GB. Quem consome decide quanto guardar.
    # utf-8-sig aceita o BOM que Excel e algumas exportações colocam no início do arquivo.
    with csv_path.open(encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        missing = set(schema.model_fields) - set(reader.fieldnames or [])
        if missing:
            raise GoldLoadError(f"{csv_path.name}: colunas faltando: {', '.join(sorted(missing))}")

        list_columns = {
            name for name, field in schema.model_fields.items() if _is_list(field.annotation)
        }
        # A linha 1 é o cabeçalho, então a primeira linha de dados é a 2.
        for line_number, raw_row in enumerate(reader, start=2):
            row = {
                column: _parse_cell(value, column in list_columns)
                for column, value in raw_row.items()
            }
            try:
                yield schema.model_validate(row).model_dump()
            except ValidationError as error:
                message = f"{csv_path.name}, linha {line_number}: {_describe(error)}"
                raise GoldLoadError(message) from error


def read_rows(csv_path: Path, schema: type[BaseModel]) -> list[dict[str, object]]:
    """Todas as linhas do CSV numa lista: só para arquivos pequenos. A carga usa iter_rows."""
    return list(iter_rows(csv_path, schema))


def _inserir_em_lotes(
    connection: Connection,
    model: type[Base],
    rows: Iterable[dict[str, object]],
    tamanho_lote: int,
) -> int:
    """Grava as linhas de um lote por vez, sem guardar mais do que um lote, e conta o que gravou."""
    gravadas = 0
    for lote in batched(rows, tamanho_lote):
        connection.execute(insert(model), list(lote))
        gravadas += len(lote)
    return gravadas


def load_gold(gold_dir: Path, engine: Engine, tamanho_lote: int = TAMANHO_LOTE) -> dict[str, int]:
    """Substitui as tabelas da Gold pelo conteúdo dos CSVs e devolve as linhas por tabela."""
    csv_paths: dict[GoldTable, Path] = {}
    for table in GOLD_TABLES:
        csv_path = gold_dir / table.file_name
        if not csv_path.exists():
            raise GoldLoadError(f"arquivo não encontrado: {csv_path}")
        csv_paths[table] = csv_path
    if not AGENT_VIEWS_SQL.exists():
        raise GoldLoadError(f"views do agente não encontradas: {AGENT_VIEWS_SQL}")
    views_sql = AGENT_VIEWS_SQL.read_text(encoding="utf-8")

    # Primeira rodada: confere todas as linhas de todos os arquivos e só conta, sem guardar
    # nada. Um arquivo ruim falha aqui, antes de a transação abrir: a Gold anterior não é
    # apagada e as tabelas não ficam travadas por minutos até o erro aparecer. A segunda
    # rodada valida de novo porque lê o arquivo de novo, e custa o dobro de validações.
    expected_counts = {
        table: sum(1 for _ in iter_rows(csv_path, table.schema))
        for table, csv_path in csv_paths.items()
    }

    gold_tables = [table.model.__table__ for table in GOLD_TABLES]
    counts: dict[str, int] = {}
    # Tudo numa transação (no Postgres, DROP e CREATE também voltam atrás): rodar duas
    # vezes não duplica, e uma falha no meio desfaz tudo, inclusive o DROP.
    with engine.begin() as connection:
        # As views do agente prendem as tabelas: saem antes e voltam no fim. O drop_all
        # continua sem CASCADE, para uma dependência que ninguém previu falhar a carga em vez
        # de sumir em silêncio (DEC-014).
        garantir_permissoes_do_agente(connection)
        drop_agent_views(connection)
        # Recria a Gold em vez de só apagar as linhas: sem migrações, o create_all não
        # acrescenta coluna em tabela que já existe, e cada mudança do contrato exigiria
        # apagar a tabela à mão. O drop só passa por GOLD_TABLES: nunca apaga uma OI.
        Base.metadata.drop_all(connection, tables=gold_tables)
        # Cria a Gold e o que faltar no schema app, sem mexer no que já está lá.
        Base.metadata.create_all(connection)
        # Um banco antigo ganha as colunas novas do app, sem tocar nas linhas (DEC-050).
        garantir_estrutura_do_app(connection)
        for table, csv_path in csv_paths.items():
            rows = iter_rows(csv_path, table.schema)
            written = _inserir_em_lotes(connection, table.model, rows, tamanho_lote)
            if written != expected_counts[table]:
                # Alguém trocou o arquivo entre as duas leituras: gravar assim seria carregar
                # o que ninguém conferiu. Falhar desfaz a transação inteira.
                raise GoldLoadError(
                    f"{csv_path.name}: o arquivo mudou durante a carga "
                    f"({expected_counts[table]} linhas conferidas, {written} gravadas)"
                )
            counts[table.model.__tablename__] = written
        try:
            connection.exec_driver_sql(views_sql)
        except ProgrammingError as error:
            # Coluna ou tabela que a Gold não tem mais: o GenAI ainda não regerou o views.sql.
            # Falhar desfaz a transação inteira, e a Gold e as views anteriores continuam. Ignorar
            # a view quebrada deixaria o agente sem consulta, e ninguém perceberia.
            raise GoldLoadError(f"as views do agente não batem com a Gold: {error.orig}") from error

    return counts


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
