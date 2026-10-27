import json
import logging
from decimal import Decimal

import pytest

from venergy_agent.application.ask import (
    ATTEMPTS_FAILED,
    CLARIFY_PREFIX,
    DATABASE_FAILED,
    EMPTY_RESULT,
    INTERNAL_FAILED,
    MODEL_FAILED,
    REFUSED_REASON,
    TOO_LONG_QUESTION,
    UNKNOWN_REASON,
    AskUseCase,
)
from venergy_agent.config import AGENT_ROOT, REPO_ROOT
from venergy_agent.domain.answer import AnswerStatus, Confidence
from venergy_agent.domain.errors import ErrorKind, QueryExecutionError
from venergy_agent.domain.sql import DraftStatus, Generation, QueryResult, SqlDraft
from venergy_agent.infrastructure.semantic_source import YamlSemanticLayerSource
from venergy_agent.infrastructure.sql_validator import SqlglotValidator

MODEL = "google-gla:gemini-test"
CONFIGURED = "google-gla:configured"
COUNT_SQL = "SELECT count(*) AS total FROM sem_uc"


@pytest.fixture
async def layer():
    return await YamlSemanticLayerSource(
        AGENT_ROOT / "semantic" / "semantic_layer.yaml",
        REPO_ROOT / "contracts" / "gold_schema.yaml",
    ).load()


def generation(status="ok", sql=COUNT_SQL, assumptions=(), clarification=None, model=MODEL):
    draft = SqlDraft(
        status=DraftStatus(status),
        sql=sql if status == "ok" else None,
        assumptions=tuple(assumptions),
        clarification_question=clarification,
    )
    return Generation(draft=draft, model=model, input_tokens=10, output_tokens=5)


class ScriptedGenerator:
    def __init__(self, *outcomes):
        self._outcomes = outcomes
        self.feedbacks = []

    async def generate(self, question, layer, feedback):
        self.feedbacks.append(feedback)
        outcome = self._outcomes[min(len(self.feedbacks), len(self._outcomes)) - 1]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class ScriptedExecutor:
    def __init__(self, *outcomes):
        self._outcomes = outcomes
        self.queries = []

    async def execute(self, query):
        self.queries.append(query)
        outcome = self._outcomes[min(len(self.queries), len(self._outcomes)) - 1]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class FixedWriter:
    def __init__(self, text=None, error=None):
        self._text = text
        self._error = error
        self.calls = 0

    async def write(self, question, draft, result):
        self.calls += 1
        if self._error:
            raise self._error
        return self._text


class BrokenValidator:
    def validate(self, sql, allowed_views):
        raise ValueError("bug no validador")


def result(rows=({"total": 3},), row_count=None, truncated=False):
    return QueryResult(
        columns=("total",),
        rows=tuple(rows),
        row_count=len(rows) if row_count is None else row_count,
        truncated=truncated,
    )


def use_case(layer, generator, executor=None, writer=None, **settings):
    values = {
        "max_question_chars": 500,
        "max_correction_attempts": 3,
        "answer_sample_rows": 20,
    }
    values.update(settings)
    return AskUseCase(
        layer=layer,
        generator=generator,
        validator=SqlglotValidator(dialect="postgres", max_rows=200, allowed_schema="gold"),
        executor=executor or ScriptedExecutor(result()),
        answer_writer=writer or FixedWriter(error=RuntimeError("sem redator")),
        prompt_version="v1",
        configured_model=CONFIGURED,
        **values,
    )


# --- entrada -----------------------------------------------------------------------------


async def test_blank_question_is_refused_without_calling_the_model(layer):
    generator = ScriptedGenerator(generation())

    answer = await use_case(layer, generator).ask("   ", "s1")

    assert answer.status is AnswerStatus.REFUSED
    assert generator.feedbacks == []


async def test_question_over_the_limit_is_refused_without_calling_the_model(layer):
    generator = ScriptedGenerator(generation())

    answer = await use_case(layer, generator, max_question_chars=10).ask("x" * 11, "s1")

    assert answer.refused_reason == TOO_LONG_QUESTION.format(limit=10)
    assert generator.feedbacks == []


# --- status sem SQL ----------------------------------------------------------------------


async def test_unknown_draft_ends_as_unknown_without_running_sql(layer):
    executor = ScriptedExecutor(result())

    answer = await use_case(layer, ScriptedGenerator(generation("unknown")), executor).ask(
        "Qual o CEP da UC?", "s1"
    )

    assert answer.status is AnswerStatus.UNKNOWN
    assert answer.refused_reason == UNKNOWN_REASON
    assert answer.sql is None and answer.confidence is Confidence.UNKNOWN
    assert executor.queries == []


