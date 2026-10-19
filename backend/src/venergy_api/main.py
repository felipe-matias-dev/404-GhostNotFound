"""Ponto de entrada da API: monta a aplicação FastAPI e registra as rotas."""

from fastapi import FastAPI

from venergy_api.routers import health


def create_app() -> FastAPI:
    app = FastAPI(title="V-Energy Grid 360 API", version="0.1.0")
    app.include_router(health.router)
    return app


app = create_app()
