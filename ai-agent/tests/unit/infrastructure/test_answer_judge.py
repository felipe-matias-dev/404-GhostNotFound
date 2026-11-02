from pathlib import Path

import pytest
from pydantic_ai.messages import ModelResponse, SystemPromptPart, ToolCallPart, UserPromptPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.usage import RequestUsage

from venergy_agent.domain.answer import AgentAnswer, AnswerStatus, Confidence
from venergy_agent.domain.errors import ModelCallFailed
from venergy_agent.infrastructure.answer_judge import PydanticAiAnswerJudge

SHIPPED_PROMPTS = Path(__file__).parents[3] / "prompts" / "judge"
NONCE = "n0nce42"
QUESTION = "Quantas UCs em Olinda?"
ANSWER = AgentAnswer(
    answer="Existem 3 UCs em Olinda.",
    status=AnswerStatus.ANSWERED,
    sql="SELECT 1",
    rows=({"total": 3},),
    row_count=1,
    truncated=False,
    confidence=Confidence.HIGH,
    sources=(),
    assumptions=(),
    clarification=None,
    refused_reason=None,
    request_id="r1",
    model="m",
    prompt_version="v2",
    latency_ms=10,
)
GOOD = {"score": 5, "passed": True, "rationale": "Clara e fiel."}
INCOHERENT = {"score": 5, "passed": False, "rationale": "Clara e fiel."}


def scripted_model(*outputs):
    calls = []

    def respond(messages, info: AgentInfo):
        calls.append(messages)
        args = outputs[min(len(calls), len(outputs)) - 1]
        return ModelResponse(parts=[ToolCallPart(tool_name=info.output_tools[0].name, args=args)])

    return FunctionModel(respond), calls


def judge(model, version="v1"):
    return PydanticAiAnswerJudge(
        model=model, prompts_dir=SHIPPED_PROMPTS, prompt_version=version, nonce=NONCE
    )


async def test_returns_the_verdict_produced_by_the_model():
    model, _ = scripted_model(GOOD)

    run = await judge(model).judge(QUESTION, ANSWER)

    assert (run.verdict.score, run.verdict.passed, run.verdict.rationale) == (
        5,
        True,
        "Clara e fiel.",
    )


async def test_reports_the_tokens_spent_by_the_judge():
    def respond(messages, info: AgentInfo):
        return ModelResponse(
            parts=[ToolCallPart(tool_name=info.output_tools[0].name, args=GOOD)],
            usage=RequestUsage(input_tokens=120, output_tokens=15),
        )

    run = await judge(FunctionModel(respond)).judge(QUESTION, ANSWER)

    assert (run.input_tokens, run.output_tokens) == (120, 15)


async def test_a_judge_call_that_never_becomes_valid_reports_the_tokens_it_spent():
    calls = []

    def respond(messages, info: AgentInfo):
        calls.append(messages)
        return ModelResponse(
            parts=[ToolCallPart(tool_name=info.output_tools[0].name, args={"score": 9})],
            usage=RequestUsage(input_tokens=7, output_tokens=3),
        )

    with pytest.raises(ModelCallFailed) as failure:
        await judge(FunctionModel(respond)).judge(QUESTION, ANSWER)

    assert failure.value.input_tokens == 7 * len(calls)
    assert failure.value.output_tokens == 3 * len(calls)
    assert failure.value.input_tokens > 0


async def test_incoherent_verdict_is_sent_back_to_the_model():
    model, calls = scripted_model(INCOHERENT, GOOD)

    run = await judge(model).judge(QUESTION, ANSWER)

    assert run.verdict.passed is True
    assert len(calls) == 2


def test_unknown_prompt_version_fails_at_construction():
    model, _ = scripted_model(GOOD)

    with pytest.raises(FileNotFoundError):
        judge(model, version="v99")


async def test_rubric_is_the_system_prompt_and_content_travels_only_as_delimited_data():
    model, calls = scripted_model(GOOD)

    await judge(model).judge(QUESTION, ANSWER)

    parts = calls[0][0].parts
    system = next(p.content for p in parts if isinstance(p, SystemPromptPart))
    user = next(p.content for p in parts if isinstance(p, UserPromptPart))
    assert "Fidelidade" in system and "{{" not in system
    assert QUESTION not in system and "Existem 3 UCs" not in system
    assert f"<pergunta-{NONCE}>\n{QUESTION}\n</pergunta-{NONCE}>" in user
    assert f"<resposta-{NONCE}>\nExistem 3 UCs em Olinda.\n</resposta-{NONCE}>" in user
    assert '{"total": 3}' in user
