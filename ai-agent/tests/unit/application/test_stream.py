import asyncio

from ask_fakes import (
    CONFIGURED,
    BrokenValidator,
    FixedWriter,
    ScriptedExecutor,
    ScriptedGenerator,
    generation,
    result,
    use_case,
)

from venergy_agent.application.ask import INTERNAL_FAILED, AskUseCase
from venergy_agent.domain.answer import AnswerStatus
from venergy_agent.domain.events import AnswerEvent, Stage, StageEvent


class BlockingGenerator:
    def __init__(self):
        self.release = asyncio.Event()
        self.cancelled = False

    async def generate(self, question, layer, feedback):
        try:
            await self.release.wait()
        except asyncio.CancelledError:
            self.cancelled = True
            raise
        return generation()


async def collect(agent, question="quantas UCs?"):
    return [event async for event in agent.stream(question, "s1")]


def stages(events):
    return [event.stage for event in events if isinstance(event, StageEvent)]


async def test_answered_flow_emits_stages_then_the_answer(layer):
    events = await collect(use_case(layer, ScriptedGenerator(generation())))

    assert stages(events) == [Stage.UNDERSTANDING, Stage.QUERYING, Stage.WRITING]
    assert all(isinstance(event, StageEvent) for event in events[:-1])
    assert isinstance(events[-1], AnswerEvent)
    assert events[-1].answer.status is AnswerStatus.ANSWERED


async def test_correction_emits_correcting_before_the_new_attempt(layer):
    generator = ScriptedGenerator(generation(sql="DELETE FROM sem_uc"), generation())

    events = await collect(use_case(layer, generator))

    assert stages(events) == [
        Stage.UNDERSTANDING,
        Stage.QUERYING,
        Stage.CORRECTING,
        Stage.QUERYING,
        Stage.WRITING,
    ]
    assert [event.attempt for event in events[:-1]] == [1, 1, 2, 2, 2]
    assert events[-1].answer.status is AnswerStatus.ANSWERED


async def test_unknown_draft_emits_only_understanding(layer):
    events = await collect(use_case(layer, ScriptedGenerator(generation("unknown"))))

    assert stages(events) == [Stage.UNDERSTANDING]
    assert events[-1].answer.status is AnswerStatus.UNKNOWN


async def test_refused_question_emits_only_the_answer(layer):
    agent = use_case(layer, ScriptedGenerator(generation()), max_question_chars=10)

    events = await collect(agent, "x" * 11)

    assert len(events) == 1
    assert events[0].answer.status is AnswerStatus.REFUSED


async def test_unexpected_error_still_ends_with_a_failed_answer(layer):
    agent = AskUseCase(
        layer=layer,
        generator=ScriptedGenerator(generation()),
        validator=BrokenValidator(),
        executor=ScriptedExecutor(result()),
        answer_writer=FixedWriter(),
        max_question_chars=500,
        max_correction_attempts=3,
        answer_sample_rows=20,
        prompt_version="v1",
        configured_model=CONFIGURED,
    )

    events = await collect(agent)

    assert stages(events) == [Stage.UNDERSTANDING, Stage.QUERYING]
    assert events[-1].answer.status is AnswerStatus.FAILED
    assert events[-1].answer.refused_reason == INTERNAL_FAILED


async def test_client_disconnect_cancels_the_run(layer):
    generator = BlockingGenerator()
    executor = ScriptedExecutor(result())
    events = use_case(layer, generator, executor).stream("quantas UCs?", "s1")

    first = await anext(events)
    await events.aclose()

    assert first.stage is Stage.UNDERSTANDING
    assert generator.cancelled is True
    assert executor.queries == []


async def test_ask_returns_the_answer_the_stream_ends_with(layer, monkeypatch):
    agent = use_case(layer, ScriptedGenerator(generation()))
    recorded = await collect(agent)

    async def replay(question, session_id):
        for event in recorded:
            yield event

    monkeypatch.setattr(agent, "stream", replay)

    assert await agent.ask("quantas UCs?", "s1") == recorded[-1].answer
