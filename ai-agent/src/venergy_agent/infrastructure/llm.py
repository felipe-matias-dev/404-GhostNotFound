from google.genai.types import HttpRetryOptions
from pydantic_ai.models import Model
from pydantic_ai.models.fallback import FallbackModel
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.models.openrouter import OpenRouterModel
from pydantic_ai.providers.google import GoogleProvider
from pydantic_ai.providers.openrouter import OpenRouterProvider

from venergy_agent.config import AgentSettings

TRANSIENT_STATUS_CODES = [429, 503]


def build_model(settings: AgentSettings) -> Model:
    primary = _build(settings.llm_model, settings)
    if settings.fallback_model is None:
        return primary
    return FallbackModel(primary, _build(settings.fallback_model, settings))


def _build(configured: str, settings: AgentSettings) -> Model:
    provider, _, name = configured.partition(":")
    if provider == "google-gla":
        key = settings.google_api_key.get_secret_value()
        retry = HttpRetryOptions(
            attempts=settings.llm_retry_attempts,
            initial_delay=settings.llm_retry_initial_delay_seconds,
            http_status_codes=TRANSIENT_STATUS_CODES,
        )
        return GoogleModel(name, provider=GoogleProvider(api_key=key, retry_options=retry))
    if provider == "openrouter":
        key = settings.openrouter_api_key.get_secret_value()
        return OpenRouterModel(name, provider=OpenRouterProvider(api_key=key))
    raise ValueError(f"unsupported provider {provider!r} in {configured!r}")
