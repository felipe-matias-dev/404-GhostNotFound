"""Configurações da API, lidas de variáveis de ambiente e do arquivo .env."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="VENERGY_API_", env_file=".env")

    # Sem valor padrão: se o .env estiver faltando, a API falha ao subir com uma
    # mensagem clara, em vez de criar um banco vazio num caminho inesperado.
    database_url: str
    # Pasta onde o time de dados entrega os CSVs da Gold, um arquivo por tabela.
    gold_dir: Path
    # Endereços do frontend que o navegador deixa chamar a API. O padrão é o do `npm run dev`.
    cors_origins: list[str] = ["http://localhost:3000"]


@lru_cache
def get_settings() -> Settings:
    """Lê as configurações uma única vez e reaproveita nas chamadas seguintes."""
    return Settings()
