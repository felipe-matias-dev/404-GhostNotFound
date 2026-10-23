from pathlib import Path

from pydantic_ai.messages import ModelResponse, TextPart
from pydantic_ai.models.function import FunctionModel

from venergy_agent.infrastructure.insight_writer import PydanticAiInsightWriter

SHIPPED_PROMPTS = Path(__file__).parents[3] / "prompts" / "insight"
NONCE = "n0nce42"
METRICS = {"receita_faturada": 1234.5, "variacao_percentual": -4.0}


def narrating_model(text):
    calls = []

    def respond(messages, info):
        calls.append(messages)
        return ModelResponse(parts=[TextPart(content=text)])

    return FunctionModel(respond), calls


def failing_model():
    def respond(messages, info):
        raise RuntimeError("provedor caiu")

    return FunctionModel(respond)


def writer(model):
    return PydanticAiInsightWriter(
        model=model,
        prompts_dir=SHIPPED_PROMPTS,
        prompt_version="v1",
        temperature=0.0,
        nonce=NONCE,
    )


async def test_returns_an_insight_when_every_number_is_in_the_metrics():
    model, _ = narrating_model("A receita faturada foi de R$ 1.234,5, com queda de 4,0%.")

    insight = await writer(model).narrate("Receita", METRICS)

    assert insight is not None
    assert insight.metrics_used == ("receita_faturada", "variacao_percentual")


async def test_a_number_outside_the_metrics_drops_the_insight():
    model, _ = narrating_model("A receita caiu 999%.")

    assert await writer(model).narrate("Receita", METRICS) is None


async def test_number_written_in_english_format_drops_the_insight():
    model, _ = narrating_model("A receita faturada foi de 1234.5.")

    assert await writer(model).narrate("Receita", METRICS) is None


async def test_numbers_inside_nested_metrics_and_their_keys_are_supported():
    metrics = {"dec_por_municipio": {"Olinda": 0.6}, "competencias": ["2025-01", "2025-03"]}
    model, _ = narrating_model("Entre 2025-01 e 2025-03, Olinda teve DEC de 0,6 hora.")

    insight = await writer(model).narrate("Continuidade", metrics)

    assert insight is not None


async def test_provider_error_returns_none_so_the_screen_shows_without_insight():
    assert await writer(failing_model()).narrate("Receita", METRICS) is None


async def test_metrics_reach_the_model_as_delimited_data_with_the_label():
    model, calls = narrating_model("Receita estável.")

    await writer(model).narrate("Receita", METRICS)

    user = next(part.content for part in calls[0][0].parts if part.part_kind == "user-prompt")
    assert f"<dados-{NONCE}>" in user and f"</dados-{NONCE}>" in user
    assert '"variacao_percentual": -4.0' in user
