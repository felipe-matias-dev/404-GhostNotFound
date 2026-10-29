import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import Session
from venergy_agent.domain.answer import AnswerStatus

from venergy_api.database import Base
from venergy_api.historico_ia import HistoricoAuditoria, usuario_da_requisicao
from venergy_api.models import AiAuditoria


@pytest.fixture(autouse=True)
def audit_table(engine: Engine) -> None:
    Base.metadata.create_all(engine)


def gravar(
    engine: Engine,
    session_id: str,
    pergunta: str,
    *,
    status: str = "answered",
    sql: str | None = "SELECT 1",
    input_tokens: int = 0,
    output_tokens: int = 0,
    minutos_atras: int = 0,
    clarification: str | None = None,
    usuario: str | None = None,
) -> None:
    with Session(engine) as session, session.begin():
        session.add(
            AiAuditoria(
                criado_em=datetime.now(UTC) - timedelta(minutes=minutos_atras),
                session_id=session_id,
                pergunta=pergunta,
                answer="texto",
                status=status,
                sql=sql,
                rows=[],
                row_count=0,
                truncated=False,
                confidence="high",
                sources=[],
                assumptions=[],
                request_id="req",
                model="m",
                prompt_version="v3",
                latency_ms=1,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                clarification=clarification,
                usuario=usuario,
            )
        )


def test_recent_returns_the_last_turns_of_the_session_oldest_first(engine: Engine) -> None:
    gravar(engine, "s1", "primeira", sql="SELECT 1", minutos_atras=30)
    gravar(engine, "s1", "segunda", sql="SELECT 2", minutos_atras=20)
    gravar(engine, "s1", "terceira", sql=None, status="clarify", minutos_atras=10)
    gravar(engine, "s2", "de outra sessão")

    turnos = asyncio.run(HistoricoAuditoria(engine).recent("s1", 2))

    assert [turno.question for turno in turnos] == ["segunda", "terceira"]
    assert turnos[0].sql == "SELECT 2"
    assert turnos[1].sql is None
    assert turnos[1].status is AnswerStatus.CLARIFY


def test_recent_of_an_unknown_session_is_empty(engine: Engine) -> None:
    assert asyncio.run(HistoricoAuditoria(engine).recent("nova", 3)) == ()


def test_recent_skips_a_status_the_agent_does_not_know(engine: Engine) -> None:
    gravar(engine, "s1", "antiga", minutos_atras=20)
    gravar(engine, "s1", "de um status futuro", status="inventado", minutos_atras=10)

    turnos = asyncio.run(HistoricoAuditoria(engine).recent("s1", 5))

    assert [turno.question for turno in turnos] == ["antiga"]


def test_tokens_used_sums_input_and_output_of_the_session_only(engine: Engine) -> None:
    gravar(engine, "s1", "a", input_tokens=100, output_tokens=20)
    gravar(engine, "s1", "b", input_tokens=50, output_tokens=5)
    gravar(engine, "s2", "c", input_tokens=999, output_tokens=999)

    historico = HistoricoAuditoria(engine)

    assert asyncio.run(historico.tokens_used("s1")) == 175
    assert asyncio.run(historico.tokens_used("sem-linhas")) == 0


def test_refused_turns_do_not_take_a_slot_of_the_limit(engine: Engine) -> None:
    gravar(engine, "s1", "respondida", minutos_atras=30)
    gravar(engine, "s1", "recusada 1", status="refused", sql=None, minutos_atras=20)
    gravar(engine, "s1", "recusada 2", status="refused", sql=None, minutos_atras=10)
    gravar(engine, "s1", "mais recente", minutos_atras=5)

    turnos = asyncio.run(HistoricoAuditoria(engine).recent("s1", 2))

    assert [turno.question for turno in turnos] == ["respondida", "mais recente"]


def test_a_clarify_turn_keeps_the_question_the_agent_asked(engine: Engine) -> None:
    gravar(
        engine,
        "s1",
        "E o FEC?",
        status="clarify",
        sql=None,
        minutos_atras=5,
        clarification="Qual período você quer?",
    )

    [turno] = asyncio.run(HistoricoAuditoria(engine).recent("s1", 3))

    assert turno.clarification == "Qual período você quer?"


def test_tokens_used_of_the_requesting_user_add_up_across_all_the_sessions(engine: Engine) -> None:
    gravar(engine, "s1", "a", input_tokens=100, output_tokens=20, usuario="ana")
    gravar(engine, "s2", "b", input_tokens=50, output_tokens=5, usuario="ana")
    gravar(engine, "s1", "c", input_tokens=999, output_tokens=999, usuario="bia")
    gravar(engine, "s3", "d", input_tokens=777, output_tokens=777)
    historico = HistoricoAuditoria(engine)

    token = usuario_da_requisicao.set("ana")
    try:
        assert asyncio.run(historico.tokens_used("s-nova")) == 175
    finally:
        usuario_da_requisicao.reset(token)
