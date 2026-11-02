import asyncio
from collections.abc import AsyncIterator, Callable, Iterator

import pytest
from fastapi.testclient import TestClient
from opentelemetry.instrumentation.psycopg import PsycopgInstrumentor
from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import SpanKind
from pydantic_ai import Agent
from pydantic_ai.models.test import TestModel
from sqlalchemy import Engine
from venergy_agent.domain.answer import AgentAnswer, AnswerStatus, Confidence
from venergy_agent.domain.events import AnswerEvent, Stage, StageEvent

from venergy_api.agente import get_agente
from venergy_api.auth import Perfil
from venergy_api.database import Base
from venergy_api.rastreamento import configurar_rastreamento

PERGUNTA = "Qual foi a receita faturada em 2024-06?"
SESSAO = "3f2b8c1e-5d4a-4e7b-9a60-1c2d3e4f5a6b"


def resposta() -> AgentAnswer:
    return AgentAnswer(
        answer="A receita faturada de 2024-06 foi de R$ 1.234,50.",
        status=AnswerStatus.ANSWERED,
        sql="SELECT competencia, receita_faturada FROM semantic.sem_kpis_mensais LIMIT 200",
        rows=({"competencia": "2024-06", "receita_faturada": 1234.5},),
        row_count=1,
        truncated=False,
        confidence=Confidence.HIGH,
        sources=("sem_kpis_mensais",),
        assumptions=(),
        clarification=None,
        refused_reason=None,
        request_id="req-rastreada",
        model="google-gla:gemini-3.1-flash-lite",
        prompt_version="v3",
        latency_ms=850,
        input_tokens=1200,
        output_tokens=80,
    )


class AgenteFalso:
    async def ask(self, question: str, session_id: str) -> AgentAnswer:
        return resposta()

    async def stream(self, question: str, session_id: str) -> AsyncIterator[object]:
        yield StageEvent(stage=Stage.QUERYING, attempt=1)
        yield AnswerEvent(answer=resposta())


@pytest.fixture
def perfil() -> Perfil:
    return Perfil.TI


@pytest.fixture
def spans() -> Iterator[InMemorySpanExporter]:
    memoria = InMemorySpanExporter()
    yield memoria
    # O psycopg e o PydanticAI são instrumentados no processo inteiro, e não só neste app.
    PsycopgInstrumentor().uninstrument()
    Agent.instrument_all(False)


@pytest.fixture
def rastreado(
    engine: Engine,
    client_for: Callable[[Engine], TestClient],
    spans: InMemorySpanExporter,
) -> Callable[[], tuple[TestClient, TracerProvider]]:
    def build() -> tuple[TestClient, TracerProvider]:
        Base.metadata.create_all(engine)
        client = client_for(engine)
        client.app.dependency_overrides[get_agente] = lambda: AgenteFalso()
        provider = configurar_rastreamento(
            client.app, client.app.state.settings, SimpleSpanProcessor(spans)
        )
        # As conexões abertas antes da instrumentação não passam por ela.
        engine.dispose()
        return client, provider

    return build


def requisicao(spans: InMemorySpanExporter) -> ReadableSpan:
    [span] = [s for s in spans.get_finished_spans() if s.kind is SpanKind.SERVER]
    return span


def consultas(spans: InMemorySpanExporter) -> list[ReadableSpan]:
    return [s for s in spans.get_finished_spans() if s.attributes.get("db.system") == "postgresql"]


# No stream, o span é lido de dentro do gerador que a resposta percorre, e não da rota: é onde o
# contexto da requisição poderia se perder.
@pytest.mark.parametrize("rota", ["/ai/ask", "/ai/ask/stream"])
def test_the_agent_answer_goes_to_the_request_span(
    rota: str,
    rastreado: Callable[[], tuple[TestClient, TracerProvider]],
    spans: InMemorySpanExporter,
) -> None:
    client, _ = rastreado()

    response = client.post(rota, json={"question": PERGUNTA, "session_id": SESSAO})

    assert response.status_code == 200, response.text
    atributos = requisicao(spans).attributes
    assert atributos["venergy.ai.request_id"] == "req-rastreada"
    assert atributos["venergy.ai.status"] == "answered"
    assert atributos["venergy.ai.row_count"] == 1
    assert (atributos["venergy.ai.input_tokens"], atributos["venergy.ai.output_tokens"]) == (
        1200,
        80,
    )


def test_database_queries_are_children_of_the_request(
    rastreado: Callable[[], tuple[TestClient, TracerProvider]], spans: InMemorySpanExporter
) -> None:
    client, _ = rastreado()

    client.post("/ai/ask", json={"question": PERGUNTA, "session_id": SESSAO})

    rota = requisicao(spans)
    sqls = consultas(spans)
    assert any("INSERT" in s.attributes["db.statement"] for s in sqls)
    assert {s.context.trace_id for s in sqls} == {rota.context.trace_id}
    assert {s.parent.span_id for s in sqls} == {rota.context.span_id}


def test_health_leaves_no_trace_not_even_its_query(
    rastreado: Callable[[], tuple[TestClient, TracerProvider]], spans: InMemorySpanExporter
) -> None:
    client, _ = rastreado()

    response = client.get("/health")

    assert response.status_code == 200
    assert spans.get_finished_spans() == ()


def test_the_live_orders_stream_leaves_no_trace(
    rastreado: Callable[[], tuple[TestClient, TracerProvider]], spans: InMemorySpanExporter
) -> None:
    client, _ = rastreado()

    # POST, e não GET: a rota do tempo real só aceita GET e abriria um stream sem fim. O filtro
    # olha só a URL, então qualquer método nela tem que ficar fora do rastreamento.
    response = client.post("/ordens-inspecao/eventos")

    assert response.status_code in (404, 405)
    assert spans.get_finished_spans() == ()


def test_model_spans_carry_no_question_prompt_or_answer(
    rastreado: Callable[[], tuple[TestClient, TracerProvider]], spans: InMemorySpanExporter
) -> None:
    _, provider = rastreado()
    agente = Agent(
        TestModel(custom_output_text="resposta-sigilosa"), system_prompt="prompt-sigiloso"
    )

    # Dentro de uma requisição, como no /ai/ask: fora dela, o sampler descarta o trace.
    with provider.get_tracer("teste").start_as_current_span("POST /ai/ask", kind=SpanKind.SERVER):
        asyncio.run(agente.run("pergunta-sigilosa"))

    exportado = str(
        [(s.attributes, [e.attributes for e in s.events]) for s in spans.get_finished_spans()]
    )
    assert any(s.attributes.get("gen_ai.request.model") for s in spans.get_finished_spans())
    for sigilo in ("pergunta-sigilosa", "prompt-sigiloso", "resposta-sigilosa"):
        assert sigilo not in exportado


def test_without_an_endpoint_tracing_stays_off(
    engine: Engine, client_for: Callable[[Engine], TestClient]
) -> None:
    client = client_for(engine)

    assert client.app.state.settings.rastreamento_endpoint is None
    assert client.app.state.rastreamento is None
    assert configurar_rastreamento(client.app, client.app.state.settings) is None
