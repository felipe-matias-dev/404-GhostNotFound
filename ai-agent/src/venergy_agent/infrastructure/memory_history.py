from collections import defaultdict

from venergy_agent.domain.answer import AgentAnswer, AnswerStatus
from venergy_agent.domain.conversation import ConversationTurn


class InMemoryConversationHistory:
    def __init__(self) -> None:
        self._turns: dict[str, list[ConversationTurn]] = defaultdict(list)
        self._tokens: dict[str, int] = defaultdict(int)

    async def record(self, session_id: str, question: str, answer: AgentAnswer) -> None:
        self._turns[session_id].append(
            ConversationTurn(
                question=question,
                sql=answer.sql,
                status=answer.status,
                clarification=answer.clarification,
            )
        )
        self._tokens[session_id] += answer.input_tokens + answer.output_tokens

    async def recent(self, session_id: str, limit: int) -> tuple[ConversationTurn, ...]:
        if limit <= 0:
            return ()
        turns = [
            turn
            for turn in self._turns.get(session_id, [])
            if turn.status is not AnswerStatus.REFUSED
        ]
        return tuple(turns[-limit:])

    async def tokens_used(self, session_id: str) -> int:
        return self._tokens.get(session_id, 0)
