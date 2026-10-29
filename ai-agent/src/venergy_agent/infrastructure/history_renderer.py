from venergy_agent.domain.conversation import ConversationTurn
from venergy_agent.infrastructure.prompt_renderer import PLACEHOLDER, delimited

NO_SQL = "sem SQL"


def render_history(template: str, turns: tuple[ConversationTurn, ...], nonce: str) -> str:
    body = "\n\n".join(_turn_text(turn) for turn in turns)
    block = delimited("historico", body, nonce)
    return PLACEHOLDER.sub(lambda _: block, template).strip()


def _turn_text(turn: ConversationTurn) -> str:
    text = f"Pergunta: {turn.question}\nStatus: {turn.status.value}\nSQL: {turn.sql or NO_SQL}"
    if turn.clarification is None:
        return text
    return f"{text}\nEsclarecimento pedido: {turn.clarification}"
