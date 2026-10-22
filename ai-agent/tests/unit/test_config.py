import pytest
from pydantic import ValidationError

from venergy_agent.config import AGENT_ENV_FILE, AgentSettings

GEMINI = "google-gla:gemini-3.1-flash-lite"
OPENROUTER = "openrouter:google/gemma-4-31b-it:free"
KEYS = ("VENERGY_AGENT_GOOGLE_API_KEY", "VENERGY_AGENT_OPENROUTER_API_KEY")


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for key in (*KEYS, "VENERGY_AGENT_LLM_MODEL", "VENERGY_AGENT_FALLBACK_MODEL"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("VENERGY_AGENT_DATABASE_URL", "postgresql://x@localhost/db")


@pytest.fixture
def required_env(monkeypatch):
    monkeypatch.setenv("VENERGY_AGENT_GOOGLE_API_KEY", "gk-test-123")


def test_prefixed_env_overrides_default(required_env, monkeypatch):
    monkeypatch.setenv("VENERGY_AGENT_MAX_ROWS", "50")

    assert AgentSettings(_env_file=None).max_rows == 50


@pytest.mark.parametrize(
    ("llm_model", "fallback_model", "present_key"),
    [
        (GEMINI, None, "VENERGY_AGENT_OPENROUTER_API_KEY"),
        (OPENROUTER, None, "VENERGY_AGENT_GOOGLE_API_KEY"),
        (GEMINI, OPENROUTER, "VENERGY_AGENT_GOOGLE_API_KEY"),
    ],
)
def test_key_of_each_chosen_provider_is_required(
    monkeypatch, llm_model, fallback_model, present_key
):
    monkeypatch.setenv(present_key, "k")

    with pytest.raises(ValidationError):
        AgentSettings(_env_file=None, llm_model=llm_model, fallback_model=fallback_model)


@pytest.mark.parametrize(
    ("llm_model", "present_key"),
    [(GEMINI, "VENERGY_AGENT_GOOGLE_API_KEY"), (OPENROUTER, "VENERGY_AGENT_OPENROUTER_API_KEY")],
)
def test_only_the_chosen_provider_key_is_needed(monkeypatch, llm_model, present_key):
    monkeypatch.setenv(present_key, "k")

    assert AgentSettings(_env_file=None, llm_model=llm_model).llm_model == llm_model


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("TEMPERATURE", "0.5"),
        ("MAX_CORRECTION_ATTEMPTS", "0"),
        ("MAX_CORRECTION_ATTEMPTS", "4"),
        ("LLM_RETRY_ATTEMPTS", "0"),
        ("LLM_RETRY_ATTEMPTS", "6"),
        ("LLM_RETRY_INITIAL_DELAY_SECONDS", "0"),
    ],
)
def test_out_of_range_values_are_rejected(required_env, monkeypatch, name, value):
    monkeypatch.setenv(f"VENERGY_AGENT_{name}", value)

    with pytest.raises(ValidationError):
        AgentSettings(_env_file=None)


@pytest.mark.parametrize("key", KEYS)
def test_api_keys_are_not_exposed(monkeypatch, key):
    for name in KEYS:
        monkeypatch.setenv(name, "secret-123")

    assert "secret-123" not in repr(AgentSettings(_env_file=None))


def test_env_file_in_current_directory_is_ignored(required_env, monkeypatch, tmp_path):
    (tmp_path / ".env").write_text("VENERGY_AGENT_MAX_ROWS=7\n")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setitem(AgentSettings.model_config, "env_file", AGENT_ENV_FILE.with_name(".none"))

    assert AgentSettings().max_rows == 200


def test_unsupported_provider_is_rejected(required_env):
    with pytest.raises(ValidationError, match="unsupported provider"):
        AgentSettings(_env_file=None, llm_model="anthropic:claude-x")


def test_blank_key_counts_as_missing(monkeypatch):
    monkeypatch.setenv("VENERGY_AGENT_GOOGLE_API_KEY", "  ")

    with pytest.raises(ValidationError):
        AgentSettings(_env_file=None)


def test_model_name_is_required_after_the_provider(required_env):
    with pytest.raises(ValidationError):
        AgentSettings(_env_file=None, llm_model="google-gla:")


def test_semantic_layer_and_contract_paths_resolve_inside_the_repository(required_env):
    settings = AgentSettings(_env_file=None)

    assert settings.semantic_layer_path.exists()
    assert settings.gold_contract_path.exists()


def test_answer_sample_rows_must_be_positive(required_env, monkeypatch):
    monkeypatch.setenv("VENERGY_AGENT_ANSWER_SAMPLE_ROWS", "0")

    with pytest.raises(ValidationError):
        AgentSettings(_env_file=None)
