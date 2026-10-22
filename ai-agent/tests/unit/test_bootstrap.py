import pytest

from venergy_agent.application.ask import AskUseCase
from venergy_agent.bootstrap import build_agent
from venergy_agent.config import AgentSettings
from venergy_agent.infrastructure.semantic_source import SemanticLayerError


@pytest.fixture
def settings(monkeypatch):
    monkeypatch.setenv("VENERGY_AGENT_GOOGLE_API_KEY", "gk-test")
    monkeypatch.setenv("VENERGY_AGENT_DATABASE_URL", "postgresql://x@localhost/db")
    return AgentSettings(_env_file=None)


async def test_builds_the_use_case_from_the_real_layer_and_prompts(settings):
    agent = await build_agent(settings)

    assert isinstance(agent, AskUseCase)


async def test_broken_semantic_layer_fails_at_startup_not_on_the_first_question(settings, tmp_path):
    broken = tmp_path / "semantic_layer.yaml"
    broken.write_text(
        'version: "0.1.0"\nviews:\n  - name: sem_x\n    source: tabela_inventada\n'
        "    description: x\n    grain: x\n    columns: []\n",
        encoding="utf-8",
    )
    settings = settings.model_copy(update={"semantic_layer_path": broken})

    with pytest.raises(SemanticLayerError, match="tabela_inventada"):
        await build_agent(settings)
