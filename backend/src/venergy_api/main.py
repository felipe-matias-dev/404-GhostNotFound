"""Ponto de entrada da API: monta a aplicação FastAPI e registra as rotas.

Uso: uv run uvicorn venergy_api.main:create_app --factory --reload --reload-dir src
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from venergy_api.config import Settings, get_settings
from venergy_api.routers import health, ordens, receita, unidades


def create_app(settings: Settings | None = None) -> FastAPI:
    # As configurações chegam na criação, e não no import: assim os testes montam o app
    # com as suas próprias, sem depender de um .env na máquina.
    settings = settings or get_settings()

    app = FastAPI(title="V-Energy Grid 360 API", version="0.5.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        # Só o que a API usa: leitura, mais POST e PATCH das ordens de inspeção.
        allow_methods=["GET", "POST", "PATCH"],
    )
    app.include_router(health.router)
    app.include_router(unidades.router)
    app.include_router(receita.router)
    app.include_router(ordens.router)
    return app
