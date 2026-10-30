from venergy_agent.domain.answer import AgentAnswer, AnswerStatus, Confidence
from venergy_agent.infrastructure.memory_history import InMemoryConversationHistory


def answer(status=AnswerStatus.ANSWERED, sql="SELECT 1", input_tokens=0, output_tokens=0):
    answered = status is AnswerStatus.ANSWERED
    return AgentAnswer(
        answer="texto",
        status=status,
        sql=sql if answered else None,
        rows=(),
        row_count=0,
        truncated=False,
        confidence=Confidence.HIGH if answered else Confidence.UNKNOWN,
        sources=(),
        assumptions=(),
        clarification=None,
        refused_reason=None if answered else "motivo",
        request_id="r1",
        model="m",
        prompt_version="v3",
        latency_ms=1,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )


async def test_recent_returns_the_last_turns_of_the_session_oldest_first():
    history = InMemoryConversationHistory()
    for index in range(4):
        await history.record("s1", f"pergunta {index}", answer(sql=f"SELECT {index}"))

    turns = await history.recent("s1", 2)

    assert [turn.question for turn in turns] == ["pergunta 2", "pergunta 3"]
    assert turns[1].sql == "SELECT 3"
    assert turns[1].status is AnswerStatus.ANSWERED


async def test_sessions_do_not_mix():
    history = InMemoryConversationHistory()
    await history.record("s1", "da s1", answer())
    await history.record("s2", "da s2", answer(AnswerStatus.UNKNOWN))

    assert [turn.question for turn in await history.recent("s1", 5)] == ["da s1"]
    assert await history.recent("s3", 5) == ()


async def test_tokens_used_sums_input_and_output_of_the_session():
    history = InMemoryConversationHistory()
    await history.record("s1", "a", answer(input_tokens=10, output_tokens=5))
    await history.record("s1", "b", answer(input_tokens=20, output_tokens=1))
    await history.record("s2", "c", answer(input_tokens=99, output_tokens=99))

    assert await history.tokens_used("s1") == 36
    assert await history.tokens_used("nova") == 0


async def test_refused_turns_do_not_take_a_slot_of_the_limit():
    history = InMemoryConversationHistory()
    await history.record("s1", "respondida", answer())
    await history.record("s1", "recusada 1", answer(status=AnswerStatus.REFUSED))
    await history.record("s1", "recusada 2", answer(status=AnswerStatus.REFUSED))
    await history.record("s1", "mais recente", answer())

    turns = await history.recent("s1", 2)

    assert [turn.question for turn in turns] == ["respondida", "mais recente"]
