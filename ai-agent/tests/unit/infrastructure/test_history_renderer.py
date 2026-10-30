from venergy_agent.domain.answer import AnswerStatus
from venergy_agent.domain.conversation import ConversationTurn
from venergy_agent.infrastructure.history_renderer import render_history

NONCE = "n0nce42"


def test_a_clarify_turn_shows_the_question_the_agent_asked():
    turn = ConversationTurn(
        question="E o FEC?",
        sql=None,
        status=AnswerStatus.CLARIFY,
        clarification="Qual período você quer?",
    )

    text = render_history("{{historico}}", (turn,), NONCE)

    assert "Esclarecimento pedido: Qual período você quer?" in text


def test_a_turn_without_clarification_has_no_such_line():
    turn = ConversationTurn(question="Quantas UCs?", sql="SELECT 1", status=AnswerStatus.ANSWERED)

    text = render_history("{{historico}}", (turn,), NONCE)

    assert "Esclarecimento" not in text
