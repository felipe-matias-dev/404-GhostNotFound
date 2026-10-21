from pathlib import Path

import pytest
from pydantic_ai.messages import ModelResponse, SystemPromptPart, ToolCallPart, UserPromptPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from venergy_agent.domain.errors import ErrorKind
from venergy_agent.domain.question import Question
from venergy_agent.domain.semantic import ColumnSpec, SemanticLayer, ViewSpec
from venergy_agent.domain.sql import AttemptFeedback, DraftStatus
from venergy_agent.infrastructure.sql_generator import PydanticAiSqlGenerator

SHIPPED_PROMPTS = Path(__file__).parents[3] / "prompts"

LAYER = SemanticLayer(
    version="v0",
    views=(
        ViewSpec(
            name="sem_uc",
            description="Unidades consumidoras",
            grain="uma linha por UC",
            columns=(ColumnSpec(name="cod_uc", type="text", description="código da UC"),),
        ),
    ),
)
QUESTION = Question(text="Quantas UCs existem?", session_id="s1")


def scripted_model(*outputs):
    calls = []

    def respond(messages, info: AgentInfo):
        calls.append(messages)
        args = outputs[min(len(calls), len(outputs)) - 1]
        return ModelResponse(parts=[ToolCallPart(tool_name=info.output_tools[0].name, args=args)])

    return FunctionModel(respond), calls


def generator(model, prompts_dir=SHIPPED_PROMPTS, version="v1"):
    return PydanticAiSqlGenerator(
        model=model, prompts_dir=prompts_dir, prompt_version=version, temperature=0.0
    )


async def test_returns_the_draft_produced_by_the_model():
    model, _ = scripted_model({"status": "ok", "sql": "SELECT count(*) FROM sem_uc"})

    draft = await generator(model).generate(QUESTION, LAYER, None)

    assert draft.status is DraftStatus.OK
    assert draft.sql == "SELECT count(*) FROM sem_uc"


async def test_invalid_draft_is_sent_back_to_the_model():
    model, calls = scripted_model({"status": "ok"}, {"status": "unknown"})

    draft = await generator(model).generate(QUESTION, LAYER, None)

    assert draft.status is DraftStatus.UNKNOWN
    assert len(calls) == 2


async def test_request_carries_rendered_system_and_user_prompts():
    model, calls = scripted_model({"status": "unknown"})

    await generator(model).generate(QUESTION, LAYER, None)

    parts = calls[0][0].parts
    system = next(p.content for p in parts if isinstance(p, SystemPromptPart))
    user = next(p.content for p in parts if isinstance(p, UserPromptPart))
    assert "### sem_uc" in system and "{{" not in system
    assert "Quantas UCs existem?" not in system
    assert user == "<pergunta>\nQuantas UCs existem?\n</pergunta>"


async def test_correction_attempt_reaches_the_model():
    model, calls = scripted_model({"status": "unknown"})
    feedback = AttemptFeedback(
        previous_sql="SELECT nope FROM sem_uc", error_kind=ErrorKind.UNKNOWN_OBJECT, message="x"
    )

    await generator(model).generate(QUESTION, LAYER, feedback)

    user = next(p.content for p in calls[0][0].parts if isinstance(p, UserPromptPart))
    assert "SELECT nope FROM sem_uc" in user and "{{" not in user


def test_unknown_prompt_version_fails_at_construction():
    model, _ = scripted_model({"status": "unknown"})

    with pytest.raises(FileNotFoundError):
        generator(model, version="v999")
