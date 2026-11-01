"""Rastreamento opcional das requisições com OpenTelemetry (DEC-066).

Cada requisição vira um trace: a rota, as consultas ao Postgres (do backend e do agente) e as
chamadas ao modelo, cada uma com a sua duração. Sem `VENERGY_API_RASTREAMENTO_ENDPOINT`, nada é
instalado e a API responde como antes.
"""

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.psycopg import PsycopgInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import SpanProcessor, TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from pydantic_ai import Agent
from pydantic_ai.models.instrumented import InstrumentationSettings
from venergy_agent.domain.answer import AgentAnswer

from venergy_api.config import Settings

NOME_DO_SERVICO = "venergy-api"

# A saúde é chamada pelo healthcheck do compose a cada poucos segundos e encheria o painel. O
# tempo real das ordens é uma conexão aberta por minutos, que viraria uma barra só escondendo o
# resto. O /ai/ask/stream fica: dura segundos e é o caminho da pergunta ao agente.
ROTAS_FORA_DO_RASTREAMENTO = r"/health$,/ordens/eventos"


def configurar_rastreamento(
    app: FastAPI, settings: Settings, processador: SpanProcessor | None = None
) -> TracerProvider | None:
    """Liga o rastreamento da API e devolve o provider, ou None se ele estiver desligado.

    O `processador` existe para os testes, que guardam os spans em memória em vez de enviá-los.
    """
    if processador is None:
        if not settings.rastreamento_endpoint:
            return None
        # Em lote e numa thread à parte: enviar span por span atrasaria cada resposta.
        processador = BatchSpanProcessor(OTLPSpanExporter(endpoint=settings.rastreamento_endpoint))

    # O provider vai explícito para cada instrumentação, nunca como o global do processo: o
    # global só pode ser definido uma vez, e cada teste monta a API com o seu.
    provider = TracerProvider(resource=Resource.create({SERVICE_NAME: NOME_DO_SERVICO}))
    provider.add_span_processor(processador)

    FastAPIInstrumentor.instrument_app(
        app,
        tracer_provider=provider,
        excluded_urls=ROTAS_FORA_DO_RASTREAMENTO,
        # Sem isso, cada evento de um stream vira um span filho, e uma pergunta ao agente
        # geraria dezenas deles sem informação nenhuma.
        exclude_spans=["receive", "send"],
    )
    # No psycopg, e não no SQLAlchemy: o agente conecta direto pelo psycopg, sem SQLAlchemy, e
    # o backend passa por ele também. Uma instrumentação só cobre as consultas dos dois.
    PsycopgInstrumentor().instrument(tracer_provider=provider)
    # O agente não muda: o PydanticAI emite os passos do modelo quando ligado de fora. Sem o
    # conteúdo: o prompt da narração leva a pergunta e as linhas da Gold, que não saem do
    # processo. Ficam a duração, o modelo e os tokens.
    Agent.instrument_all(InstrumentationSettings(tracer_provider=provider, include_content=False))
    return provider


def anotar_resposta_do_agente(answer: AgentAnswer) -> None:
    """Grava no span da requisição o que o agente respondeu, a começar pelo `request_id`.

    É a ponte entre a auditoria e o trace: o perfil `ti` lê o `request_id` em
    `GET /ai/audit/{id}` e o Jaeger acha o trace por essa tag, sem coluna nova no banco. Com o
    rastreamento desligado, o span atual não grava nada, e a chamada não custa nada.
    """
    trace.get_current_span().set_attributes(
        {
            "venergy.ai.request_id": answer.request_id,
            "venergy.ai.status": answer.status.value,
            "venergy.ai.row_count": answer.row_count,
            "venergy.ai.input_tokens": answer.input_tokens,
            "venergy.ai.output_tokens": answer.output_tokens,
        }
    )
