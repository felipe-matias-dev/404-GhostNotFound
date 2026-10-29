from pathlib import Path
from typing import Literal, Self

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

AGENT_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = Path(__file__).resolve().parents[3]
AGENT_ENV_FILE = AGENT_ROOT / ".env"
PROVIDER_KEYS = {"google-gla": "google_api_key", "openrouter": "openrouter_api_key"}


class AgentSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="VENERGY_AGENT_", env_file=AGENT_ENV_FILE)

    llm_model: str = "google-gla:gemini-3.1-flash-lite"
    fallback_model: str | None = None
    google_api_key: SecretStr | None = None
    openrouter_api_key: SecretStr | None = None
    temperature: float = Field(0.0, ge=0.0, le=0.2)
    llm_retry_attempts: int = Field(3, ge=1, le=5)
    llm_retry_initial_delay_seconds: float = Field(1.0, gt=0)
    sql_dialect: Literal["postgres"] = "postgres"
    database_url: str
    allowed_schema: str = "gold"
    max_question_chars: int = Field(500, gt=0)
    max_rows: int = Field(200, gt=0)
    query_timeout_seconds: float = Field(10.0, gt=0)
    max_correction_attempts: int = Field(3, ge=1, le=3)
    prompt_version: str = "v2"
    prompts_dir: Path = AGENT_ROOT / "prompts"
    answer_prompt_version: str = "v3"
    insight_prompt_version: str = "v2"
    answer_sample_rows: int = Field(20, gt=0)
    semantic_layer_path: Path = AGENT_ROOT / "semantic" / "semantic_layer.yaml"
    gold_contract_path: Path = REPO_ROOT / "contracts" / "gold_schema.yaml"

    @model_validator(mode="after")
    def check_provider_keys(self) -> Self:
        for model in filter(None, (self.llm_model, self.fallback_model)):
            provider, _, name = model.partition(":")
            key = PROVIDER_KEYS.get(provider)
            if key is None:
                raise ValueError(
                    f"unsupported provider {provider!r}, use one of {list(PROVIDER_KEYS)}"
                )
            if not name:
                raise ValueError(f"{model!r} has no model name after the provider")
            secret = getattr(self, key)
            if secret is None or not secret.get_secret_value().strip():
                raise ValueError(f"{model!r} requires VENERGY_AGENT_{key.upper()}")
        return self
