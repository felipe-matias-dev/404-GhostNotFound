from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

AGENT_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class AgentSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="VENERGY_AGENT_", env_file=AGENT_ENV_FILE)

    llm_model: str = "openrouter:google/gemini-3.1-flash-lite"
    fallback_model: str | None = None
    openrouter_api_key: SecretStr
    temperature: float = Field(0.0, ge=0.0, le=0.2)
    sql_dialect: Literal["postgres"] = "postgres"
    database_url: str
    allowed_schema: str = "gold"
    max_question_chars: int = Field(500, gt=0)
    max_rows: int = Field(200, gt=0)
    query_timeout_seconds: float = Field(10.0, gt=0)
    max_correction_attempts: int = Field(3, ge=1, le=3)
    prompt_version: str = "v1"
