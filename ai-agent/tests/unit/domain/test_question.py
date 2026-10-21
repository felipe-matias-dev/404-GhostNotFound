import pytest
from pydantic import ValidationError

from venergy_agent.domain.question import Question


@pytest.mark.parametrize("text", ["", "   ", "\n\t"])
def test_blank_text_is_rejected(text):
    with pytest.raises(ValidationError):
        Question(text=text, session_id="s1")


def test_text_is_stripped_and_request_id_generated():
    question = Question(text="  receita de 03/2025?  ", session_id="s1")

    assert question.text == "receita de 03/2025?"
    assert question.request_id
