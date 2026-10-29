import logging
from collections.abc import Callable
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, select, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from venergy_api.amostra import write_sample
from venergy_api.auditoria import garantir_colunas_na_subida
from venergy_api.carga import load_gold
from venergy_api.models import AiAuditoria


@pytest.fixture
def gold_dir(tmp_path: Path, engine: Engine) -> Path:
    # Mesmo caminho do README: gera a amostra sintética e carrega pela carga da Gold,
    # que também cria as tabelas do schema app.
    gold_dir = tmp_path / "gold"
    write_sample(gold_dir, force=True)
    load_gold(gold_dir, engine)
    return gold_dir


def test_audit_records_survive_a_gold_reload(gold_dir: Path, engine: Engine) -> None:
    with Session(engine) as session, session.begin():
        session.add(
            AiAuditoria(
                session_id="sessao-1",
                pergunta="Qual foi a receita faturada em 2024-06?",
                answer="A receita faturada foi de R$ 10,00.",
                status="answered",
                sql="SELECT 1 LIMIT 1",
                rows=[{"receita_faturada": 10.0}],
                row_count=1,
                truncated=False,
                confidence="high",
                sources=["sem_kpis_mensais"],
                assumptions=[],
                request_id="req-1",
                model="google-gla:gemini",
                prompt_version="v2",
                latency_ms=120,
            )
        )

    load_gold(gold_dir, engine)
    load_gold(gold_dir, engine)

    with Session(engine) as session:
        stored = session.scalars(select(AiAuditoria)).one()
        assert stored.pergunta == "Qual foi a receita faturada em 2024-06?"
        assert stored.rows == [{"receita_faturada": 10.0}]
        assert stored.sources == ["sem_kpis_mensais"]
        assert stored.criado_em is not None


def test_reload_adds_the_token_columns_to_an_older_audit_table(
    gold_dir: Path, engine: Engine
) -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO app.ai_auditoria (session_id, pergunta, answer, status, rows, "
                "row_count, truncated, confidence, sources, assumptions, request_id, model, "
                "prompt_version, latency_ms) VALUES ('s', 'p', 'a', 'answered', '[]', 0, false, "
                "'high', '[]', '[]', 'r', 'm', 'v2', 1)"
            )
        )
        connection.execute(
            text("ALTER TABLE app.ai_auditoria DROP COLUMN input_tokens, DROP COLUMN output_tokens")
        )

    load_gold(gold_dir, engine)
    load_gold(gold_dir, engine)

    with Session(engine) as session:
        stored = session.scalars(select(AiAuditoria)).one()
        assert stored.pergunta == "p"
        assert (stored.input_tokens, stored.output_tokens) == (0, 0)


def test_startup_adds_the_token_columns_to_an_older_audit_table(
    gold_dir: Path, engine: Engine
) -> None:
    with engine.begin() as connection:
        connection.execute(
            text("ALTER TABLE app.ai_auditoria DROP COLUMN input_tokens, DROP COLUMN output_tokens")
        )

    garantir_colunas_na_subida(lambda: engine)

    with Session(engine) as session:
        assert (
            session.execute(text("SELECT input_tokens, output_tokens FROM app.ai_auditoria")).all()
            == []
        )


def test_startup_survives_a_database_that_is_down(caplog: pytest.LogCaptureFixture) -> None:
    def engine_fora() -> Engine:
        raise OperationalError("SELECT 1", {}, Exception("banco fora"))

    with caplog.at_level(logging.WARNING):
        garantir_colunas_na_subida(engine_fora)

    assert "auditoria" in caplog.text.lower()


def test_api_startup_ensures_the_audit_columns(
    engine: Engine, client_for: Callable[..., TestClient], monkeypatch: pytest.MonkeyPatch
) -> None:
    chamadas = []

    async def sem_agente() -> None:
        return None

    monkeypatch.setattr("venergy_api.main.montar_agente", sem_agente)
    monkeypatch.setattr("venergy_api.main.montar_redator_insights", sem_agente)
    monkeypatch.setattr(
        "venergy_api.main.garantir_colunas_na_subida", lambda *_: chamadas.append(True)
    )

    with client_for(engine):
        pass

    assert chamadas == [True]


def test_reload_and_startup_add_the_user_column_and_index_to_an_older_audit_table(
    gold_dir: Path, engine: Engine
) -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO app.ai_auditoria (session_id, pergunta, answer, status, rows, "
                "row_count, truncated, confidence, sources, assumptions, request_id, model, "
                "prompt_version, latency_ms) VALUES ('s', 'p', 'a', 'answered', '[]', 0, false, "
                "'high', '[]', '[]', 'r', 'm', 'v2', 1)"
            )
        )
        connection.execute(text("DROP INDEX app.ix_ai_auditoria_usuario"))
        connection.execute(text("ALTER TABLE app.ai_auditoria DROP COLUMN usuario"))

    load_gold(gold_dir, engine)
    garantir_colunas_na_subida(lambda: engine)

    with Session(engine) as session:
        stored = session.scalars(select(AiAuditoria)).one()
        assert stored.pergunta == "p"
        assert stored.usuario is None
    with engine.connect() as connection:
        indices = connection.execute(
            text("SELECT indexname FROM pg_indexes WHERE schemaname = 'app'")
        ).scalars()
        assert "ix_ai_auditoria_usuario" in set(indices)
