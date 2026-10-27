from collections.abc import Callable
from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, func, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session
from venergy_agent.domain.answer import AgentAnswer, AnswerStatus, Confidence

from venergy_api.agente import get_agente
from venergy_api.database import Base
from venergy_api.models import AiAuditoria
from venergy_api.schemas import MAX_PERGUNTA_IA, MAX_SESSAO_IA

PERGUNTA = "Qual foi a receita faturada em 2024-06?"


class AgenteFalso:
    """Devolve a resposta combinada, sem chamar o Gemini, e guarda o que recebeu."""

    def __init__(self, answer: AgentAnswer) -> None:
        self.answer = answer
        self.chamadas: list[tuple[str, str]] = []

    async def ask(self, question: str, session_id: str) -> AgentAnswer:
        self.chamadas.append((question, session_id))
        return self.answer


def answered_answer() -> AgentAnswer:
    return AgentAnswer(
        answer="A receita faturada de 2024-06 foi de R$ 1.234,50.",
        status=AnswerStatus.ANSWERED,
        sql="SELECT competencia, receita_faturada FROM gold.sem_kpis_mensais LIMIT 200",
        rows=(
            {
                "competencia": "2024-06",
                "receita_faturada": Decimal("1234.50"),
                "fechamento": date(2024, 6, 30),
            },
        ),
        row_count=1,
        truncated=False,
        confidence=Confidence.HIGH,
        sources=("sem_kpis_mensais",),
        assumptions=("Receita sem qualificador é a receita faturada.",),
        clarification=None,
        refused_reason=None,
        request_id="req-answered",
        model="google-gla:gemini-3.1-flash-lite",
        prompt_version="v2",
        latency_ms=850,
    )


def refused_answer() -> AgentAnswer:
    return AgentAnswer(
        answer="Só respondo perguntas sobre consumo, faturamento, interrupções e atendimento.",
        status=AnswerStatus.REFUSED,
        sql=None,
        rows=(),
        row_count=0,
        truncated=False,
        confidence=Confidence.UNKNOWN,
        sources=(),
        assumptions=(),
        clarification=None,
        refused_reason="Pergunta fora do escopo da V-Energy.",
        request_id="req-refused",
        model="google-gla:gemini-3.1-flash-lite",
        prompt_version="v2",
        latency_ms=210,
    )


@pytest.fixture(autouse=True)
def audit_table(engine: Engine) -> None:
    Base.metadata.create_all(engine)


@pytest.fixture
def client_with_agent(
    engine: Engine, client_for: Callable[[Engine], TestClient]
) -> Callable[[AgentAnswer], tuple[TestClient, AgenteFalso]]:
    def build(answer: AgentAnswer) -> tuple[TestClient, AgenteFalso]:
        client = client_for(engine)
        agente = AgenteFalso(answer)
        client.app.dependency_overrides[get_agente] = lambda: agente
        return client, agente

    return build


def stored_audits(engine: Engine) -> list[AiAuditoria]:
    with Session(engine) as session:
        return list(session.scalars(select(AiAuditoria).order_by(AiAuditoria.id)))


def test_answers_and_returns_the_audit_id(
    engine: Engine, client_with_agent: Callable[[AgentAnswer], tuple[TestClient, AgenteFalso]]
) -> None:
    client, agente = client_with_agent(answered_answer())

    response = client.post("/ai/ask", json={"question": PERGUNTA, "session_id": "sessao-1"})

    assert response.status_code == 200, response.text
    corpo = response.json()
    [auditoria] = stored_audits(engine)
    assert corpo["audit_id"] == auditoria.id
    assert corpo["status"] == "answered"
    assert corpo["answer"] == "A receita faturada de 2024-06 foi de R$ 1.234,50."
    assert corpo["sources"] == ["sem_kpis_mensais"]
    assert corpo["confidence"] == "high"
    assert corpo["request_id"] == "req-answered"
    assert agente.chamadas == [(PERGUNTA, "sessao-1")]


