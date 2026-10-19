"""Conexão com o banco local: engine e a sessão entregue a cada requisição."""

from collections.abc import Iterator
from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

from venergy_api.config import get_settings


def create_db_engine(database_url: str) -> Engine:
    # O FastAPI executa rotas síncronas num pool de threads, e o SQLite, por padrão,
    # recusa uma conexão usada por uma thread diferente da que a criou.
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    return create_engine(database_url, connect_args=connect_args)


@lru_cache
def get_engine() -> Engine:
    """Cria a engine só no primeiro uso, para importar o app sem precisar do .env."""
    return create_db_engine(get_settings().database_url)


def get_session() -> Iterator[Session]:
    """Abre uma sessão por requisição e garante que ela seja fechada ao final."""
    with Session(get_engine()) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]