async def test_refuse_draft_ends_as_refused(layer):
    answer = await use_case(layer, ScriptedGenerator(generation("refuse"))).ask("apague", "s1")

    assert answer.status is AnswerStatus.REFUSED
    assert answer.refused_reason == REFUSED_REASON
    assert "consumo, faturamento, interrupções e atendimento" in REFUSED_REASON
    assert "altera" not in REFUSED_REASON


async def test_clarify_draft_asks_back_without_sql(layer):
    answer = await use_case(
        layer, ScriptedGenerator(generation("clarify", clarification="Qual mês?"))
    ).ask("venda do mês", "s1")

    assert answer.status is AnswerStatus.CLARIFY
    assert answer.clarification == "Qual mês?"
    assert answer.answer == CLARIFY_PREFIX + "Qual mês?"
    assert answer.sql is None


# --- caminho feliz -----------------------------------------------------------------------


async def test_valid_draft_is_executed_and_answered_with_its_rows(layer):
    executor = ScriptedExecutor(result(rows=({"total": 3},)))

    answer = await use_case(layer, ScriptedGenerator(generation()), executor).ask(
        "Quantas UCs existem?", "s1"
    )

    assert answer.status is AnswerStatus.ANSWERED
    assert answer.rows == ({"total": 3},)
    assert answer.row_count == 1
    assert answer.sources == ("sem_uc",)
    assert answer.sql == executor.queries[0].sql
    assert answer.sql.upper().endswith("LIMIT 200")
    assert answer.model == MODEL
    assert answer.prompt_version == "v1"
    assert answer.confidence is Confidence.HIGH
    assert answer.latency_ms >= 0


async def test_empty_result_is_answered_with_low_confidence_and_says_so(layer):
    empty = result(rows=(), row_count=0)

    answer = await use_case(layer, ScriptedGenerator(generation()), ScriptedExecutor(empty)).ask(
        "UCs em Marte?", "s1"
    )

    assert answer.status is AnswerStatus.ANSWERED
    assert answer.confidence is Confidence.LOW
    assert answer.answer == EMPTY_RESULT


async def test_truncated_result_is_low_confidence_and_warns_about_the_limit(layer):
    capped = result(rows=({"total": 1},) * 2, row_count=200, truncated=True)

    answer = await use_case(layer, ScriptedGenerator(generation()), ScriptedExecutor(capped)).ask(
        "todas as UCs", "s1"
    )

    assert answer.truncated is True
    assert answer.confidence is Confidence.LOW
    assert "limitado a 200 linhas" in answer.answer


async def test_declared_assumptions_make_the_answer_medium_and_are_listed(layer):
    answer = await use_case(
        layer, ScriptedGenerator(generation(assumptions=("receita = receita faturada",)))
    ).ask("receita de março", "s1")

    assert answer.confidence is Confidence.MEDIUM
    assert answer.assumptions == ("receita = receita faturada",)
    assert "receita = receita faturada" in answer.answer


async def test_sample_is_capped_but_row_count_is_the_real_total(layer):
    many = result(rows=tuple({"total": n} for n in range(5)), row_count=5)

    answer = await use_case(
        layer, ScriptedGenerator(generation()), ScriptedExecutor(many), answer_sample_rows=2
    ).ask("liste", "s1")

    assert len(answer.rows) == 2
    assert answer.row_count == 5


# --- correção ----------------------------------------------------------------------------


async def test_rejected_sql_goes_back_to_the_model_with_the_reason(layer):
    generator = ScriptedGenerator(generation(sql="DELETE FROM sem_uc"), generation(sql=COUNT_SQL))

    answer = await use_case(layer, generator).ask("quantas UCs?", "s1")

    feedback = generator.feedbacks[1]
    assert feedback.error_kind is ErrorKind.REJECTED
    assert feedback.previous_sql == "DELETE FROM sem_uc"
    assert feedback.message
    assert answer.status is AnswerStatus.ANSWERED
    assert answer.confidence is Confidence.MEDIUM


async def test_execution_error_goes_back_with_its_kind_and_the_draft_sql(layer):
    generator = ScriptedGenerator(generation(), generation())
    executor = ScriptedExecutor(
        QueryExecutionError(ErrorKind.UNKNOWN_OBJECT, "coluna não existe"), result()
    )

    answer = await use_case(layer, generator, executor).ask("quantas?", "s1")

    feedback = generator.feedbacks[1]
    assert feedback.error_kind is ErrorKind.UNKNOWN_OBJECT
    assert feedback.message == "coluna não existe"
    assert feedback.previous_sql == COUNT_SQL
    assert answer.status is AnswerStatus.ANSWERED


