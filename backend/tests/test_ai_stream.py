import asyncio
import json
from collections.abc import AsyncIterator, Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session
from venergy_agent.domain.answer import AgentAnswer, AnswerStatus, Confidence
from venergy_agent.domain.events import AnswerEvent, Stage, StageEvent

from venergy_api.agente import get_agente
from venergy_api.auditoria import gravar_auditoria
from venergy_api.auth import Perfil, UsuarioLogado
from venergy_api.database import Base
from venergy_api.models import AiAuditoria
from venergy_api.routers import ai as rota_ai
from venergy_api.routers.ai import _eventos

SESSAO = "3f2b8c1e-5d4a-4e7b-9a60-1c2d3e4f5a6b"
URL = "/ai/ask/stream"


def resposta() -> AgentAnswer:
    return AgentAnswer(
        answer="Há 3 UCs.",
        status=AnswerStatus.ANSWERED,
        sql="SELECT 1",
        rows=({"total": 3},),
        row_count=1,
        truncated=False,
        confidence=Confidence.HIGH,
        sources=("sem_uc",),
        assumptions=(),
        clarification=None,
        refused_reason=None,
        request_id="req-1",
        model="modelo",
        prompt_version="v3",
        latency_ms=10,
    )


class AgenteFalso:
    def __init__(self) -> None:
        self.chamadas = 0

    async def stream(self, question: str, session_id: str) -> AsyncIterator[object]:
        self.chamadas += 1
        yield StageEvent(stage=Stage.UNDERSTANDING, attempt=1)
        yield StageEvent(stage=Stage.QUERYING, attempt=1)
        yield AnswerEvent(answer=resposta())


class AgenteQueTrava:
    def __init__(self) -> None:
        self.fechado = False

    async def stream(self, question: str, session_id: str) -> AsyncIterator[object]:
        try:
            yield StageEvent(stage=Stage.QUERYING, attempt=1, input_tokens=500, output_tokens=40)
            await asyncio.Event().wait()
        finally:
            self.fechado = True


def mensagens(corpo: str) -> list[tuple[str, dict[str, object]]]:
    saida = []
    for bloco in corpo.strip().split("\n\n"):
        linhas = bloco.split("\n")
        if linhas[0].startswith(":"):
            continue
        saida.append(
            (linhas[0].removeprefix("event: "), json.loads(linhas[1].removeprefix("data: ")))
        )
    return saida


@pytest.fixture
def api(engine: Engine, client_for: Callable[..., TestClient]) -> TestClient:
    Base.metadata.create_all(engine)
    return client_for(engine)


def test_streams_the_stages_then_the_audited_answer(api: TestClient, engine: Engine) -> None:
    api.app.dependency_overrides[get_agente] = AgenteFalso

    resposta_http = api.post(URL, json={"question": "Quantas UCs?", "session_id": SESSAO})

    assert resposta_http.status_code == 200
    assert resposta_http.headers["content-type"].startswith("text/event-stream")
    assert resposta_http.headers["x-accel-buffering"] == "no"
    eventos = mensagens(resposta_http.text)
    assert [nome for nome, _ in eventos] == ["stage", "stage", "answer"]
    assert eventos[0][1]["label"] == "Entendendo a pergunta"
    final = eventos[-1][1]["answer"]
    assert final["session_id"] == SESSAO
    with Session(engine) as session:
        auditoria = session.scalars(select(AiAuditoria)).one()
    assert final["audit_id"] == auditoria.id
    assert auditoria.usuario == "teste"
    assert auditoria.pergunta == "Quantas UCs?"


def test_session_of_someone_else_answers_403_without_opening_the_stream(
    api: TestClient, engine: Engine
) -> None:
    agente = AgenteFalso()
    api.app.dependency_overrides[get_agente] = lambda: agente
    with Session(engine) as session:
        gravar_auditoria(session, "x", SESSAO, resposta(), "outra.pessoa")

    resposta_http = api.post(URL, json={"question": "Mais uma", "session_id": SESSAO})

    assert resposta_http.status_code == 403
    assert agente.chamadas == 0


def test_limit_answers_429_without_opening_the_stream(
    engine: Engine, client_for: Callable[..., TestClient]
) -> None:
    Base.metadata.create_all(engine)
    api = client_for(engine, ai_limite_perguntas=1)
    agente = AgenteFalso()
    api.app.dependency_overrides[get_agente] = lambda: agente
    with Session(engine) as session:
        gravar_auditoria(session, "x", SESSAO, resposta(), "teste")

    assert api.post(URL, json={"question": "Mais uma"}).status_code == 429
    assert agente.chamadas == 0


def test_without_an_agent_answers_503(api: TestClient) -> None:
    assert api.post(URL, json={"question": "Quantas UCs?"}).status_code == 503


def test_sends_a_ping_while_the_agent_is_silent(
    api: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    class AgenteLento(AgenteFalso):
        async def stream(self, question: str, session_id: str) -> AsyncIterator[object]:
            await asyncio.sleep(0.05)
            yield AnswerEvent(answer=resposta())

    monkeypatch.setattr(rota_ai, "INTERVALO_PING_SEGUNDOS", 0.01)
    api.app.dependency_overrides[get_agente] = AgenteLento

    assert ": ping" in api.post(URL, json={"question": "Quantas UCs?"}).text


def test_disconnect_closes_the_agent_and_counts_the_question(
    api: TestClient, engine: Engine
) -> None:
    agente = AgenteQueTrava()
    usuario = UsuarioLogado(login="teste", nome="Teste", perfil=Perfil.PERDAS)
    request = type("Pedido", (), {"app": api.app})()

    async def desconectar() -> None:
        eventos = _eventos("Pergunta", SESSAO, agente, Session(engine), request, usuario)
        async with asyncio.timeout(2):
            assert (await anext(eventos)).startswith("event: stage")
            await eventos.aclose()

    asyncio.run(desconectar())

    assert agente.fechado is True
    assert not rota_ai.trava_do_usuario(api.app, "teste").locked()
    with Session(engine) as session:
        auditoria = session.scalars(select(AiAuditoria)).one()
    assert auditoria.status == "failed"
    assert (auditoria.input_tokens, auditoria.output_tokens) == (500, 40)
    assert auditoria.usuario == "teste"
