import asyncio

import pytest
from pydantic_ai import Agent
from pydantic_ai.exceptions import ModelAPIError
from pydantic_ai.messages import ModelResponse, TextPart
from pydantic_ai.models.fallback import FallbackModel
from pydantic_ai.models.function import FunctionModel

from venergy_agent.infrastructure.guarded_model import GuardedModel


class Clock:
    now = 100.0

    def __call__(self):
        return self.now


def model(behaviour):
    calls = []

    async def respond(messages, info):
        calls.append(1)
        return await behaviour()

    return FunctionModel(respond), calls


async def answer():
    return ModelResponse(parts=[TextPart("reserva")])


async def overloaded():
    raise ModelAPIError("primary", "503")


async def hangs():
    await asyncio.Event().wait()


def chain(primary, clock, timeout=5.0):
    backup, backup_calls = model(answer)
    guarded = GuardedModel(primary, timeout, cooldown_seconds=60, clock=clock)
    return Agent(FallbackModel(guarded, backup)), backup_calls


async def test_a_hanging_model_gives_way_to_the_next_one():
    primary, _ = model(hangs)
    agent, _ = chain(primary, Clock(), timeout=0.01)

    async with asyncio.timeout(1):
        result = await agent.run("x")

    assert result.output == "reserva"


async def test_a_failed_model_is_skipped_during_the_cooldown_and_tried_after_it():
    clock = Clock()
    primary, primary_calls = model(overloaded)
    agent, backup_calls = chain(primary, clock)

    await agent.run("x")
    await agent.run("x")
    assert (len(primary_calls), len(backup_calls)) == (1, 2)

    clock.now += 61
    await agent.run("x")
    assert (len(primary_calls), len(backup_calls)) == (2, 3)


async def test_a_healthy_model_is_not_skipped():
    primary, primary_calls = model(answer)
    agent, backup_calls = chain(primary, Clock())

    await agent.run("x")
    await agent.run("x")

    assert (len(primary_calls), len(backup_calls)) == (2, 0)


async def test_the_error_reaches_the_caller_when_there_is_no_next_model():
    primary, _ = model(overloaded)
    agent = Agent(GuardedModel(primary, 5.0, cooldown_seconds=0, clock=Clock()))

    with pytest.raises(ModelAPIError):
        await agent.run("x")
