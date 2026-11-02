from google.genai.types import HttpRetryOptions
from pydantic_ai.models import Model
from pydantic_ai.models.fallback import FallbackModel
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.models.openrouter import OpenRouterModel
from pydantic_ai.providers.google import GoogleProvider
from pydantic_ai.providers.openrouter import OpenRouterProvider

from venergy_agent.config import PROVIDER_KEYS, AgentSettings
from venergy_agent.infrastructure.guarded_model import GuardedModel

TRANSIENT_STATUS_CODES = [429, 503]


def build_model(settings: AgentSettings) -> Model:
    configured = (settings.llm_model, *settings.fallback_models)
    models = [
        GuardedModel(
            _build(model, settings),
            settings.llm_request_timeout_seconds,
            settings.llm_cooldown_seconds if position < len(configured) - 1 else 0,
        )
        for position, model in enumerate(configured)
    ]
    return FallbackModel(*models) if len(models) > 1 else models[0]


def build_judge_model(settings: AgentSettings) -> Model:
    provider, _, name = settings.judge_model.partition(":")
    variable = PROVIDER_KEYS.get(provider)
    if variable is None:
        raise ValueError(
            f"judge_model has unsupported provider {provider!r}, use one of {list(PROVIDER_KEYS)}"
        )
    if not name:
        raise ValueError(f"judge_model {settings.judge_model!r} has no model name")
    generators = (settings.llm_model, *settings.fallback_models)
    if _base_name(settings.judge_model) in {_base_name(model) for model in generators}:
        raise ValueError("judge_model must be a different model from llm_model and fallback_model")
    secret = getattr(settings, variable)
    if secret is None or not secret.get_secret_value().strip():
        raise ValueError(f"the judge requires VENERGY_AGENT_{variable.upper()}")
    return _build(settings.judge_model, settings)


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


def _base_name(model: str) -> str:
    _, _, name = model.partition(":")
    return name.rpartition("/")[2]
