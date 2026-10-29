import pytest
from pydantic_ai.models.fallback import FallbackModel
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.models.openrouter import OpenRouterModel

from venergy_agent.config import AgentSettings
from venergy_agent.infrastructure import llm
from venergy_agent.infrastructure.llm import build_judge_model, build_model


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


def test_builds_the_judge_model_from_its_own_setting():
    model = build_judge_model(settings())

    assert isinstance(model, GoogleModel)
    assert model.model_name == "gemini-3.1-flash"


def test_judge_without_its_provider_key_names_the_variable_and_not_a_key():
    only_openrouter = AgentSettings(
        _env_file=None,
        llm_model="openrouter:google/gemma-4-31b-it:free",
        openrouter_api_key="sk-secret-999",
        database_url="postgresql://x@localhost/db",
    )

    with pytest.raises(ValueError, match="VENERGY_AGENT_GOOGLE_API_KEY") as error:
        build_judge_model(only_openrouter)

    assert "sk-secret-999" not in str(error.value)


@pytest.mark.parametrize(
    "overrides",
    [
        {"llm_model": "google-gla:gemini-3.1-flash"},
        {"fallback_model": "google-gla:gemini-3.1-flash"},
        {
            "llm_model": "google-gla:gemini-3.1-flash-lite",
            "judge_model": "openrouter:google/gemini-3.1-flash-lite",
        },
    ],
)
def test_judge_equal_to_the_generator_or_fallback_is_refused_when_built(overrides):
    with pytest.raises(ValueError, match="judge_model"):
        build_judge_model(settings(**overrides))


@pytest.mark.parametrize("judge_model", ["anthropic:claude-x", "google-gla:", ""])
def test_judge_needs_a_known_provider_and_a_name_when_built(judge_model):
    with pytest.raises(ValueError, match="judge_model"):
        build_judge_model(settings(judge_model=judge_model))
