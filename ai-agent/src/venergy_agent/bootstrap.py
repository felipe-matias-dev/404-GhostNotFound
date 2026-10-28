from venergy_agent.application.ask import AskUseCase
from venergy_agent.application.ports import InsightWriter
from venergy_agent.config import AgentSettings
from venergy_agent.infrastructure.answer_writer import PydanticAiAnswerWriter
from venergy_agent.infrastructure.insight_writer import PydanticAiInsightWriter
from venergy_agent.infrastructure.llm import build_model
from venergy_agent.infrastructure.postgres_executor import PostgresQueryExecutor
from venergy_agent.infrastructure.semantic_source import YamlSemanticLayerSource
from venergy_agent.infrastructure.sql_generator import PydanticAiSqlGenerator
from venergy_agent.infrastructure.sql_validator import SqlglotValidator


async def build_agent(settings: AgentSettings, narrate: bool = True) -> AskUseCase:
    layer = await YamlSemanticLayerSource(
        settings.semantic_layer_path, settings.gold_contract_path
    ).load()
    model = build_model(settings)
    return AskUseCase(
        layer=layer,
        generator=PydanticAiSqlGenerator(
            model=model,
            prompts_dir=settings.prompts_dir,
            prompt_version=settings.prompt_version,
            temperature=settings.temperature,
        ),
        validator=SqlglotValidator(
            dialect=settings.sql_dialect,
            max_rows=settings.max_rows,
            allowed_schema=settings.allowed_schema,
        ),
        executor=PostgresQueryExecutor(settings.database_url, settings.query_timeout_seconds),
        answer_writer=(
            PydanticAiAnswerWriter(
                model=model,
                prompts_dir=settings.prompts_dir / "answer",
                prompt_version=settings.answer_prompt_version,
                temperature=settings.temperature,
                units=layer.column_units,
            )
            if narrate
            else None
        ),
        max_question_chars=settings.max_question_chars,
        max_correction_attempts=settings.max_correction_attempts,
        answer_sample_rows=settings.answer_sample_rows,
        prompt_version=settings.prompt_version,
        configured_model=settings.llm_model.partition(":")[2],
    )


def build_insight_writer(settings: AgentSettings) -> InsightWriter:
    return PydanticAiInsightWriter(
        model=build_model(settings),
        prompts_dir=settings.prompts_dir / "insight",
        prompt_version=settings.insight_prompt_version,
        temperature=settings.temperature,
    )
