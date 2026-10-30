from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, func, inspect, select, text
from sqlalchemy.orm import Session
from venergy_agent.domain.answer import AgentAnswer, AnswerStatus, Confidence

from venergy_api.agente import get_agente
from venergy_api.auditoria import gravar_auditoria
from venergy_api.auth import Perfil, UsuarioLogado
from venergy_api.database import Base
from venergy_api.estrutura_app import garantir_estrutura_do_app
from venergy_api.models import AiAuditoria
from venergy_api.sessao import usuario_atual

SESSAO = "3f2b8c1e-5d4a-4e7b-9a60-1c2d3e4f5a6b"
OUTRA_SESSAO = "9a8b7c6d-5e4f-4a3b-8c2d-1e0f9a8b7c6d"


def resposta() -> AgentAnswer:
    return AgentAnswer(
        answer="Há 3 UCs.",
        status=AnswerStatus.ANSWERED,
        sql="SELECT count(*) AS total FROM gold.sem_uc LIMIT 200",
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


def turno(engine: Engine, session_id: str, pergunta: str, usuario: str | None = "teste") -> None:
    with Session(engine) as session:
        gravar_auditoria(session, pergunta, session_id, resposta(), usuario)


def como(client: TestClient, login: str, perfil: Perfil = Perfil.TI) -> TestClient:
    usuario = UsuarioLogado(login=login, nome=login, perfil=perfil)
    client.app.dependency_overrides[usuario_atual] = lambda: usuario
    return client


@pytest.fixture
def api(engine: Engine, client_for: Callable[[Engine], TestClient]) -> TestClient:
    Base.metadata.create_all(engine)
    return client_for(engine)


def test_lists_only_the_user_sessions_with_their_turns_in_order(
    api: TestClient, engine: Engine
) -> None:
    turno(engine, SESSAO, "Quantas UCs existem?")
    turno(engine, SESSAO, "E em Olinda?")
    turno(engine, OUTRA_SESSAO, "Pergunta alheia", "outra.pessoa")

    corpo = api.get("/ai/sessions").json()

    assert [sessao["session_id"] for sessao in corpo] == [SESSAO]
    assert corpo[0]["titulo"] == "Quantas UCs existem?"
    assert corpo[0]["favorita"] is False
    assert [t["pergunta"] for t in corpo[0]["turnos"]] == ["Quantas UCs existem?", "E em Olinda?"]
    assert corpo[0]["turnos"][0]["answer"] == "Há 3 UCs."


def test_long_first_question_is_shortened_in_the_default_title(
    api: TestClient, engine: Engine
) -> None:
    turno(engine, SESSAO, "x" * 200)

    assert len(api.get("/ai/sessions").json()[0]["titulo"]) == 80


def test_patch_renames_and_favorites_and_keeps_the_other_field(
    api: TestClient, engine: Engine
) -> None:
    turno(engine, SESSAO, "Pergunta")

    assert (
        api.patch(f"/ai/sessions/{SESSAO}", json={"titulo": "  Receita "}).json()["titulo"]
        == "Receita"
    )
    corpo = api.patch(f"/ai/sessions/{SESSAO}", json={"favorita": True}).json()

    assert corpo["titulo"] == "Receita"
    assert corpo["favorita"] is True
    assert api.get("/ai/sessions").json()[0]["favorita"] is True


@pytest.mark.parametrize(
    "corpo", [{}, {"titulo": None}, {"titulo": "   "}, {"titulo": "x" * 121}, {"favorita": None}]
)
def test_patch_rejects_an_empty_or_invalid_change(
    api: TestClient, engine: Engine, corpo: dict[str, object]
) -> None:
    turno(engine, SESSAO, "Pergunta")

    assert api.patch(f"/ai/sessions/{SESSAO}", json=corpo).status_code == 422


@pytest.mark.parametrize("dono", ["outra.pessoa", None])
def test_session_of_someone_else_answers_404_and_changes_nothing(
    api: TestClient, engine: Engine, dono: str | None
) -> None:
    turno(engine, SESSAO, "Pergunta", dono)

    assert api.patch(f"/ai/sessions/{SESSAO}", json={"favorita": True}).status_code == 404
    assert api.delete(f"/ai/sessions/{SESSAO}").status_code == 404
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM app.ai_sessao")) == 0


def test_unknown_session_answers_404(api: TestClient) -> None:
    assert api.delete(f"/ai/sessions/{SESSAO}").status_code == 404


def test_delete_hides_the_session_and_keeps_the_audit(api: TestClient, engine: Engine) -> None:
    turno(engine, SESSAO, "Pergunta")

    assert api.delete(f"/ai/sessions/{SESSAO}").status_code == 204

    assert api.get("/ai/sessions").json() == []
    assert api.delete(f"/ai/sessions/{SESSAO}").status_code == 404
    assert api.patch(f"/ai/sessions/{SESSAO}", json={"favorita": True}).status_code == 404
    with Session(engine) as session:
        audit_id = session.scalar(select(func.min(AiAuditoria.id)))
    assert como(api, "ti").get(f"/ai/audit/{audit_id}").status_code == 200


def test_deleted_session_cannot_receive_new_questions(api: TestClient, engine: Engine) -> None:
    class Agente:
        chamadas = 0

        async def ask(self, question: str, session_id: str) -> AgentAnswer:
            Agente.chamadas += 1
            return resposta()

    api.app.dependency_overrides[get_agente] = Agente
    turno(engine, SESSAO, "Pergunta")
    api.delete(f"/ai/sessions/{SESSAO}")

    pedido = api.post("/ai/ask", json={"question": "Mais uma", "session_id": SESSAO})

    assert pedido.status_code == 409
    assert Agente.chamadas == 0


def test_invalid_session_id_answers_422(api: TestClient) -> None:
    assert api.delete("/ai/sessions/nao-e-uuid").status_code == 422


def test_routes_require_login(engine: Engine, client_for: Callable[..., TestClient]) -> None:
    Base.metadata.create_all(engine)

    assert client_for(engine, sem_login=True).get("/ai/sessions").status_code == 401


def test_old_database_gets_the_session_table(engine: Engine) -> None:
    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(text("DROP TABLE app.ai_sessao"))
        garantir_estrutura_do_app(connection)

    assert inspect(engine).has_table("ai_sessao", schema="app")
