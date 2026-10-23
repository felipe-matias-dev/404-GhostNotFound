import pytest

from venergy_agent.config import AGENT_ROOT, REPO_ROOT
from venergy_agent.infrastructure.semantic_source import YamlSemanticLayerSource


@pytest.fixture
async def layer():
    return await YamlSemanticLayerSource(
        AGENT_ROOT / "semantic" / "semantic_layer.yaml",
        REPO_ROOT / "contracts" / "gold_schema.yaml",
    ).load()
