import pytest
from pydantic import ValidationError

from venergy_agent.domain.judge import PASS_SCORE, JudgeVerdict


@pytest.mark.parametrize(("score", "passed"), [(4, False), (5, False), (1, True), (3, True)])
def test_passed_must_agree_with_the_score(score, passed):
    with pytest.raises(ValidationError):
        JudgeVerdict(score=score, passed=passed, rationale="ok")


def test_blank_rationale_is_rejected():
    with pytest.raises(ValidationError):
        JudgeVerdict(score=5, passed=True, rationale="   ")


@pytest.mark.parametrize(("score", "passed"), [(PASS_SCORE, True), (PASS_SCORE - 1, False)])
def test_coherent_verdict_is_accepted(score, passed):
    verdict = JudgeVerdict(score=score, passed=passed, rationale="clara e fiel")

    assert verdict.passed is passed
