import asyncio
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, func, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session
from venergy_agent.domain.answer import AgentAnswer, AnswerStatus, Confidence
from venergy_agent.domain.conversation import ConversationTurn

from venergy_api.agente import get_agente
from venergy_api.auditoria import gravar_auditoria
from venergy_api.auth import Perfil, UsuarioLogado
from venergy_api.database import Base
from venergy_api.historico_ia import HistoricoAuditoria, usuario_da_requisicao
from venergy_api.models import AiAuditoria
from venergy_api.schemas import MAX_PERGUNTA_IA
from venergy_api.sessao import usuario_atual

PERGUNTA = "Qual foi a receita faturada em 2024-06?"
SESSAO = "3f2b8c1e-5d4a-4e7b-9a60-1c2d3e4f5a6b"
OUTRA_SESSAO = "9a8b7c6d-5e4f-4a3b-8c2d-1e0f9a8b7c6d"
USUARIO = "teste"
OUTRO_USUARIO = "outra.pessoa"


class AgenteFalso:
    """Devolve a resposta combinada, sem chamar o Gemini, e guarda o que recebeu."""

    def __init__(self, answer: AgentAnswer) -> None:
        self.answer = answer
        self.chamadas: list[tuple[str, str]] = []

    async def ask(self, question: str, session_id: str) -> AgentAnswer:
        self.chamadas.append((question, session_id))
        return self.answer


class AgenteQueMedeConexoes(AgenteFalso):
    def __init__(self, answer: AgentAnswer, engine: Engine) -> None:
        super().__init__(answer)
        self._engine = engine
        self.conexoes_ao_responder: int | None = None

    async def ask(self, question: str, session_id: str) -> AgentAnswer:
        self.conexoes_ao_responder = self._engine.pool.checkedout()
        return await super().ask(question, session_id)


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
        input_tokens=1200,
        output_tokens=80,
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


@pytest.fixture
def perfil() -> Perfil:
    # Os testes deste arquivo leem a auditoria, e só a TI pode (DEC-049).
    return Perfil.TI


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

    response = client.post("/ai/ask", json={"question": PERGUNTA, "session_id": SESSAO})

    assert response.status_code == 200, response.text
    corpo = response.json()
    [auditoria] = stored_audits(engine)
    assert corpo["audit_id"] == auditoria.id
    assert corpo["status"] == "answered"
    assert corpo["answer"] == "A receita faturada de 2024-06 foi de R$ 1.234,50."
    assert corpo["sources"] == ["sem_kpis_mensais"]
    assert corpo["confidence"] == "high"
    assert corpo["request_id"] == "req-answered"
    assert (corpo["input_tokens"], corpo["output_tokens"]) == (1200, 80)
    assert agente.chamadas == [(PERGUNTA, SESSAO)]


def test_stores_every_field_of_the_answer_with_exact_values(
    engine: Engine, client_with_agent: Callable[[AgentAnswer], tuple[TestClient, AgenteFalso]]
) -> None:
    client, _ = client_with_agent(answered_answer())

    client.post("/ai/ask", json={"question": PERGUNTA, "session_id": SESSAO})

    [auditoria] = stored_audits(engine)
    assert auditoria.pergunta == PERGUNTA
    assert auditoria.session_id == SESSAO
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
    assert (auditoria.input_tokens, auditoria.output_tokens) == (1200, 80)


def test_stores_a_refused_answer_with_its_reason(
    engine: Engine, client_with_agent: Callable[[AgentAnswer], tuple[TestClient, AgenteFalso]]
) -> None:
    client, _ = client_with_agent(refused_answer())

    response = client.post("/ai/ask", json={"question": "Me conta uma piada", "session_id": SESSAO})

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

    response = client.post("/ai/ask", json={"question": PERGUNTA, "session_id": SESSAO})

    assert response.status_code == 503
    assert "VENERGY_AGENT_GOOGLE_API_KEY" in response.json()["detail"]
    assert stored_audits(engine) == []


