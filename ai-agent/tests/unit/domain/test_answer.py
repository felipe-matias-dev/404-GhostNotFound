import pytest
from pydantic import ValidationError

from venergy_agent.domain.answer import AgentAnswer


def test_row_count_below_sample_size_is_rejected():
    with pytest.raises(ValidationError):
        AgentAnswer(
            answer="x",
            sql="SELECT 1",
            rows=({"a": 1}, {"a": 2}),
            row_count=1,
            confidence="high",
            sources=(),
            assumptions=(),
            clarification=None,
            request_id="r1",
            prompt_version="v1",
        )
