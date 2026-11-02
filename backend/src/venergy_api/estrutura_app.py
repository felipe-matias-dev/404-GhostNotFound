"""Colunas que o schema app ganhou depois que as tabelas já existiam.

Não há migrações, e o create_all só cria a tabela que falta: não acrescenta coluna a uma que já
existe. Apagar uma tabela do app para isso perderia as ordens de inspeção de quem já usa o portal
(DEC-050). Tudo aqui só acrescenta, com IF NOT EXISTS: nunca apaga nem altera dado.
"""

import logging

from sqlalchemy import Connection, text
from sqlalchemy.exc import SQLAlchemyError

from venergy_api.auditoria import garantir_estrutura_da_auditoria
from venergy_api.database import create_db_engine
from venergy_api.models import TentativaLogin
from venergy_api.visoes_agente import migrar_views_do_agente

logger = logging.getLogger(__name__)


def garantir_estrutura_do_app(connection: Connection) -> None:
    """Acrescenta ao schema app as colunas que faltam num banco criado antes delas."""
    # Num banco novo, a coluna já veio do create_all e o comando não faz nada. O IF EXISTS da
    # tabela cobre o banco que ainda não passou pela primeira carga: não há o que acrescentar.
    connection.execute(
        text("ALTER TABLE IF EXISTS app.ordem_evento ADD COLUMN IF NOT EXISTS autor_login text")
    )
    # Tabela nova (DEC-065): quem atualiza o código sem rodar a carga precisa dela para o login.
    TentativaLogin.__table__.create(connection, checkfirst=True)
    # Auditoria do agente (DEC-046): tokens, usuário e os índices que o limite e o histórico usam.
    garantir_estrutura_da_auditoria(connection)
    # D1: num banco antigo, as views do agente saem de gold e o acesso dele à Gold acaba.
    migrar_views_do_agente(connection)


def garantir_estrutura_na_subida(database_url: str) -> None:
    """Garante as colunas na subida da API, para quem atualiza o código sem rodar a carga.

    Sem isso, a API nova grava uma coluna que o banco antigo não tem, e gerar ou mover uma ordem
    de inspeção dá 500. Banco fora do ar não impede a subida: as rotas que usam o banco já
    respondem erro sozinhas, e a carga também garante as colunas.
    """
    # Engine própria, a partir da URL do app, e não a get_engine() global: assim a subida usa as
    # mesmas configurações que o app recebeu, inclusive nos testes.
    engine = create_db_engine(database_url)
    try:
        with engine.begin() as connection:
            garantir_estrutura_do_app(connection)
    except SQLAlchemyError as error:
        # Só o tipo do erro: a mensagem do driver pode trazer o endereço e o usuário do banco.
        logger.warning(
            "Não foi possível conferir as colunas do schema app na subida (%s). "
            "A carga da Gold também as acrescenta.",
            type(error).__name__,
        )
    finally:
        engine.dispose()