def test_stores_every_field_of_the_answer_with_exact_values(
    engine: Engine, client_with_agent: Callable[[AgentAnswer], tuple[TestClient, AgenteFalso]]
) -> None:
    client, _ = client_with_agent(answered_answer())

    client.post("/ai/ask", json={"question": PERGUNTA, "session_id": "sessao-1"})

    [auditoria] = stored_audits(engine)
    assert auditoria.pergunta == PERGUNTA
    assert auditoria.session_id == "sessao-1"
    assert auditoria.criado_em is not None
    assert auditoria.sql == (
        "SELECT competencia, receita_faturada FROM gold.sem_kpis_mensais LIMIT 200"
    )
    # Decimal e date viram texto no JSONB: o valor exato da consulta fica guardado.
    assert auditoria.rows == [
        {"competencia": "2024-06", "receita_faturada": "1234.50", "fechamento": "2024-06-30"}
    ]
    assert auditoria.row_count == 1
    assert auditoria.truncated is False
    assert auditoria.assumptions == ["Receita sem qualificador é a receita faturada."]
    assert auditoria.model == "google-gla:gemini-3.1-flash-lite"
    assert auditoria.prompt_version == "v2"
    assert auditoria.latency_ms == 850


def test_stores_a_refused_answer_with_its_reason(
    engine: Engine, client_with_agent: Callable[[AgentAnswer], tuple[TestClient, AgenteFalso]]
) -> None:
    client, _ = client_with_agent(refused_answer())

    response = client.post("/ai/ask", json={"question": "Me conta uma piada", "session_id": "s"})

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "refused"
    [auditoria] = stored_audits(engine)
    assert auditoria.status == "refused"
    assert auditoria.refused_reason == "Pergunta fora do escopo da V-Energy."
    assert auditoria.sql is None
    assert auditoria.rows == []


def test_without_an_agent_answers_503_and_stores_nothing(
    engine: Engine, client_for: Callable[[Engine], TestClient]
) -> None:
    # Sem o lifespan e sem override, o app não tem agente: o mesmo caso da chave ausente.
    client = client_for(engine)

    response = client.post("/ai/ask", json={"question": PERGUNTA, "session_id": "sessao-1"})

    assert response.status_code == 503
    assert "VENERGY_AGENT_GOOGLE_API_KEY" in response.json()["detail"]
    assert stored_audits(engine) == []


@pytest.mark.parametrize(
    "corpo",
    [
        {"question": "x" * (MAX_PERGUNTA_IA + 1), "session_id": "s"},
        {"question": PERGUNTA, "session_id": "s" * (MAX_SESSAO_IA + 1)},
        {"question": "   ", "session_id": "s"},
        {"question": PERGUNTA, "session_id": ""},
        {"question": PERGUNTA},
    ],
)
def test_rejects_an_invalid_request_without_calling_the_agent(
    engine: Engine,
    client_with_agent: Callable[[AgentAnswer], tuple[TestClient, AgenteFalso]],
    corpo: dict[str, str],
) -> None:
    client, agente = client_with_agent(answered_answer())

    response = client.post("/ai/ask", json=corpo)

    assert response.status_code == 422
    assert agente.chamadas == []
    assert stored_audits(engine) == []


def test_does_not_deliver_the_answer_when_the_audit_cannot_be_stored(
    engine: Engine,
    client_with_agent: Callable[[AgentAnswer], tuple[TestClient, AgenteFalso]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _ = client_with_agent(answered_answer())

    def gravar_com_falha(*args: object) -> None:
        raise OperationalError("INSERT INTO app.ai_auditoria ...", {"pergunta": PERGUNTA}, None)

    monkeypatch.setattr("venergy_api.routers.ai.gravar_auditoria", gravar_com_falha)

    response = client.post("/ai/ask", json={"question": PERGUNTA, "session_id": "sessao-1"})

    assert response.status_code == 500
    assert "R$ 1.234,50" not in response.text
    assert PERGUNTA not in response.text


def test_each_question_gets_its_own_audit_record(
    engine: Engine, client_with_agent: Callable[[AgentAnswer], tuple[TestClient, AgenteFalso]]
) -> None:
    client, _ = client_with_agent(answered_answer())

    primeira = client.post("/ai/ask", json={"question": PERGUNTA, "session_id": "s"}).json()
    segunda = client.post("/ai/ask", json={"question": PERGUNTA, "session_id": "s"}).json()

    assert primeira["audit_id"] != segunda["audit_id"]
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(AiAuditoria)) == 2