@pytest.mark.parametrize(
    "corpo",
    [
        {"question": "x" * (MAX_PERGUNTA_IA + 1), "session_id": SESSAO},
        {"question": PERGUNTA, "session_id": "sessao-1"},
        {"question": PERGUNTA, "session_id": "s" * 200},
        {"question": "   ", "session_id": SESSAO},
        {"question": PERGUNTA, "session_id": ""},
        {"question": PERGUNTA, "session_id": 123},
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
    client_with_agent: Callable[[AgentAnswer], tuple[TestClient, AgenteFalso]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _ = client_with_agent(answered_answer())

    def gravar_com_falha(*args: object) -> None:
        raise OperationalError("INSERT INTO app.ai_auditoria ...", {"pergunta": PERGUNTA}, None)

    monkeypatch.setattr("venergy_api.routers.ai.gravar_auditoria", gravar_com_falha)

    response = client.post("/ai/ask", json={"question": PERGUNTA, "session_id": SESSAO})

    assert response.status_code == 500
    assert "R$ 1.234,50" not in response.text
    assert PERGUNTA not in response.text


def test_audit_returns_what_the_post_answered(
    client_with_agent: Callable[[AgentAnswer], tuple[TestClient, AgenteFalso]],
) -> None:
    client, _ = client_with_agent(answered_answer())
    resposta = client.post("/ai/ask", json={"question": PERGUNTA, "session_id": SESSAO}).json()

    response = client.get(f"/ai/audit/{resposta['audit_id']}")

    assert response.status_code == 200, response.text
    auditoria = response.json()
    # Tudo o que o POST entregou volta igual, inclusive a amostra com Decimal e data.
    # A auditoria não expõe o session_id: ele só volta na resposta do POST.
    assert {campo: auditoria[campo] for campo in resposta if campo != "session_id"} == {
        campo: valor for campo, valor in resposta.items() if campo != "session_id"
    }
    assert resposta["session_id"] == SESSAO
    assert auditoria["pergunta"] == PERGUNTA
    assert auditoria["criado_em"]
    assert auditoria["sql"].startswith("SELECT competencia")
    assert auditoria["rows"][0]["receita_faturada"] == "1234.50"


def test_audit_of_a_refused_answer_shows_the_reason(
    client_with_agent: Callable[[AgentAnswer], tuple[TestClient, AgenteFalso]],
) -> None:
    client, _ = client_with_agent(refused_answer())
    resposta = client.post("/ai/ask", json={"question": "Me conta uma piada", "session_id": SESSAO})

    auditoria = client.get(f"/ai/audit/{resposta.json()['audit_id']}").json()

    assert auditoria["status"] == "refused"
    assert auditoria["refused_reason"] == "Pergunta fora do escopo da V-Energy."
    assert auditoria["sql"] is None


def test_audit_is_readable_without_the_agent(
    engine: Engine, client_for: Callable[[Engine], TestClient]
) -> None:
    # Ler a trilha não depende da chave do Gemini: o histórico continua consultável.
    with Session(engine) as session:
        gravar_auditoria(session, PERGUNTA, SESSAO, answered_answer(), USUARIO)
    [auditoria] = stored_audits(engine)

    response = client_for(engine).get(f"/ai/audit/{auditoria.id}")

    assert response.status_code == 200
    assert response.json()["audit_id"] == auditoria.id


def test_audit_not_found_answers_404(
    client_with_agent: Callable[[AgentAnswer], tuple[TestClient, AgenteFalso]],
) -> None:
    client, _ = client_with_agent(answered_answer())

    response = client.get("/ai/audit/999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Registro de auditoria 999 não encontrado"}


@pytest.mark.parametrize("audit_id", ["0", "-1", "2147483648", "abc"])
def test_audit_rejects_an_id_the_table_cannot_hold(
    client_with_agent: Callable[[AgentAnswer], tuple[TestClient, AgenteFalso]], audit_id: str
) -> None:
    client, _ = client_with_agent(answered_answer())

    assert client.get(f"/ai/audit/{audit_id}").status_code == 422


def test_each_question_gets_its_own_audit_record(
    engine: Engine, client_with_agent: Callable[[AgentAnswer], tuple[TestClient, AgenteFalso]]
) -> None:
    client, _ = client_with_agent(answered_answer())

    primeira = client.post("/ai/ask", json={"question": PERGUNTA, "session_id": SESSAO}).json()
    segunda = client.post("/ai/ask", json={"question": PERGUNTA, "session_id": SESSAO}).json()

    assert primeira["audit_id"] != segunda["audit_id"]
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(AiAuditoria)) == 2


def gravar_perguntas(
    engine: Engine,
    session_id: str,
    quantas: int,
    minutos_atras: int = 0,
    usuario: str | None = USUARIO,
) -> None:
    with Session(engine) as session:
        for _ in range(quantas):
            auditoria = gravar_auditoria(session, PERGUNTA, session_id, answered_answer(), usuario)
            auditoria.criado_em = datetime.now(UTC) - timedelta(minutes=minutos_atras)
            session.commit()


@pytest.fixture
def client_with_limit(
    engine: Engine, client_for: Callable[..., TestClient]
) -> Callable[[int], tuple[TestClient, AgenteFalso]]:
    def build(limite: int) -> tuple[TestClient, AgenteFalso]:
        client = client_for(engine, ai_limite_perguntas=limite, ai_janela_segundos=600)
        agente = AgenteFalso(answered_answer())
        client.app.dependency_overrides[get_agente] = lambda: agente
        return client, agente

    return build


def test_answers_429_when_the_session_reached_the_limit_in_the_window(
    engine: Engine, client_with_limit: Callable[[int], tuple[TestClient, AgenteFalso]]
) -> None:
    client, agente = client_with_limit(2)
    gravar_perguntas(engine, SESSAO, 2)

    response = client.post("/ai/ask", json={"question": PERGUNTA, "session_id": SESSAO})

    assert response.status_code == 429
    assert response.headers["Retry-After"] == "600"
    assert "limite" in response.json()["detail"].lower()
    assert agente.chamadas == []
    assert len(stored_audits(engine)) == 2


def test_questions_older_than_the_window_and_other_users_do_not_count(
    engine: Engine, client_with_limit: Callable[[int], tuple[TestClient, AgenteFalso]]
) -> None:
    client, agente = client_with_limit(2)
    gravar_perguntas(engine, SESSAO, 1)
    gravar_perguntas(engine, SESSAO, 5, minutos_atras=60)
    gravar_perguntas(engine, OUTRA_SESSAO, 5, usuario=OUTRO_USUARIO)

    response = client.post("/ai/ask", json={"question": PERGUNTA, "session_id": SESSAO})

    assert response.status_code == 200, response.text
    assert len(agente.chamadas) == 1


def test_limit_zero_turns_the_check_off(
    engine: Engine, client_with_limit: Callable[[int], tuple[TestClient, AgenteFalso]]
) -> None:
    client, agente = client_with_limit(0)
    gravar_perguntas(engine, SESSAO, 30)

    response = client.post("/ai/ask", json={"question": PERGUNTA, "session_id": SESSAO})

    assert response.status_code == 200, response.text
    assert len(agente.chamadas) == 1


def test_generates_a_random_session_id_when_the_request_has_none(
    engine: Engine, client_with_agent: Callable[[AgentAnswer], tuple[TestClient, AgenteFalso]]
) -> None:
    client, agente = client_with_agent(answered_answer())

    primeira = client.post("/ai/ask", json={"question": PERGUNTA}).json()
    segunda = client.post("/ai/ask", json={"question": PERGUNTA}).json()

    gerados = [primeira["session_id"], segunda["session_id"]]
    assert gerados[0] != gerados[1]
    for gerado in gerados:
        assert UUID(gerado).version == 4
    assert [sessao for _, sessao in agente.chamadas] == gerados
    assert [auditoria.session_id for auditoria in stored_audits(engine)] == gerados


def test_echoes_the_session_id_sent_by_the_client(
    client_with_agent: Callable[[AgentAnswer], tuple[TestClient, AgenteFalso]],
) -> None:
    client, _ = client_with_agent(answered_answer())

    corpo = client.post("/ai/ask", json={"question": PERGUNTA, "session_id": SESSAO}).json()

    assert corpo["session_id"] == SESSAO


def test_answers_503_when_the_limit_cannot_be_checked_and_does_not_call_the_agent(
    engine: Engine,
    client_with_limit: Callable[[int], tuple[TestClient, AgenteFalso]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, agente = client_with_limit(2)

    def contador_quebrado(*args: object, **kwargs: object) -> int:
        raise OperationalError(
            "SELECT count(*) FROM app.ai_auditoria", {"sessao": SESSAO}, Exception()
        )

    monkeypatch.setattr("venergy_api.routers.ai.contar_perguntas_recentes", contador_quebrado)

    response = client.post("/ai/ask", json={"question": PERGUNTA, "session_id": SESSAO})

    assert response.status_code == 503
    assert agente.chamadas == []
    assert SESSAO not in response.text


def test_audit_does_not_expose_the_session_id(
    engine: Engine, client_for: Callable[[Engine], TestClient]
) -> None:
    with Session(engine) as session:
        gravar_auditoria(session, PERGUNTA, SESSAO, answered_answer(), USUARIO)
    [auditoria] = stored_audits(engine)

    response = client_for(engine).get(f"/ai/audit/{auditoria.id}")

    assert response.status_code == 200
    assert "session_id" not in response.json()


def test_the_request_releases_its_connection_before_calling_the_model(
    engine: Engine, client_for: Callable[..., TestClient]
) -> None:
    client = client_for(engine, ai_limite_perguntas=2, ai_janela_segundos=600)
    agente = AgenteQueMedeConexoes(answered_answer(), engine)
    client.app.dependency_overrides[get_agente] = lambda: agente

    response = client.post("/ai/ask", json={"question": PERGUNTA, "session_id": SESSAO})

    assert response.status_code == 200
    assert agente.conexoes_ao_responder == 0


def como(client: TestClient, login: str) -> TestClient:
    usuario = UsuarioLogado(login=login, nome=login, perfil=Perfil.TI)
    client.app.dependency_overrides[usuario_atual] = lambda: usuario
    return client


def test_stores_the_logged_user_in_the_audit(
    engine: Engine, client_with_agent: Callable[[AgentAnswer], tuple[TestClient, AgenteFalso]]
) -> None:
    client, _ = client_with_agent(answered_answer())

    client.post("/ai/ask", json={"question": PERGUNTA, "session_id": SESSAO})

    [auditoria] = stored_audits(engine)
    assert auditoria.usuario == USUARIO


def test_limit_counts_the_user_questions_across_sessions(
    engine: Engine, client_with_limit: Callable[[int], tuple[TestClient, AgenteFalso]]
) -> None:
    client, agente = client_with_limit(2)
    gravar_perguntas(engine, SESSAO, 1)
    gravar_perguntas(engine, OUTRA_SESSAO, 1)

    response = client.post("/ai/ask", json={"question": PERGUNTA, "session_id": str(uuid4())})

    assert response.status_code == 429
    assert agente.chamadas == []


def test_omitting_the_session_id_does_not_reset_the_limit(
    engine: Engine, client_with_limit: Callable[[int], tuple[TestClient, AgenteFalso]]
) -> None:
    client, agente = client_with_limit(2)
    gravar_perguntas(engine, SESSAO, 2)

    response = client.post("/ai/ask", json={"question": PERGUNTA})

    assert response.status_code == 429
    assert agente.chamadas == []


def test_another_user_has_the_own_limit(
    engine: Engine, client_with_limit: Callable[[int], tuple[TestClient, AgenteFalso]]
) -> None:
    client, agente = client_with_limit(2)
    gravar_perguntas(engine, SESSAO, 2)

    response = como(client, OUTRO_USUARIO).post("/ai/ask", json={"question": PERGUNTA})

    assert response.status_code == 200, response.text
    assert len(agente.chamadas) == 1


def test_answers_403_when_the_session_belongs_to_another_user(
    engine: Engine, client_with_agent: Callable[[AgentAnswer], tuple[TestClient, AgenteFalso]]
) -> None:
    client, agente = client_with_agent(answered_answer())
    gravar_perguntas(engine, SESSAO, 1, usuario=OUTRO_USUARIO)

    response = client.post("/ai/ask", json={"question": PERGUNTA, "session_id": SESSAO})

    assert response.status_code == 403
    assert "sessão" in response.json()["detail"].lower()
    assert agente.chamadas == []
    assert len(stored_audits(engine)) == 1


def test_a_session_without_an_owner_is_not_open_to_anyone(
    engine: Engine, client_with_agent: Callable[[AgentAnswer], tuple[TestClient, AgenteFalso]]
) -> None:
    client, agente = client_with_agent(answered_answer())
    gravar_perguntas(engine, SESSAO, 1, usuario=None)

    response = client.post("/ai/ask", json={"question": PERGUNTA, "session_id": SESSAO})

    assert response.status_code == 403
    assert agente.chamadas == []


def test_the_owner_keeps_using_the_own_session(
    engine: Engine, client_with_agent: Callable[[AgentAnswer], tuple[TestClient, AgenteFalso]]
) -> None:
    client, agente = client_with_agent(answered_answer())
    gravar_perguntas(engine, SESSAO, 1)

    response = client.post("/ai/ask", json={"question": PERGUNTA, "session_id": SESSAO})

    assert response.status_code == 200, response.text
    assert len(agente.chamadas) == 1


class AgenteQueLeOHistorico(AgenteFalso):
    """Lê o histórico da sessão pela mesma porta que o agente real usa (HistoricoAuditoria)."""

    def __init__(self, answer: AgentAnswer, engine: Engine) -> None:
        super().__init__(answer)
        self._historico = HistoricoAuditoria(lambda: engine)
        self.historicos_vistos: list[tuple[ConversationTurn, ...]] = []

    async def ask(self, question: str, session_id: str) -> AgentAnswer:
        self.historicos_vistos.append(await self._historico.recent(session_id, 3))
        return await super().ask(question, session_id)


def test_a_follow_up_in_the_same_session_sees_the_previous_turn(
    engine: Engine, client_for: Callable[[Engine], TestClient]
) -> None:
    client = client_for(engine)
    agente = AgenteQueLeOHistorico(answered_answer(), engine)
    client.app.dependency_overrides[get_agente] = lambda: agente

    client.post("/ai/ask", json={"question": PERGUNTA, "session_id": SESSAO})
    response = client.post("/ai/ask", json={"question": "E no mês anterior?", "session_id": SESSAO})

    assert response.status_code == 200, response.text
    assert agente.historicos_vistos[0] == ()
    assert [turno.question for turno in agente.historicos_vistos[1]] == [PERGUNTA]


class AgenteQueLeOUsuario(AgenteFalso):
    def __init__(self, answer: AgentAnswer) -> None:
        super().__init__(answer)
        self.usuario_visto: str | None = None

    async def ask(self, question: str, session_id: str) -> AgentAnswer:
        self.usuario_visto = usuario_da_requisicao.get()
        return await super().ask(question, session_id)


def test_the_agent_runs_with_the_requesting_user_and_the_context_is_cleared_after(
    engine: Engine, client_for: Callable[..., TestClient]
) -> None:
    client = client_for(engine)
    agente = AgenteQueLeOUsuario(answered_answer())
    client.app.dependency_overrides[get_agente] = lambda: agente

    client.post("/ai/ask", json={"question": PERGUNTA})

    assert agente.usuario_visto == USUARIO
    assert usuario_da_requisicao.get() is None


class AgenteLento(AgenteFalso):
    async def ask(self, question: str, session_id: str) -> AgentAnswer:
        await asyncio.sleep(0.3)
        return await super().ask(question, session_id)


def test_simultaneous_questions_of_the_same_user_cannot_pass_the_limit_together(
    engine: Engine, client_for: Callable[..., TestClient]
) -> None:
    client = client_for(engine, ai_limite_perguntas=1, ai_janela_segundos=600)
    agente = AgenteLento(answered_answer())
    client.app.dependency_overrides[get_agente] = lambda: agente

    with client, ThreadPoolExecutor(max_workers=2) as pool:
        respostas = list(
            pool.map(lambda _: client.post("/ai/ask", json={"question": PERGUNTA}), range(2))
        )

    assert sorted(r.status_code for r in respostas) == [200, 429]
    assert len(agente.chamadas) == 1
