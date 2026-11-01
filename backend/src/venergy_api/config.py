"""Configurações da API, lidas de variáveis de ambiente e do arquivo .env."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

JANELA_ORCAMENTO_PADRAO_SEGUNDOS = 86400


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
    # Limite de perguntas por usuário logado, numa janela de tempo, no POST /ai/ask (429 ao
    # passar). Conta em todas as sessões do usuário. 0 desliga o limite. É uma trava de custo e
    # de abuso acidental, não de segurança (DEC-046).
    ai_limite_perguntas: int = Field(20, ge=0)
    ai_janela_segundos: int = Field(600, gt=0)
    ai_janela_orcamento_segundos: int = Field(JANELA_ORCAMENTO_PADRAO_SEGUNDOS, gt=0)
    # Limite de tentativas de login (DEC-065): depois de `login_max_falhas` senhas erradas do
    # mesmo login a partir do mesmo endereço, dentro da janela, o par fica bloqueado (429) até
    # a falha mais antiga sair dela. 0 desliga o limite.
    login_max_falhas: int = Field(5, ge=0)
    login_janela_segundos: int = Field(900, gt=0)
    # Para onde a API manda os traces do OpenTelemetry (DEC-068), por exemplo o Jaeger do
    # compose: http://jaeger:4318/v1/traces. Vazio desliga: sem coletor no ar, o exportador
    # encheria o log com falhas de envio.
    rastreamento_endpoint: str | None = None


@lru_cache
def get_settings() -> Settings:
    """Lê as configurações uma única vez e reaproveita nas chamadas seguintes."""
    return Settings()
