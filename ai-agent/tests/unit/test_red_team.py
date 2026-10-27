import pytest
import yaml

from venergy_agent.config import AGENT_ROOT

RED_TEAM = AGENT_ROOT / "eval" / "red_team.yaml"
KINDS = {
    "ignorar_instrucoes",
    "vazar_prompt",
    "escrita_via_texto",
    "injecao_por_dados",
    "fora_do_escopo",
}


@pytest.fixture(scope="module")
def items():
    return yaml.safe_load(RED_TEAM.read_text(encoding="utf-8"))["itens"]


def test_red_team_has_at_least_15_attacks_covering_every_kind(items):
    assert len(items) >= 15
    assert {item["kind"] for item in items} == KINDS
    assert len({item["id"] for item in items}) == len(items)
    assert len({item["attack"] for item in items}) == len(items)


def test_red_team_expected_status_is_refused_or_unknown(items):
    assert {item["expected_status"] for item in items} <= {"refused", "unknown"}
