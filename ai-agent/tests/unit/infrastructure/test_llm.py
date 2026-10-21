import pytest
from pydantic_ai.models.fallback import FallbackModel
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.models.openrouter import OpenRouterModel

from venergy_agent.config import AgentSettings
from venergy_agent.infrastructure import llm
from venergy_agent.infrastructure.llm import build_model


def settings(**overrides):
    return AgentSettings(
        _env_file=None,
        google_api_key="gk-test",
        openrouter_api_key="sk-test",
        database_url="postgresql://x@localhost/db",
        **overrides,
    )


def test_builds_gemini_direct_by_default():
    model = build_model(settings())

    assert isinstance(model, GoogleModel)
    assert model.model_name == "gemini-3.1-flash-lite"


def test_builds_openrouter_model_from_its_prefix():
    model = build_model(settings(llm_model="openrouter:google/gemma-4-31b-it:free"))

    assert isinstance(model, OpenRouterModel)
    assert model.model_name == "google/gemma-4-31b-it:free"


def test_fallback_can_use_the_other_provider():
    model = build_model(settings(fallback_model="openrouter:google/gemini-3.1-flash-lite"))

    assert isinstance(model, FallbackModel)
    assert [type(m) for m in model.models] == [GoogleModel, OpenRouterModel]


def test_unknown_provider_is_never_routed_to_openrouter():
    unchecked = AgentSettings.model_construct(
        llm_model="anthropic:claude-x", fallback_model=None, openrouter_api_key="sk-test"
    )

    with pytest.raises(ValueError, match="anthropic"):
        build_model(unchecked)


def test_gemini_client_retries_transient_errors_with_backoff(monkeypatch):
    received = {}
    real_provider = llm.GoogleProvider

    def spy(**kwargs):
        received.update(kwargs)
        return real_provider(**kwargs)

    monkeypatch.setattr(llm, "GoogleProvider", spy)

    build_model(settings(llm_retry_attempts=4, llm_retry_initial_delay_seconds=0.5))

    options = received["retry_options"]
    assert options.attempts == 4
    assert options.initial_delay == 0.5
    assert sorted(options.http_status_codes) == [429, 503]
