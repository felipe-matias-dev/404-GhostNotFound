import pytest
from pydantic import ValidationError

from venergy_agent.config import AGENT_ENV_FILE, AgentSettings


@pytest.fixture
def required_env(monkeypatch):
    monkeypatch.setenv("VENERGY_AGENT_OPENROUTER_API_KEY", "sk-test-123")
    monkeypatch.setenv("VENERGY_AGENT_DATABASE_URL", "sqlite:///gold.db")


def test_prefixed_env_overrides_default(required_env, monkeypatch):
    monkeypatch.setenv("VENERGY_AGENT_MAX_ROWS", "50")

    assert AgentSettings(_env_file=None).max_rows == 50


def test_missing_api_key_fails(monkeypatch):
    monkeypatch.setenv("VENERGY_AGENT_DATABASE_URL", "sqlite:///gold.db")
    monkeypatch.delenv("VENERGY_AGENT_OPENROUTER_API_KEY", raising=False)

    with pytest.raises(ValidationError):
        AgentSettings(_env_file=None)


@pytest.mark.parametrize(
    ("name", "value"),
    [("TEMPERATURE", "0.5"), ("MAX_CORRECTION_ATTEMPTS", "0"), ("MAX_CORRECTION_ATTEMPTS", "4")],
)
def test_out_of_range_values_are_rejected(required_env, monkeypatch, name, value):
    monkeypatch.setenv(f"VENERGY_AGENT_{name}", value)

    with pytest.raises(ValidationError):
        AgentSettings(_env_file=None)


def test_api_key_is_not_exposed(required_env):
    assert "sk-test-123" not in repr(AgentSettings(_env_file=None))


def test_env_file_in_current_directory_is_ignored(required_env, monkeypatch, tmp_path):
    (tmp_path / ".env").write_text("VENERGY_AGENT_MAX_ROWS=7\n")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setitem(AgentSettings.model_config, "env_file", AGENT_ENV_FILE.with_name(".none"))

    assert AgentSettings().max_rows == 200