async def test_unclassified_database_error_fails_at_once_without_retry(layer):
    generator = ScriptedGenerator(generation(), generation())
    executor = ScriptedExecutor(PermissionError("sem permissão"))

    answer = await use_case(layer, generator, executor).ask("quantas?", "s1")

    assert answer.status is AnswerStatus.FAILED
    assert answer.refused_reason == DATABASE_FAILED
    assert len(generator.feedbacks) == 1
    assert answer.sql is not None


async def test_attempts_are_capped_and_the_last_sql_is_kept_for_audit(layer):
    generator = ScriptedGenerator(generation(sql="DELETE FROM sem_uc"))

    answer = await use_case(layer, generator, max_correction_attempts=2).ask("x", "s1")

    assert len(generator.feedbacks) == 2
    assert answer.status is AnswerStatus.FAILED
    assert answer.refused_reason == ATTEMPTS_FAILED.format(attempts=2)
    assert answer.sql == "DELETE FROM sem_uc"


async def test_model_error_ends_as_failed_with_the_configured_model(layer):
    answer = await use_case(layer, ScriptedGenerator(RuntimeError("503"))).ask("x", "s1")

    assert answer.status is AnswerStatus.FAILED
    assert answer.refused_reason == MODEL_FAILED
    assert answer.sql is None
    assert answer.model == CONFIGURED


# --- contrato: ask nunca levanta exceção --------------------------------------------------


async def test_ask_never_raises_even_when_a_port_breaks(layer):
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

    answer = await agent.ask("quantas?", "s1")

    assert answer.status is AnswerStatus.FAILED
    assert answer.refused_reason == INTERNAL_FAILED


# --- narrativa e verificação numérica -----------------------------------------------------


async def test_narrative_with_supported_numbers_replaces_the_deterministic_text(layer):
    writer = FixedWriter(text="Há 3 UCs cadastradas.")

    answer = await use_case(layer, ScriptedGenerator(generation()), writer=writer).ask(
        "quantas?", "s1"
    )

    assert answer.answer == "Há 3 UCs cadastradas."
    assert writer.calls == 1


async def test_narrative_with_an_invented_number_falls_back_to_the_deterministic_text(layer):
    writer = FixedWriter(text="Há 999 UCs cadastradas.")

    answer = await use_case(layer, ScriptedGenerator(generation()), writer=writer).ask(
        "quantas?", "s1"
    )

    assert "999" not in answer.answer
    assert answer.answer.startswith("A consulta devolveu 1 linha(s).")


async def test_narrative_with_an_unreadable_number_falls_back_instead_of_failing(layer):
    writer = FixedWriter(text="Classes 1,2,3 com 3 UCs.")

    answer = await use_case(layer, ScriptedGenerator(generation()), writer=writer).ask(
        "quantas?", "s1"
    )

    assert answer.status is AnswerStatus.ANSWERED
    assert answer.answer.startswith("A consulta devolveu 1 linha(s).")


@pytest.mark.parametrize(
    "text",
    [
        "Há 3 UCs em sem_uc.",
        "Os dados de sem_kpis_mensais mostram 3 UCs.",
        "Consultei gold_fato_faturamento_mensal e achei 3 UCs.",
    ],
)
async def test_narrative_naming_a_table_or_view_falls_back(layer, text):
    writer = FixedWriter(text=text)

    answer = await use_case(layer, ScriptedGenerator(generation()), writer=writer).ask(
        "quantas?", "s1"
    )

    assert answer.answer.startswith("A consulta devolveu 1 linha(s).")
    assert "sem_" not in answer.answer
    assert "gold_" not in answer.answer


async def test_narrative_with_the_word_sem_alone_is_kept(layer):
    writer = FixedWriter(text="Há 3 UCs, sem interrupções registradas.")

    answer = await use_case(layer, ScriptedGenerator(generation()), writer=writer).ask(
        "quantas?", "s1"
    )

    assert answer.answer == "Há 3 UCs, sem interrupções registradas."


@pytest.mark.parametrize(
    "text",
    [
        "A receita_faturada foi de 3 UCs.",
        "Há 3 UCs em SEM_UC.",
    ],
)
async def test_narrative_naming_a_column_or_in_uppercase_falls_back(layer, text):
    writer = FixedWriter(text=text)

    answer = await use_case(layer, ScriptedGenerator(generation()), writer=writer).ask(
        "quantas?", "s1"
    )

    assert answer.answer.startswith("A consulta devolveu 1 linha(s).")


async def test_assumption_naming_a_technical_name_is_left_out_of_the_text(layer):
    writer = FixedWriter(text="Há 999 UCs em sem_uc.")
    assumptions = ("Considerei só o mês atual", "Os dados vêm de sem_kpis_mensais")

    answer = await use_case(
        layer, ScriptedGenerator(generation(assumptions=assumptions)), writer=writer
    ).ask("quantas?", "s1")

    assert "Considerei só o mês atual" in answer.answer
    assert "sem_kpis_mensais" not in answer.answer
    assert answer.assumptions == assumptions


