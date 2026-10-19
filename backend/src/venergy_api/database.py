"""Conexão com o banco local: engine e a sessão entregue a cada requisição."""

from collections.abc import Iterator
from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session

from venergy_api.config import get_settings


class Base(DeclarativeBase):
    """Classe-mãe dos modelos: registra as tabelas que o SQLAlchemy sabe criar."""


def create_db_engine(database_url: str) -> Engine:
    return create_engine(
        database_url,
        # Testa cada conexão antes de reaproveitá-la: se o container do banco reiniciar,
        # a API descarta as conexões mortas em vez de devolver erro.
        pool_pre_ping=True,
        # Com o banco fora do ar, falha em segundos (o /health responde 503) em vez de
        # deixar a requisição pendurada.
        connect_args={"connect_timeout": 5},
    )


@lru_cache
def get_engine() -> Engine:
    """Cria a engine só no primeiro uso, para importar o app sem precisar do .env."""
    return create_db_engine(get_settings().database_url)


def get_session() -> Iterator[Session]:
    """Abre uma sessão por requisição e garante que ela seja fechada ao final."""
    with Session(get_engine()) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]
