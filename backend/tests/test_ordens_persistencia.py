from pathlib import Path

import pytest
from sqlalchemy import Engine, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from venergy_api.amostra import write_sample
from venergy_api.carga import load_gold
from venergy_api.models import OrdemEvento, OrdemInspecao
from venergy_api.ordens import StatusOrdem


@pytest.fixture
def gold_dir(tmp_path: Path, engine: Engine) -> Path:
    # Mesmo caminho do README: gera a amostra sintética e carrega pela carga da Gold,
    # que também cria as tabelas do schema app.
    gold_dir = tmp_path / "gold"
    write_sample(gold_dir, force=True)
    load_gold(gold_dir, engine)
    return gold_dir


def add_order(session: Session, cod_uc: str, status: StatusOrdem) -> None:
    session.add(OrdemInspecao(cod_uc=cod_uc, status=status))


def test_orders_survive_a_gold_reload(gold_dir: Path, engine: Engine) -> None:
    with Session(engine) as session, session.begin():
        ordem = OrdemInspecao(cod_uc="0001")
        ordem.eventos.append(OrdemEvento(status_novo=StatusOrdem.GERADA))
        session.add(ordem)

    load_gold(gold_dir, engine)

    with Session(engine) as session:
        stored = session.scalars(select(OrdemInspecao)).one()
        assert stored.cod_uc == "0001"
        assert stored.status == StatusOrdem.GERADA
        assert [evento.status_novo for evento in stored.eventos] == [StatusOrdem.GERADA]


def test_rejects_a_second_active_order_for_the_same_uc(gold_dir: Path, engine: Engine) -> None:
    with Session(engine) as session, session.begin():
        add_order(session, "0001", StatusOrdem.GERADA)

    with (
        pytest.raises(IntegrityError, match="uq_ordem_inspecao_uc_ativa"),
        Session(engine) as session,
        session.begin(),
    ):
        add_order(session, "0001", StatusOrdem.EM_CAMPO)


def test_allows_a_new_order_once_the_previous_one_is_closed(gold_dir: Path, engine: Engine) -> None:
    with Session(engine) as session, session.begin():
        add_order(session, "0001", StatusOrdem.CONCLUIDA)
        add_order(session, "0001", StatusOrdem.CANCELADA)
        add_order(session, "0001", StatusOrdem.GERADA)

    with Session(engine) as session:
        assert len(session.scalars(select(OrdemInspecao)).all()) == 3


def test_database_rejects_an_unknown_status(gold_dir: Path, engine: Engine) -> None:
    # SQL direto, passando por fora do Python: o CHECK no banco é a última barreira.
    with (
        pytest.raises(IntegrityError, match="ck_ordem_inspecao_status"),
        engine.begin() as connection,
    ):
        connection.execute(
            text("INSERT INTO app.ordem_inspecao (cod_uc, status) VALUES ('0001', 'PERDIDA')")
        )


def test_reload_adds_the_author_column_to_an_events_table_that_lacks_it(
    gold_dir: Path, engine: Engine
) -> None:
    # Simula o banco de quem criou as tabelas antes de a coluna existir: o create_all sozinho
    # não a acrescentaria, e as ordens de inspeção não podem ser apagadas para isso.
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE app.ordem_evento DROP COLUMN autor_login"))
        connection.execute(
            text("INSERT INTO app.ordem_inspecao (cod_uc, status) VALUES ('0001', 'GERADA')")
        )
        connection.execute(
            text(
                "INSERT INTO app.ordem_evento (ordem_id, status_novo) "
                "SELECT id, 'GERADA' FROM app.ordem_inspecao"
            )
        )

    load_gold(gold_dir, engine)
    load_gold(gold_dir, engine)

    with Session(engine) as session:
        [evento] = session.scalars(select(OrdemEvento)).all()
        assert evento.status_novo == StatusOrdem.GERADA
        assert evento.autor_login is None
