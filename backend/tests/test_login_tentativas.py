from sqlalchemy import Engine, inspect, text

from venergy_api.database import Base
from venergy_api.estrutura_app import garantir_estrutura_do_app


def test_old_database_gets_the_login_attempts_table(engine: Engine) -> None:
    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(text("DROP TABLE app.tentativa_login"))
        garantir_estrutura_do_app(connection)

    assert inspect(engine).has_table("tentativa_login", schema="app")