def table(columns, *rows):
    return QueryResult(
        columns=columns,
        rows=tuple(dict(zip(columns, row, strict=True)) for row in rows),
        row_count=len(rows),
        truncated=False,
    )


async def fallback_text(layer, query_result):
    answer = await use_case(
        layer, ScriptedGenerator(generation()), ScriptedExecutor(query_result)
    ).ask("quantas?", "s1")
    return answer.answer


async def test_fallback_text_shows_the_values_of_a_small_result(layer):
    text = await fallback_text(layer, table(("total",), (3,)))

    assert text == "A consulta devolveu 1 linha(s). Resultado: total = 3."


async def test_fallback_text_writes_numbers_in_pt_br_and_null_as_missing(layer):
    query_result = table(
        ("municipio", "receita", "dec"),
        ("Olinda", Decimal("11079.18"), None),
        ("Recife", Decimal("1234567.5"), 0.6),
    )

    text = await fallback_text(layer, query_result)

    assert text.endswith(
        "Resultado: municipio = Olinda, receita = 11.079,18, dec = sem valor; "
        "municipio = Recife, receita = 1.234.567,5, dec = 0,6."
    )


async def test_fallback_text_omits_the_values_of_a_large_result(layer):
    query_result = table(("total",), *[(n,) for n in range(6)])

    text = await fallback_text(layer, query_result)

    assert text == "A consulta devolveu 6 linha(s)."


async def test_writer_error_falls_back_to_the_deterministic_text(layer):
    writer = FixedWriter(error=RuntimeError("provedor caiu"))

    answer = await use_case(layer, ScriptedGenerator(generation()), writer=writer).ask(
        "quantas?", "s1"
    )

    assert answer.status is AnswerStatus.ANSWERED
    assert answer.answer.startswith("A consulta devolveu")


# --- logs ------------------------------------------------------------------------------


async def test_each_step_is_logged_as_json_and_row_values_never_reach_the_logs(layer, caplog):
    secret = "dado-pessoal-xyz"
    private = result(rows=({"total": secret},))
    caplog.set_level(logging.INFO, logger="venergy_agent.ask")

    await use_case(layer, ScriptedGenerator(generation()), ScriptedExecutor(private)).ask(
        "quantas?", "s1"
    )

    lines = [json.loads(record.getMessage()) for record in caplog.records]
    steps = [line["step"] for line in lines]
    assert {"pergunta", "geracao", "validacao", "execucao", "resposta"} <= set(steps)
    assert all(line["session_id"] == "s1" and line["request_id"] for line in lines)
    assert not any(secret in record.getMessage() for record in caplog.records)


async def test_clarify_writes_the_final_answer_log_line(layer, caplog):
    caplog.set_level(logging.INFO, logger="venergy_agent.ask")

    await use_case(layer, ScriptedGenerator(generation("clarify", clarification="Qual mês?"))).ask(
        "receita?", "s1"
    )

    lines = [json.loads(record.getMessage()) for record in caplog.records]
    assert [line["status"] for line in lines if line["step"] == "resposta"] == ["clarify"]


async def test_validation_and_execution_steps_log_their_own_latency(layer, caplog):
    caplog.set_level(logging.INFO, logger="venergy_agent.ask")

    await use_case(layer, ScriptedGenerator(generation())).ask("quantas?", "s1")

    lines = [json.loads(record.getMessage()) for record in caplog.records]
    for step in ("validacao", "execucao"):
        (line,) = [entry for entry in lines if entry["step"] == step and "latency_ms" in entry]
        assert isinstance(line["latency_ms"], int) and line["latency_ms"] >= 0


async def test_number_from_the_question_does_not_make_a_narrative_faithful(layer):
    writer = FixedWriter(text="Há 3 UCs acima de 300 kWh.")

    answer = await use_case(layer, ScriptedGenerator(generation()), writer=writer).ask(
        "Quantas UCs estão acima de 300 kWh?", "s1"
    )

    assert "300" not in answer.answer
    assert answer.answer.startswith("A consulta devolveu 1 linha(s).")


async def test_long_text_values_are_shortened_in_the_fallback_answer(layer):
    long_text = "x" * 300

    answer = await use_case(
        layer,
        ScriptedGenerator(generation()),
        ScriptedExecutor(result(rows=({"total": long_text},))),
    ).ask("quantas?", "s1")

    assert "x" * 300 not in answer.answer
    assert "x" * 117 + "..." in answer.answer
