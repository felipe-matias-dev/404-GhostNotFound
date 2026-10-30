"""Configurações da API, lidas de variáveis de ambiente e do arquivo .env."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="VENERGY_API_", env_file=".env")

    # Sem valor padrão: se o .env estiver faltando, a API falha ao subir com uma
    # mensagem clara, em vez de criar um banco vazio num caminho inesperado.
    database_url: str
    # Pasta onde o time de dados entrega os CSVs da Gold, um arquivo por tabela.
    gold_dir: Path
    # Assina o token de sessão. Sem valor padrão: um segredo escrito aqui, num repositório
    # público, deixaria qualquer pessoa forjar o token de qualquer perfil.
    jwt_secret: str = Field(min_length=32)
    # Senha dos usuários de demonstração, usada só por `python -m venergy_api.usuarios`.
    senha_demo: str | None = None
    # Endereços do frontend que o navegador deixa chamar a API. O padrão é o do `npm run dev`.
    cors_origins: list[str] = ["http://localhost:3000"]
    # Limite de perguntas por sessão numa janela de tempo no POST /ai/ask (429 ao passar).
    # 0 desliga o limite. Sem autenticação, o session_id é escolhido pelo cliente: é uma trava
    # de custo e de abuso acidental, não de segurança (DEC-046).
    ai_limite_perguntas: int = Field(20, ge=0)
    ai_janela_segundos: int = Field(600, gt=0)
    ai_janela_orcamento_segundos: int = Field(86400, gt=0)


@lru_cache
def get_settings() -> Settings:
    """Lê as configurações uma única vez e reaproveita nas chamadas seguintes."""
    return Settings()
