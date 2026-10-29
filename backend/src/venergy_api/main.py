"""Ponto de entrada da API: monta a aplicação FastAPI e registra as rotas.

Uso: uv run uvicorn venergy_api.main:create_app --factory --reload --reload-dir src
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from venergy_api.agente import (
    configurar_logs_do_agente,
    montar_agente,
    montar_redator_insights,
)
from venergy_api.config import Settings, get_settings
from venergy_api.insights import CacheInsights
from venergy_api.routers import (
    ai,
    auth,
    continuidade,
    fila,
    health,
    indicadores,
    ordens,
    receita,
    unidades,
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    # Uma vez por processo, e não por requisição: carregar a camada semântica e montar o
    # modelo a cada pergunta seria custo à toa. Fica no estado do app para os testes
    # trocarem o agente por um falso (dependency_overrides), sem chamar o Gemini.
    # Os logs entram aqui, e não no create_app: os testes não mexem no log do processo.
    configurar_logs_do_agente()
    app.state.agente = await montar_agente()
    app.state.redator_insights = await montar_redator_insights()
    yield


def create_app(settings: Settings | None = None) -> FastAPI:
    # As configurações chegam na criação, e não no import: assim os testes montam o app
    # com as suas próprias, sem depender de um .env na máquina.
    settings = settings or get_settings()

    app = FastAPI(title="V-Energy Grid 360 API", version="0.10.0", lifespan=lifespan)
    # Criado com o app, e não no lifespan: o cache não depende de nada externo, e o app dos
    # testes (sem lifespan) também precisa dele.
    app.state.cache_insights = CacheInsights()
    # A dependência de login lê o segredo daqui, e não de get_settings(): os testes montam o
    # app com as próprias configurações.
    app.state.settings = settings
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        # Só o que a API usa: leitura, mais POST e PATCH das ordens de inspeção.
        allow_methods=["GET", "POST", "PATCH"],
    )
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(unidades.router)
    app.include_router(receita.router)
    app.include_router(continuidade.router)
    app.include_router(indicadores.router)
    app.include_router(fila.router)
    app.include_router(ordens.router)
    app.include_router(ai.router)
    return app
