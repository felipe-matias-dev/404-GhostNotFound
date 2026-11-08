import asyncio
import json
import logging
from decimal import Decimal

import pytest

from venergy_agent.application.ask import (
    ATTEMPTS_FAILED,
    BUDGET_EXHAUSTED,
    BUDGET_UNAVAILABLE,
    CLARIFY_PREFIX,
    DATABASE_FAILED,
    DEADLINE_FAILED,
    EMPTY_RESULT,
    GENERIC_CLARIFICATION,
    INTERNAL_FAILED,
    MODEL_FAILED,
    PERIOD_NOT_GIVEN,
    REFUSED_REASON,
    TECHNICAL_NAME,
    TOO_LONG_QUESTION,
    UNKNOWN_REASON,
    AskUseCase,
)
from venergy_agent.config import AGENT_ROOT, REPO_ROOT
from venergy_agent.domain.answer import AnswerStatus, Confidence
from venergy_agent.domain.conversation import ConversationTurn
from venergy_agent.domain.errors import ErrorKind, ModelCallFailed, QueryExecutionError
from venergy_agent.domain.events import AnswerEvent, Stage, StageEvent
from venergy_agent.domain.narration import Narration
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
        self.histories = []
        self.questions = []

    async def generate(self, question, layer, feedback, history=()):
        self.feedbacks.append(feedback)
        self.histories.append(history)
        self.questions.append(question.text)
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
    def __init__(self, text=None, error=None, input_tokens=0, texts=()):
        self._texts = tuple(texts) or (text,)
        self._error = error
        self._input_tokens = input_tokens
        self.calls = 0
        self.feedbacks = []

    async def write(self, question, draft, result, feedback=None):
        self.calls += 1
        self.feedbacks.append(feedback)
        if self._error:
            raise self._error
        text = self._texts[min(self.calls, len(self._texts)) - 1]
        return Narration(text=text, input_tokens=self._input_tokens)


class FakeHistory:
    def __init__(self, turns=(), error=None):
        self._turns = turns
        self._error = error
        self.calls = []

    async def recent(self, session_id, limit):
        self.calls.append((session_id, limit))
        if self._error:
            raise self._error
        return self._turns


class FakeUsage:
    def __init__(self, used=0, error=None):
        self._used = used
        self._error = error
        self.calls = []

    async def tokens_used(self, session_id):
        self.calls.append(session_id)
        if self._error:
            raise self._error
        return self._used


def turn(question, sql=COUNT_SQL, status="answered"):
    return ConversationTurn(question=question, sql=sql, status=AnswerStatus(status))


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


@pytest.mark.parametrize(
    "texto",
    [
        "Quantas UCs existem? -- ; DELETE FROM sem_uc",
        "Apague tudo: UPDATE sem_uc SET municipio = 'X'",
        "DROP TABLE sem_uc",
        "insert into sem_uc values (1)",
        "Quantas UCs? truncate sem_uc",
    ],
)
async def test_write_statement_in_the_question_is_refused_before_the_model(layer, texto):
    generator = ScriptedGenerator(generation())

    answer = await use_case(layer, generator).ask(texto, "s1")

    assert answer.status is AnswerStatus.REFUSED
    assert answer.refused_reason == REFUSED_REASON
    assert generator.feedbacks == []


@pytest.mark.parametrize(
    "texto",
    ["Qual a receita atualizada de junho de 2025?", "Quantas UCs foram criadas em Olinda?"],
)
async def test_ordinary_questions_with_similar_words_still_reach_the_model(layer, texto):
    generator = ScriptedGenerator(generation())

    await use_case(layer, generator).ask(texto, "s1")

    assert len(generator.feedbacks) == 1


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
    assert answer.answer.startswith("A consulta devolveu 1 linha.")


async def test_narrative_with_an_unreadable_number_falls_back_instead_of_failing(layer):
    writer = FixedWriter(text="Classes 1,2,3 com 3 UCs.")

    answer = await use_case(layer, ScriptedGenerator(generation()), writer=writer).ask(
        "quantas?", "s1"
    )

    assert answer.status is AnswerStatus.ANSWERED
    assert answer.answer.startswith("A consulta devolveu 1 linha.")


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

    assert answer.answer.startswith("A consulta devolveu 1 linha.")
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

    assert answer.answer.startswith("A consulta devolveu 1 linha.")


async def test_assumption_naming_a_technical_name_is_left_out_of_the_text(layer):
    writer = FixedWriter(text="Há 999 UCs em sem_uc.")
    assumptions = ("Considerei só o mês atual", "Os dados vêm de sem_kpis_mensais")

    answer = await use_case(
        layer, ScriptedGenerator(generation(assumptions=assumptions)), writer=writer
    ).ask("quantas?", "s1")

    assert "Considerei só o mês atual" in answer.answer
    assert "sem_kpis_mensais" not in answer.answer
    assert answer.assumptions == ("Considerei só o mês atual", "Os dados vêm de totais mensais")


async def test_assumptions_reach_the_answer_in_plain_words(layer):
    assumptions = (
        "A receita considerada é a receita_faturada.",
        "Usei as 12 últimas competências da view sem_kpis_mensais.",
    )

    answer = await use_case(layer, ScriptedGenerator(generation(assumptions=assumptions))).ask(
        "quantas?", "s1"
    )

    assert answer.assumptions == (
        "A receita considerada é a receita faturada.",
        "Usei as 12 últimas competências dos dados de totais mensais.",
    )
    assert answer.answer.endswith(
        "Suposições: A receita considerada é a receita faturada; Usei as 12 últimas "
        "competências dos dados de totais mensais."
    )


async def test_fallback_text_writes_labels_with_accents_and_negative_money_first(layer):
    query_result = table(
        ("efeito_preco", "efeito_volume", "variacao_percentual"),
        (Decimal("14425779.04"), Decimal("-4656505.19"), Decimal("8.01")),
    )

    text = await fallback_text(layer, query_result)

    assert text.endswith(
        "Resultado: efeito preço = R$ 14.425.779,04, efeito volume = -R$ 4.656.505,19, "
        "variação percentual = 8,01%."
    )


async def test_narrative_without_the_period_falls_back_to_a_text_that_has_it(layer):
    writer = FixedWriter(text="Há 3 UCs.")
    executor = ScriptedExecutor(table(("competencia", "total"), ("2025-06", 3)))

    answer = await use_case(
        layer, ScriptedGenerator(generation()), executor=executor, writer=writer
    ).ask("quantas?", "s1")

    assert answer.answer.startswith("A consulta devolveu 1 linha. Período: 2025-06.")


@pytest.mark.parametrize("text", ["Em junho de 2025 havia 3 UCs.", "Em 06/2025 havia 3 UCs."])
async def test_narrative_that_names_the_period_is_kept(layer, text):
    writer = FixedWriter(text=text)
    executor = ScriptedExecutor(table(("competencia", "total"), ("2025-06", 3)))

    answer = await use_case(
        layer, ScriptedGenerator(generation()), executor=executor, writer=writer
    ).ask("quantas?", "s1")

    assert answer.answer == text


async def test_a_range_needs_both_ends_in_the_narrative(layer):
    writer = FixedWriter(text="Em dezembro de 2025 havia 3 UCs.")
    executor = ScriptedExecutor(table(("competencia", "total"), ("2025-01", 3), ("2025-12", 3)))

    answer = await use_case(
        layer, ScriptedGenerator(generation()), executor=executor, writer=writer
    ).ask("quantas?", "s1")

    assert answer.answer.startswith("A consulta devolveu 2 linhas. Período: 2025-01 a 2025-12.")


@pytest.mark.parametrize(
    "text",
    [
        "Entre junho e dezembro de 2025 havia 3 UCs.",
        "De jun/2025 a dez/2025 havia 3 UCs.",
        "De junho/2025 a dezembro/2025 havia 3 UCs.",
    ],
)
async def test_common_ways_to_name_a_range_keep_the_narrative(layer, text):
    writer = FixedWriter(text=text)
    executor = ScriptedExecutor(table(("competencia", "total"), ("2025-06", 3), ("2025-12", 3)))

    answer = await use_case(
        layer, ScriptedGenerator(generation()), executor=executor, writer=writer
    ).ask("quantas?", "s1")

    assert answer.answer == text


async def test_the_narrative_period_is_the_one_in_the_rows_the_writer_saw(layer):
    writer = FixedWriter(text="Entre janeiro e fevereiro de 2025 havia 3 UCs.")
    executor = ScriptedExecutor(
        table(("competencia", "total"), ("2025-01", 3), ("2025-02", 3), ("2025-03", 3))
    )

    answer = await use_case(
        layer,
        ScriptedGenerator(generation()),
        executor=executor,
        writer=writer,
        answer_sample_rows=2,
    ).ask("quantas?", "s1")

    assert answer.answer == "Entre janeiro e fevereiro de 2025 havia 3 UCs."


FILTERED_SQL = "SELECT count(*) AS total FROM sem_faturamento_mensal WHERE competencia = '2025-06'"


async def test_a_month_in_the_sql_filter_can_be_named_when_the_rows_have_no_month(layer):
    writer = FixedWriter(text="Em junho de 2025 havia 3 UCs.")

    answer = await use_case(
        layer,
        ScriptedGenerator(generation(sql=FILTERED_SQL)),
        executor=ScriptedExecutor(table(("total",), (3,))),
        writer=writer,
    ).ask("quantas em junho de 2025?", "s1")

    assert answer.answer == "Em junho de 2025 havia 3 UCs."


async def test_a_month_outside_the_sql_filter_still_drops_the_narrative(layer):
    writer = FixedWriter(text="Em junho de 2024 havia 3 UCs.")

    answer = await use_case(
        layer,
        ScriptedGenerator(generation(sql=FILTERED_SQL)),
        executor=ScriptedExecutor(table(("total",), (3,))),
        writer=writer,
    ).ask("quantas em junho de 2025?", "s1")

    assert answer.answer.startswith("A consulta devolveu 1 linha.")


async def test_a_month_in_the_sql_filter_must_be_named_when_the_rows_have_no_month(layer):
    writer = FixedWriter(text="Havia 3 UCs.")

    answer = await use_case(
        layer,
        ScriptedGenerator(generation(sql=FILTERED_SQL)),
        executor=ScriptedExecutor(table(("total",), (3,))),
        writer=writer,
    ).ask("quantas em junho de 2025?", "s1")

    assert answer.answer.startswith("A consulta devolveu 1 linha.")


async def test_the_fallback_names_the_months_of_the_sql_filter_when_the_rows_have_no_month(layer):
    range_sql = (
        "SELECT count(*) AS total FROM sem_faturamento_mensal "
        "WHERE competencia BETWEEN '2025-01' AND '2025-12'"
    )

    answer = await use_case(
        layer,
        ScriptedGenerator(generation(sql=range_sql)),
        executor=ScriptedExecutor(table(("total",), (3,))),
    ).ask("quantas em 2025?", "s1")

    assert answer.answer.startswith("A consulta devolveu 1 linha. Período: 2025-01 a 2025-12.")


async def test_a_range_in_the_sql_filter_needs_both_ends_in_the_narrative(layer):
    writer = FixedWriter(text="Em dezembro de 2025 havia 3 UCs.")
    range_sql = (
        "SELECT count(*) AS total FROM sem_faturamento_mensal "
        "WHERE competencia BETWEEN '2025-01' AND '2025-12'"
    )

    answer = await use_case(
        layer,
        ScriptedGenerator(generation(sql=range_sql)),
        executor=ScriptedExecutor(table(("total",), (3,))),
        writer=writer,
    ).ask("quantas em 2025?", "s1")

    assert answer.answer.startswith("A consulta devolveu 1 linha.")


@pytest.mark.parametrize("text", ["Em 2025 havia 3 UCs.", "No ano de 2025, havia 3 UCs."])
async def test_a_whole_year_in_the_sql_filter_can_be_named_by_the_year(layer, text):
    writer = FixedWriter(text=text)
    year_sql = (
        "SELECT count(*) AS total FROM sem_faturamento_mensal "
        "WHERE competencia BETWEEN '2025-01' AND '2025-12'"
    )

    answer = await use_case(
        layer,
        ScriptedGenerator(generation(sql=year_sql)),
        executor=ScriptedExecutor(table(("total",), (3,))),
        writer=writer,
    ).ask("quantas em 2025?", "s1")

    assert answer.answer == text


async def test_whole_years_need_both_years_named(layer):
    writer = FixedWriter(text="Em 2025 havia 3 UCs.")
    years_sql = (
        "SELECT count(*) AS total FROM sem_faturamento_mensal "
        "WHERE competencia BETWEEN '2024-01' AND '2025-12'"
    )

    answer = await use_case(
        layer,
        ScriptedGenerator(generation(sql=years_sql)),
        executor=ScriptedExecutor(table(("total",), (3,))),
        writer=writer,
    ).ask("quantas em 2024 e 2025?", "s1")

    assert answer.answer.startswith("A consulta devolveu 1 linha.")


async def test_a_year_used_as_a_filter_prefix_can_be_cited(layer):
    writer = FixedWriter(text="A receita foi de R$ 10,00 em 2024 e de R$ 12,00 em 2025.")
    years_sql = (
        "SELECT sum(CASE WHEN competencia LIKE '2024-%' THEN receita_faturada END) AS r24, "
        "sum(CASE WHEN competencia LIKE '2025-%' THEN receita_faturada END) AS r25 "
        "FROM sem_faturamento_mensal"
    )

    answer = await use_case(
        layer,
        ScriptedGenerator(generation(sql=years_sql)),
        executor=ScriptedExecutor(table(("r24", "r25"), (Decimal("10.00"), Decimal("12.00")))),
        writer=writer,
    ).ask("quanto cresceu entre 2024 e 2025?", "s1")

    assert answer.answer == "A receita foi de R$ 10,00 em 2024 e de R$ 12,00 em 2025."


async def test_a_year_from_another_month_is_not_taken_as_the_period(layer):
    writer = FixedWriter(text="Entre dezembro de 2024 e janeiro de 2025 havia 3 UCs.")
    executor = ScriptedExecutor(table(("competencia", "total"), ("2025-01", 3), ("2025-12", 3)))

    answer = await use_case(
        layer, ScriptedGenerator(generation()), executor=executor, writer=writer
    ).ask("quantas?", "s1")

    assert answer.answer.startswith("A consulta devolveu 2 linhas.")


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

    assert text == "A consulta devolveu 1 linha. Resultado: total = 3."


async def test_fallback_text_writes_numbers_in_pt_br_and_null_as_missing(layer):
    query_result = table(
        ("municipio", "receita", "dec"),
        ("Olinda", Decimal("11079.18"), None),
        ("Recife", Decimal("1234567.5"), 0.6),
    )

    text = await fallback_text(layer, query_result)

    assert text.endswith(
        "Resultado: município = Olinda, receita = 11.079,18, DEC = sem valor; "
        "município = Recife, receita = 1.234.567,5, DEC = 0,6."
    )


async def test_fallback_text_trims_long_division_decimals_but_keeps_money_cents(layer):
    query_result = table(
        ("fec", "taxa", "receita"),
        (Decimal("4.5000000000000000"), Decimal("0.05612345678901"), Decimal("35482.70")),
    )

    text = await fallback_text(layer, query_result)

    assert text.endswith("Resultado: FEC = 4,5, taxa = 0,0561, receita = 35.482,70.")


async def test_fallback_text_rounds_long_decimals_to_two_places(layer):
    query_result = table(("cod_alimentador", "dec"), ("ALM-JAB-008", 1.9135965))

    text = await fallback_text(layer, query_result)

    assert text.endswith("Resultado: alimentador = ALM-JAB-008, DEC = 1,91.")


async def test_fallback_text_omits_the_values_of_a_large_result(layer):
    query_result = table(("total",), *[(n,) for n in range(6)])

    text = await fallback_text(layer, query_result)

    assert text == "A consulta devolveu 6 linhas."


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
    assert answer.answer.startswith("A consulta devolveu 1 linha.")


async def test_a_duration_from_the_question_keeps_the_narrative(layer):
    writer = FixedWriter(text="Nos últimos 12 meses, há 3 UCs.")

    answer = await use_case(layer, ScriptedGenerator(generation()), writer=writer).ask(
        "Quantas UCs faturaram nos últimos 12 meses?", "s1"
    )

    assert answer.answer == "Nos últimos 12 meses, há 3 UCs."


async def test_a_duration_from_the_assumptions_keeps_the_narrative(layer):
    writer = FixedWriter(text="Considerando as 12 últimas competências da base, há 3 UCs.")
    draft = generation(assumptions=("O período são as 12 últimas competências da base.",))

    answer = await use_case(layer, ScriptedGenerator(draft), writer=writer).ask(
        "Quantas UCs faturaram recentemente?", "s1"
    )

    assert answer.answer == "Considerando as 12 últimas competências da base, há 3 UCs."


async def test_a_duration_from_the_question_used_as_a_count_drops_the_narrative(layer):
    writer = FixedWriter(text="Há 12 UCs.")

    answer = await use_case(layer, ScriptedGenerator(generation()), writer=writer).ask(
        "Quantas UCs faturaram nos últimos 12 meses?", "s1"
    )

    assert answer.answer.startswith("A consulta devolveu 1 linha.")


async def test_a_refused_narrative_is_written_again_with_the_reason(layer):
    writer = FixedWriter(texts=("Há 999 UCs.", "Há 3 UCs."))

    answer = await use_case(layer, ScriptedGenerator(generation()), writer=writer).ask(
        "quantas?", "s1"
    )

    assert answer.answer == "Há 3 UCs."
    assert writer.feedbacks[0] is None
    assert "999" in writer.feedbacks[1]


async def test_a_narrative_refused_twice_falls_back_to_the_deterministic_text(layer):
    writer = FixedWriter(texts=("Há 999 UCs.", "Há 998 UCs."))

    answer = await use_case(layer, ScriptedGenerator(generation()), writer=writer).ask(
        "quantas?", "s1"
    )

    assert answer.answer.startswith("A consulta devolveu 1 linha.")
    assert writer.calls == 2


async def test_the_reason_for_a_missing_period_names_the_months(layer):
    writer = FixedWriter(texts=("Há 3 UCs.", "Em março de 2025, há 3 UCs."))
    executor = ScriptedExecutor(table(("competencia", "total"), ("2025-03", 3)))

    answer = await use_case(layer, ScriptedGenerator(generation()), executor, writer).ask(
        "quantas?", "s1"
    )

    assert answer.answer == "Em março de 2025, há 3 UCs."
    assert "março de 2025" in writer.feedbacks[1]


async def test_the_reason_for_a_technical_name_asks_for_plain_words(layer):
    writer = FixedWriter(texts=("O total_ucs é 3.", "Há 3 UCs."))

    answer = await use_case(layer, ScriptedGenerator(generation()), writer=writer).ask(
        "quantas?", "s1"
    )

    assert answer.answer == "Há 3 UCs."
    assert "nomes técnicos" in writer.feedbacks[1]


async def test_both_narrations_count_toward_the_answer_usage(layer):
    writer = FixedWriter(texts=("Há 999 UCs.", "Há 3 UCs."), input_tokens=7)

    answer = await use_case(layer, ScriptedGenerator(generation()), writer=writer).ask(
        "quantas?", "s1"
    )

    assert answer.input_tokens == 10 + 7 + 7


async def test_fallback_text_shows_the_values_of_a_result_with_six_columns(layer):
    columns = ("efeito_tarifa", "efeito_bandeira", "efeito_volume", "efeito_mix", "a", "b")
    query_result = table(columns, (1, 2, 3, 4, 5, 6))

    text = await fallback_text(layer, query_result)

    assert "Resultado: " in text and "b = 6" in text


async def test_fallback_text_omits_the_values_of_a_result_with_seven_columns(layer):
    columns = ("a", "b", "c", "d", "e", "f", "g")

    text = await fallback_text(layer, table(columns, (1, 2, 3, 4, 5, 6, 7)))

    assert "Resultado" not in text


async def test_fallback_text_gives_a_unit_to_a_period_alias_and_a_percentage(layer):
    query_result = table(
        ("receita_2024", "variacao_percentual"), (Decimal("16778217.14"), Decimal("0.89"))
    )

    text = await fallback_text(layer, query_result)

    assert text.endswith("Resultado: receita 2024 = R$ 16.778.217,14, variação percentual = 0,89%.")


async def test_long_text_values_are_shortened_in_the_fallback_answer(layer):
    long_text = "x" * 300

    answer = await use_case(
        layer,
        ScriptedGenerator(generation()),
        ScriptedExecutor(result(rows=({"total": long_text},))),
    ).ask("quantas?", "s1")

    assert "x" * 300 not in answer.answer
    assert "x" * 117 + "..." in answer.answer


async def test_without_an_answer_writer_the_answer_is_the_deterministic_text(layer, caplog):
    caplog.set_level(logging.INFO, logger="venergy_agent.ask")
    agent = AskUseCase(
        layer=layer,
        generator=ScriptedGenerator(generation()),
        validator=SqlglotValidator(dialect="postgres", max_rows=200, allowed_schema="gold"),
        executor=ScriptedExecutor(result()),
        answer_writer=None,
        max_question_chars=500,
        max_correction_attempts=3,
        answer_sample_rows=20,
        prompt_version="v1",
        configured_model=CONFIGURED,
    )

    answer = await agent.ask("quantas?", "s1")

    assert answer.status is AnswerStatus.ANSWERED
    assert answer.answer.startswith("A consulta devolveu 1 linha.")
    assert "narrativa_falhou" not in caplog.text


async def test_fallback_text_labels_columns_in_plain_words_with_their_unit(layer):
    query_result = table(
        ("receita_faturada", "kwh_faturado", "n_chamados", "dias_sem_unidade"),
        (Decimal("35482.79"), Decimal("1200"), 85, 3),
    )

    text = await fallback_text(layer, query_result)

    assert text.endswith(
        "Resultado: receita faturada = R$ 35.482,79, energia faturada = 1.200 kWh, "
        "número de chamados = 85, dias sem unidade = 3."
    )
    assert not TECHNICAL_NAME.search(text)


async def test_clarification_naming_a_technical_name_becomes_a_generic_question(layer, caplog):
    caplog.set_level(logging.INFO, logger="venergy_agent.ask")
    question = "Você quer os dados de sem_kpis_mensais ou de sem_faturamento_mensal?"

    answer = await use_case(
        layer, ScriptedGenerator(generation("clarify", clarification=question))
    ).ask("receita?", "s1")

    assert answer.status is AnswerStatus.CLARIFY
    assert answer.clarification == GENERIC_CLARIFICATION
    assert not TECHNICAL_NAME.search(answer.answer)
    assert "nome_tecnico_no_esclarecimento" in caplog.text


# --- memória da conversa -----------------------------------------------------------------


async def test_generator_receives_the_turns_from_the_port_oldest_first_on_every_attempt(layer):
    history = FakeHistory((turn("primeira"), turn("segunda")))
    generator = ScriptedGenerator(generation(sql="DELETE FROM sem_uc"), generation())

    await use_case(layer, generator, history=history, history_turns=3).ask("e em Olinda?", "s1")

    assert generator.histories == [history._turns, history._turns]
    assert history.calls == [("s1", 3)]


async def test_history_is_not_read_when_disabled_or_missing(layer):
    history = FakeHistory((turn("antes"),))
    generator = ScriptedGenerator(generation("unknown"))

    await use_case(layer, generator, history=history, history_turns=0).ask("x", "s1")
    await use_case(layer, generator, history=None, history_turns=3).ask("x", "s1")

    assert history.calls == []
    assert generator.histories == [(), ()]


async def test_history_port_failure_is_logged_and_the_question_goes_on_without_it(layer, caplog):
    caplog.set_level(logging.INFO, logger="venergy_agent.ask")
    history = FakeHistory(error=RuntimeError("auditoria fora"))
    generator = ScriptedGenerator(generation())

    answer = await use_case(layer, generator, history=history, history_turns=3).ask("x", "s1")

    assert answer.status is AnswerStatus.ANSWERED
    assert generator.histories == [()]
    lines = [json.loads(record.getMessage()) for record in caplog.records]
    assert any(line["status"] == "historico_indisponivel" for line in lines)


async def test_history_log_has_the_turn_count_and_never_the_old_questions(layer, caplog):
    caplog.set_level(logging.INFO, logger="venergy_agent.ask")
    history = FakeHistory((turn("pergunta-secreta-antiga"), turn("outra-antiga")))

    await use_case(layer, ScriptedGenerator(generation()), history=history, history_turns=3).ask(
        "x", "s1"
    )

    lines = [json.loads(record.getMessage()) for record in caplog.records]
    (line,) = [entry for entry in lines if entry["step"] == "historico"]
    assert line["turnos"] == 2
    assert not any("antiga" in record.getMessage() for record in caplog.records)


async def test_invalid_questions_do_not_read_the_history(layer):
    history = FakeHistory((turn("antes"),))
    agent = use_case(
        layer,
        ScriptedGenerator(generation()),
        history=history,
        history_turns=3,
        max_question_chars=5,
    )

    await agent.ask("   ", "s1")
    await agent.ask("x" * 6, "s1")

    assert history.calls == []


# --- tokens e orçamento ------------------------------------------------------------------


async def test_answer_after_a_correction_sums_the_tokens_of_every_generation(layer):
    generator = ScriptedGenerator(generation(sql="DELETE FROM sem_uc"), generation())

    answer = await use_case(layer, generator).ask("quantas?", "s1")

    assert answer.status is AnswerStatus.ANSWERED
    assert (answer.input_tokens, answer.output_tokens) == (20, 10)


@pytest.mark.parametrize(
    "draft",
    [generation("unknown"), generation("refuse"), generation("clarify", clarification="Qual mês?")],
)
async def test_statuses_without_sql_carry_the_tokens_of_the_call(layer, draft):
    answer = await use_case(layer, ScriptedGenerator(draft)).ask("x", "s1")

    assert (answer.input_tokens, answer.output_tokens) == (10, 5)


async def test_provider_error_after_an_attempt_keeps_the_tokens_already_spent(layer):
    generator = ScriptedGenerator(generation(sql="DELETE FROM sem_uc"), RuntimeError("503"))

    answer = await use_case(layer, generator).ask("x", "s1")

    assert answer.status is AnswerStatus.FAILED
    assert (answer.input_tokens, answer.output_tokens) == (10, 5)


async def test_exhausted_attempts_carry_the_tokens_of_all_of_them(layer):
    generator = ScriptedGenerator(generation(sql="DELETE FROM sem_uc"))

    answer = await use_case(layer, generator, max_correction_attempts=2).ask("x", "s1")

    assert (answer.input_tokens, answer.output_tokens) == (20, 10)


async def test_question_barred_before_the_model_spends_no_tokens(layer):
    answer = await use_case(layer, ScriptedGenerator(generation())).ask("  ", "s1")

    assert (answer.input_tokens, answer.output_tokens) == (0, 0)


async def test_exhausted_budget_refuses_without_calling_the_model_or_the_history(layer):
    generator = ScriptedGenerator(generation())
    history = FakeHistory((turn("antes"),))
    usage = FakeUsage(used=1000)

    answer = await use_case(
        layer, generator, history=history, history_turns=3, usage=usage, session_token_budget=1000
    ).ask("quantas?", "s1")

    assert answer.status is AnswerStatus.REFUSED
    assert answer.refused_reason == BUDGET_EXHAUSTED
    assert (answer.input_tokens, answer.output_tokens) == (0, 0)
    assert generator.feedbacks == [] and history.calls == []
    assert usage.calls == ["s1"]


async def test_usage_under_the_budget_goes_on_normally(layer):
    answer = await use_case(
        layer,
        ScriptedGenerator(generation()),
        usage=FakeUsage(used=999),
        session_token_budget=1000,
    ).ask("quantas?", "s1")

    assert answer.status is AnswerStatus.ANSWERED


@pytest.mark.parametrize("settings", [{"session_token_budget": 0}, {"usage": None}])
async def test_usage_is_not_read_when_the_budget_is_off_or_the_port_is_missing(layer, settings):
    usage = FakeUsage(used=10**9)
    values = {"usage": usage, "session_token_budget": 1000, **settings}

    answer = await use_case(layer, ScriptedGenerator(generation()), **values).ask("x", "s1")

    assert answer.status is AnswerStatus.ANSWERED
    assert usage.calls == []


async def test_unreadable_usage_fails_closed_without_calling_the_model(layer):
    generator = ScriptedGenerator(generation())
    usage = FakeUsage(error=RuntimeError("auditoria fora"))

    answer = await use_case(layer, generator, usage=usage, session_token_budget=1000).ask("x", "s1")

    assert answer.status is AnswerStatus.FAILED
    assert answer.refused_reason == BUDGET_UNAVAILABLE
    assert generator.feedbacks == []


async def test_failed_model_call_keeps_the_tokens_it_already_spent(layer):
    generator = ScriptedGenerator(ModelCallFailed(input_tokens=100, output_tokens=20))

    answer = await use_case(layer, generator).ask("x", "s1")

    assert answer.status is AnswerStatus.FAILED
    assert (answer.input_tokens, answer.output_tokens) == (100, 20)


async def test_failed_narration_keeps_the_tokens_of_the_generation_and_of_the_attempt(layer):
    writer = FixedWriter(error=ModelCallFailed(input_tokens=30, output_tokens=5))

    answer = await use_case(layer, ScriptedGenerator(generation()), writer=writer).ask("x", "s1")

    assert answer.status is AnswerStatus.ANSWERED
    assert (answer.input_tokens, answer.output_tokens) == (10 + 30, 5 + 5)


async def test_budget_log_has_numbers_only(layer, caplog):
    caplog.set_level(logging.INFO, logger="venergy_agent.ask")

    await use_case(
        layer, ScriptedGenerator(generation()), usage=FakeUsage(used=7), session_token_budget=1000
    ).ask("quantas?", "s1")

    lines = [json.loads(record.getMessage()) for record in caplog.records]
    (line,) = [entry for entry in lines if entry["step"] == "orcamento"]
    assert (line["tokens_usados"], line["orcamento"]) == (7, 1000)


async def test_narration_tokens_count_toward_the_answer_usage(layer):
    writer = FixedWriter(text="Há 3 UCs.", input_tokens=500)

    answer = await use_case(layer, ScriptedGenerator(generation()), writer=writer).ask(
        "quantas?", "s1"
    )

    assert answer.answer == "Há 3 UCs."
    assert answer.input_tokens == generation().input_tokens + 500


@pytest.mark.parametrize("turns", [(), None])
async def test_followup_without_a_previous_turn_asks_back_without_calling_the_model(layer, turns):
    generator = ScriptedGenerator(generation())
    history = None if turns is None else FakeHistory(turns)

    answer = await use_case(layer, generator, history=history, history_turns=3).ask(
        "Agora faça o mesmo para Olinda.", "s1"
    )

    assert answer.status is AnswerStatus.CLARIFY
    assert answer.sql is None
    assert answer.input_tokens == 0
    assert generator.histories == []


async def test_followup_with_a_previous_turn_goes_to_the_model(layer):
    generator = ScriptedGenerator(generation())
    history = FakeHistory((turn("Quantas UCs existem em Recife?"),))

    answer = await use_case(
        layer, generator, ScriptedExecutor(result()), history=history, history_turns=3
    ).ask("E em Olinda?", "s1")

    assert answer.status is AnswerStatus.ANSWERED
    assert len(generator.histories) == 1


async def test_standalone_question_without_history_goes_to_the_model(layer):
    generator = ScriptedGenerator(generation())

    await use_case(
        layer, generator, ScriptedExecutor(result()), history=FakeHistory(()), history_turns=3
    ).ask("Quantas UCs existem em Olinda?", "s1")

    assert len(generator.histories) == 1


class BlockingGenerator:
    def __init__(self):
        self.release = asyncio.Event()
        self.cancelled = False

    async def generate(self, question, layer, feedback, history=()):
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


async def test_stream_emits_stages_then_the_answer(layer):
    events = await collect(
        use_case(layer, ScriptedGenerator(generation()), ScriptedExecutor(result()))
    )

    assert stages(events) == [Stage.UNDERSTANDING, Stage.QUERYING, Stage.WRITING]
    assert isinstance(events[-1], AnswerEvent)
    assert events[-1].answer.status is AnswerStatus.ANSWERED


async def test_stream_emits_correcting_before_a_new_attempt(layer):
    generator = ScriptedGenerator(generation(sql="DELETE FROM sem_uc"), generation())

    events = await collect(use_case(layer, generator, ScriptedExecutor(result())))

    assert stages(events) == [
        Stage.UNDERSTANDING,
        Stage.QUERYING,
        Stage.CORRECTING,
        Stage.QUERYING,
        Stage.WRITING,
    ]
    assert events[-1].answer.status is AnswerStatus.ANSWERED


async def test_stream_of_an_invalid_question_has_only_the_answer(layer):
    events = await collect(use_case(layer, ScriptedGenerator(generation())), "   ")

    assert len(events) == 1
    assert events[0].answer.status is AnswerStatus.REFUSED


async def test_stream_ends_with_a_failed_answer_on_an_unexpected_error(layer):
    agent = use_case(layer, ScriptedGenerator(generation()))
    agent._validator = BrokenValidator()

    events = await collect(agent)

    assert isinstance(events[-1], AnswerEvent)
    assert events[-1].answer.status is AnswerStatus.FAILED


async def test_closing_the_stream_cancels_the_run(layer):
    generator = BlockingGenerator()
    executor = ScriptedExecutor(result())
    events = use_case(layer, generator, executor).stream("quantas UCs?", "s1")

    async with asyncio.timeout(1):
        first = await anext(events)
        await events.aclose()

    assert first.stage is Stage.UNDERSTANDING
    assert generator.cancelled is True
    assert executor.queries == []


async def test_stage_events_carry_the_tokens_spent_so_far_outside_the_serialized_event(layer):
    events = await collect(
        use_case(layer, ScriptedGenerator(generation()), ScriptedExecutor(result()))
    )

    assert events[0].input_tokens == 0
    assert events[1].input_tokens == generation().input_tokens
    assert "input_tokens" not in events[1].model_dump_json()


class HangingWriter:
    async def write(self, question, draft, result, feedback=None):
        await asyncio.Event().wait()


async def test_a_question_past_the_deadline_fails_with_its_own_message(layer):
    agent = use_case(layer, BlockingGenerator(), answer_deadline_seconds=0.01)

    async with asyncio.timeout(1):
        answer = await agent.ask("quantas UCs?", "s1")

    assert answer.status is AnswerStatus.FAILED
    assert answer.refused_reason == DEADLINE_FAILED


async def test_a_slow_narration_keeps_the_result_with_the_deterministic_text(layer):
    agent = use_case(
        layer,
        ScriptedGenerator(generation()),
        ScriptedExecutor(result()),
        HangingWriter(),
        answer_deadline_seconds=1.05,
    )

    async with asyncio.timeout(1):
        answer = await agent.ask("quantas UCs?", "s1")

    assert answer.status is AnswerStatus.ANSWERED
    assert answer.rows == ({"total": 3},)


async def test_the_reason_says_when_a_refused_number_is_only_in_the_question(layer):
    writer = FixedWriter(texts=("Há 3 UCs acima de 300 kWh.", "Há 3 UCs."))

    await use_case(layer, ScriptedGenerator(generation()), writer=writer).ask(
        "Quantas UCs estão acima de 300 kWh?", "s1"
    )

    assert "300" in writer.feedbacks[1] and "só na pergunta" in writer.feedbacks[1]


class SlowFirstWriter:
    def __init__(self, delay, texts):
        self._delay = delay
        self._texts = texts
        self.calls = 0

    async def write(self, question, draft, result, feedback=None):
        self.calls += 1
        if self.calls == 1:
            await asyncio.sleep(self._delay)
        return Narration(text=self._texts[self.calls - 1])


async def test_no_second_narration_starts_without_time_to_finish_it(layer):
    writer = SlowFirstWriter(0.3, ("Há 999 UCs.", "Há 3 UCs."))
    agent = use_case(
        layer,
        ScriptedGenerator(generation()),
        writer=writer,
        answer_deadline_seconds=1.5,
        narration_min_seconds=0.4,
    )

    answer = await agent.ask("quantas?", "s1")

    assert writer.calls == 1
    assert answer.answer.startswith("A consulta devolveu")


async def test_a_second_narration_runs_when_there_is_time_for_it(layer):
    writer = SlowFirstWriter(0.01, ("Há 999 UCs.", "Há 3 UCs."))
    agent = use_case(
        layer,
        ScriptedGenerator(generation()),
        writer=writer,
        answer_deadline_seconds=2.0,
        narration_min_seconds=0.4,
    )

    answer = await agent.ask("quantas?", "s1")

    assert answer.answer == "Há 3 UCs."


async def test_an_answer_carries_the_unit_of_each_column_it_knows(layer):
    query_result = table(
        ("receita_2024", "variacao_percentual", "municipio"),
        (Decimal("16778217.14"), Decimal("0.89"), "Recife"),
    )

    answer = await use_case(
        layer, ScriptedGenerator(generation()), ScriptedExecutor(query_result)
    ).ask("quantas?", "s1")

    assert answer.column_units == {"receita_2024": "R$", "variacao_percentual": "%"}
    assert answer.column_labels == {
        "receita_2024": "receita 2024",
        "variacao_percentual": "variação percentual",
        "municipio": "município",
    }


async def test_a_month_inside_the_sql_range_is_a_supported_number(layer):
    writer = FixedWriter(text="De 2025-01 a 2025-03, passando por 2025-02, o DEC foi de 0,34 h.")
    range_sql = (
        "SELECT sum(horas_interrompidas) / NULLIF(sum(n_uc) / 3.0, 0) AS dec "
        "FROM sem_kpis_segmento_mensal WHERE competencia BETWEEN '2025-01' AND '2025-03'"
    )

    answer = await use_case(
        layer,
        ScriptedGenerator(generation(sql=range_sql)),
        executor=ScriptedExecutor(table(("dec",), (Decimal("0.3392"),))),
        writer=writer,
    ).ask("Qual foi o DEC no primeiro trimestre de 2025?", "s1")

    assert answer.answer == "De 2025-01 a 2025-03, passando por 2025-02, o DEC foi de 0,34 h."


async def test_a_number_of_the_question_used_as_a_filter_in_the_sql_is_supported(layer):
    writer = FixedWriter(text="Há 3 UCs acima de 300 kWh.")
    filter_sql = "SELECT count(*) AS total FROM sem_faturamento_mensal WHERE kwh_faturado > 300"

    answer = await use_case(
        layer,
        ScriptedGenerator(generation(sql=filter_sql)),
        executor=ScriptedExecutor(table(("total",), (3,))),
        writer=writer,
    ).ask("Quantas UCs estão acima de 300 kWh?", "s1")

    assert answer.answer == "Há 3 UCs acima de 300 kWh."


TWO_YEARS_SQL = (
    "SELECT count(*) AS total FROM sem_faturamento_mensal "
    "WHERE competencia LIKE '2023-%' OR competencia LIKE '2024-%'"
)


async def test_a_year_nobody_asked_for_becomes_a_question_about_the_period(layer):
    executor = ScriptedExecutor(result())

    answer = await use_case(layer, ScriptedGenerator(generation(sql=TWO_YEARS_SQL)), executor).ask(
        "Quantas UCs com painel solar em Olinda tiveram queda de consumo acima de 30%?", "s1"
    )

    assert answer.status is AnswerStatus.CLARIFY
    assert answer.clarification == PERIOD_NOT_GIVEN
    assert executor.queries == []


WHOLE_SERIES_SQL = "SELECT sum(receita_faturada) AS receita FROM sem_faturamento_mensal"


async def test_a_sum_over_the_whole_series_without_a_period_becomes_a_question_about_it(layer):
    executor = ScriptedExecutor(result())

    answer = await use_case(
        layer, ScriptedGenerator(generation(sql=WHOLE_SERIES_SQL)), executor
    ).ask("Qual foi a receita?", "s1")

    assert answer.status is AnswerStatus.CLARIFY
    assert answer.clarification == PERIOD_NOT_GIVEN
    assert executor.queries == []


async def test_a_sum_over_the_whole_series_is_answered_when_the_question_asks_for_it(layer):
    answer = await use_case(layer, ScriptedGenerator(generation(sql=WHOLE_SERIES_SQL))).ask(
        "Qual foi a receita em todo o histórico?", "s1"
    )

    assert answer.status is AnswerStatus.ANSWERED


async def test_a_sum_over_the_whole_series_keeps_the_period_of_the_conversation(layer):
    history = FakeHistory(
        (
            ConversationTurn(
                question="Qual foi a receita de junho de 2024?",
                sql="SELECT sum(receita_faturada) FROM sem_faturamento_mensal "
                "WHERE competencia = '2024-06'",
                status=AnswerStatus.ANSWERED,
            ),
        )
    )

    answer = await use_case(
        layer,
        ScriptedGenerator(generation(sql=WHOLE_SERIES_SQL)),
        history=history,
        history_turns=3,
    ).ask("E a receita?", "s1")

    assert answer.status is AnswerStatus.ANSWERED


async def test_years_written_in_words_are_not_invented(layer):
    answer = await use_case(layer, ScriptedGenerator(generation(sql=TWO_YEARS_SQL))).ask(
        "Quantas UCs faturaram de dois mil e vinte e três pra dois mil e vinte e quatro?", "s1"
    )

    assert answer.status is AnswerStatus.ANSWERED


async def test_a_year_next_to_one_the_question_names_is_not_invented(layer):
    answer = await use_case(layer, ScriptedGenerator(generation(sql=TWO_YEARS_SQL))).ask(
        "Quantas UCs faturaram em 2024 em relação ao ano anterior?", "s1"
    )

    assert answer.status is AnswerStatus.ANSWERED


async def test_a_year_from_the_conversation_history_is_not_invented(layer):
    history = FakeHistory(
        (
            ConversationTurn(
                question="Qual foi a receita de junho de 2024?",
                sql=COUNT_SQL,
                status=AnswerStatus.ANSWERED,
            ),
        )
    )

    answer = await use_case(
        layer,
        ScriptedGenerator(generation(sql=TWO_YEARS_SQL)),
        history=history,
        history_turns=3,
    ).ask("E o número de UCs?", "s1")

    assert answer.status is AnswerStatus.ANSWERED


async def test_a_count_written_with_a_unit_is_refused_with_the_reason(layer):
    writer = FixedWriter(texts=("O total foi de 208 kWh.", "Foram 208 UCs."))
    count = ScriptedExecutor(table(("total",), (208,)))

    answer = await use_case(layer, ScriptedGenerator(generation()), count, writer).ask(
        "Quantas UCs tiveram queda?", "s1"
    )

    assert answer.answer == "Foram 208 UCs."
    assert "208" in writer.feedbacks[1] and "kWh" in writer.feedbacks[1]


async def test_a_value_written_with_another_known_unit_is_refused(layer):
    writer = FixedWriter(text="A receita foi de 1.200 kWh.")
    money = ScriptedExecutor(table(("receita_faturada",), (Decimal("1200"),)))

    answer = await use_case(layer, ScriptedGenerator(generation()), money, writer).ask(
        "receita?", "s1"
    )

    assert answer.answer.startswith("A consulta devolveu")


async def test_a_percentage_of_a_column_without_unit_is_kept(layer):
    writer = FixedWriter(text="A taxa foi de 5,6%.")
    rate_result = ScriptedExecutor(table(("taxa",), (Decimal("5.6"),)))

    answer = await use_case(layer, ScriptedGenerator(generation()), rate_result, writer).ask(
        "taxa?", "s1"
    )

    assert answer.answer == "A taxa foi de 5,6%."


async def test_a_column_named_with_a_months_suffix_reaches_the_answer_as_a_duration(layer):
    assumptions = ("Usei a média de consumo_medio_kwh_12m das UCs residenciais.",)

    answer = await use_case(layer, ScriptedGenerator(generation(assumptions=assumptions))).ask(
        "Qual é o consumo médio das UCs residenciais nos últimos 12 meses?", "s1"
    )

    assert answer.assumptions == (
        "Usei a média de consumo médio mensal dos últimos 12 meses das UCs residenciais.",
    )


LAST_MONTHS_SQL = (
    "SELECT sum(receita_faturada) AS receita FROM sem_kpis_mensais WHERE competencia >= '2025-07'"
)


@pytest.mark.parametrize(
    "question",
    [
        "Qual foi a receita nos últimos 12 meses?",
        "Qual foi a receita no primeiro ano da base?",
    ],
)
async def test_a_period_relative_to_the_base_does_not_need_its_years_in_the_question(
    layer, question
):
    answer = await use_case(layer, ScriptedGenerator(generation(sql=LAST_MONTHS_SQL))).ask(
        question, "s1"
    )

    assert answer.status is AnswerStatus.ANSWERED


async def test_a_calendar_last_year_without_years_still_asks_for_the_period(layer):
    answer = await use_case(layer, ScriptedGenerator(generation(sql=LAST_MONTHS_SQL))).ask(
        "Qual foi a receita no último ano?", "s1"
    )

    assert answer.clarification == PERIOD_NOT_GIVEN


CLARIFY_TURN = turn("queda acima de 30%", sql=None, status="clarify")


async def test_an_answer_to_a_clarification_completes_the_original_question(layer, caplog):
    generator = ScriptedGenerator(generation())
    history = FakeHistory((CLARIFY_TURN,))

    with caplog.at_level(logging.INFO, logger="venergy_agent.ask"):
        await use_case(layer, generator, history=history, history_turns=3).ask(
            "entre 2024 e 2025", "s1"
        )

    assert generator.questions == ["queda acima de 30% Esclarecimento: entre 2024 e 2025"]
    assert "pergunta_completada" in caplog.text
    assert "queda acima de 30%" not in caplog.text


async def test_a_new_complete_question_after_a_clarification_is_not_completed(layer):
    generator = ScriptedGenerator(generation())
    history = FakeHistory((CLARIFY_TURN,))

    await use_case(layer, generator, history=history, history_turns=3).ask(
        "Quantas UCs existem na base?", "s1"
    )

    assert generator.questions == ["Quantas UCs existem na base?"]


async def test_a_reply_after_an_answer_is_not_treated_as_a_clarification(layer):
    generator = ScriptedGenerator(generation())
    history = FakeHistory((turn("quantas UCs?"),))

    await use_case(layer, generator, history=history, history_turns=3).ask("percentual", "s1")

    assert generator.questions == ["percentual"]


def test_fallback_text_shows_hours_and_percent_with_at_most_two_decimals():
    from venergy_agent.application.ask import _with_unit

    assert _with_unit(0.0256, "h") == "0,03 h"
    assert _with_unit(3.456, "%") == "3,46%"
    assert _with_unit(1234.5, "kWh") == "1.235 kWh"
    assert _with_unit(12.4, "contagem") == "12"


async def test_a_new_request_after_a_clarification_reaches_the_generator_unchanged(layer):
    generator = ScriptedGenerator(generation())
    history = FakeHistory((CLARIFY_TURN,))

    await use_case(layer, generator, history=history, history_turns=3).ask(
        "Mostre a receita de junho de 2026", "s1"
    )

    assert generator.questions == ["Mostre a receita de junho de 2026"]


async def test_a_percentage_threshold_is_not_invented_when_the_sql_uses_its_complement(layer):
    sql = "SELECT count(*) AS total FROM sem_faturamento_mensal WHERE kwh_faturado < 0.7"
    writer = FixedWriter(text="Há 3 UCs com queda acima de 30%.")

    answer = await use_case(
        layer,
        ScriptedGenerator(generation(sql=sql)),
        executor=ScriptedExecutor(table(("total",), (3,))),
        writer=writer,
    ).ask("Quantas UCs tiveram queda acima de 30%?", "s1")

    assert answer.answer == "Há 3 UCs com queda acima de 30%."


async def test_a_period_clarification_offers_the_years_the_sql_assumed(layer):
    answer = await use_case(
        layer,
        ScriptedGenerator(generation(sql=TWO_YEARS_SQL)),
        ScriptedExecutor(result()),
    ).ask("Quantas UCs com painel solar em Olinda tiveram queda de consumo acima de 30%?", "s1")

    assert answer.status is AnswerStatus.CLARIFY
    assert answer.clarification_options == ("em 2023", "em 2024", "nos últimos 12 meses")


async def test_a_period_clarification_from_the_model_offers_the_last_twelve_months(layer):
    draft = generation(
        status="clarify", sql=None, clarification="De qual período você quer a receita?"
    )

    answer = await use_case(layer, ScriptedGenerator(draft)).ask("Qual foi a receita?", "s1")

    assert answer.clarification_options == ("nos últimos 12 meses",)


async def test_a_clarification_from_the_model_about_something_else_has_no_options(layer):
    draft = generation(
        status="clarify", sql=None, clarification="O que você considera os piores bairros?"
    )

    answer = await use_case(layer, ScriptedGenerator(draft)).ask("Quais os piores bairros?", "s1")

    assert answer.clarification_options == ()


async def test_a_period_clarification_has_no_options_when_the_question_names_a_year(layer):
    draft = generation(
        status="clarify", sql=None, clarification="Qual mês de 2024 você quer consultar?"
    )

    answer = await use_case(layer, ScriptedGenerator(draft)).ask(
        "Qual foi a receita em 2024?", "s1"
    )

    assert answer.clarification_options == ()


async def test_a_period_clarification_has_no_options_when_the_conversation_has_a_period(layer):
    history = FakeHistory(
        (
            ConversationTurn(
                question="Qual a receita do primeiro ano da base?",
                sql="SELECT sum(receita_faturada) FROM sem_kpis_mensais "
                "WHERE competencia BETWEEN '2022-07' AND '2023-06'",
                status=AnswerStatus.ANSWERED,
            ),
        )
    )
    draft = generation(status="clarify", sql=None, clarification="Qual mês você quer ver?")

    answer = await use_case(layer, ScriptedGenerator(draft), history=history, history_turns=3).ask(
        "E por classe?", "s1"
    )

    assert answer.clarification_options == ()


async def test_a_base_window_does_not_cross_a_sentence(layer):
    executor = ScriptedExecutor(result())

    answer = await use_case(layer, ScriptedGenerator(generation(sql=TWO_YEARS_SQL)), executor).ask(
        "Qual a receita do último trimestre? Quero os dados de Recife.", "s1"
    )

    assert answer.status is AnswerStatus.CLARIFY
    assert executor.queries == []


async def test_energy_written_as_an_integer_matches_a_value_with_decimals(layer):
    writer = FixedWriter(text="A energia faturada foi de 496.099 kWh.")
    energy = ScriptedExecutor(table(("kwh_faturado",), (Decimal("496099.37"),)))

    answer = await use_case(layer, ScriptedGenerator(generation()), energy, writer).ask(
        "energia?", "s1"
    )

    assert answer.answer == "A energia faturada foi de 496.099 kWh."


async def test_an_integer_still_does_not_round_a_value_without_an_integer_unit(layer):
    writer = FixedWriter(text="A tarifa foi de 2.")
    tariff = ScriptedExecutor(table(("tarifa_media",), (Decimal("1.71"),)))

    answer = await use_case(layer, ScriptedGenerator(generation()), tariff, writer).ask(
        "tarifa?", "s1"
    )

    assert answer.answer.startswith("A consulta devolveu")


async def test_a_year_of_the_question_used_in_a_date_of_the_sql_can_be_cited(layer):
    writer = FixedWriter(text="Em 2025, 3 UCs conectaram painel solar.")
    date_sql = (
        "SELECT count(*) AS total FROM sem_uc "
        "WHERE data_conexao_gd BETWEEN '2025-01-01' AND '2025-12-31'"
    )

    answer = await use_case(layer, ScriptedGenerator(generation(sql=date_sql)), writer=writer).ask(
        "Quantas UCs conectaram painel solar em 2025?", "s1"
    )

    assert answer.answer == "Em 2025, 3 UCs conectaram painel solar."


async def test_a_duration_in_the_name_of_a_column_the_sql_reads_can_be_cited(layer):
    writer = FixedWriter(text="Nos últimos 12 meses, o consumo médio foi de 3.")
    column_sql = "SELECT avg(consumo_medio_kwh_12m) AS total FROM sem_uc"

    answer = await use_case(
        layer, ScriptedGenerator(generation(sql=column_sql)), writer=writer
    ).ask("qual o consumo médio das casas residenciais?", "s1")

    assert answer.answer == "Nos últimos 12 meses, o consumo médio foi de 3."


async def test_a_calendar_period_without_a_year_is_asked_before_calling_the_model(layer):
    generator = ScriptedGenerator(generation())

    answer = await use_case(layer, generator).ask(
        "Qual bairro mais perdeu volume residencial no último ano?", "s1"
    )

    assert answer.status is AnswerStatus.CLARIFY
    assert answer.clarification == PERIOD_NOT_GIVEN
    assert generator.feedbacks == []


BASE_WINDOW_SQL = (
    "WITH meses AS (SELECT competencia, row_number() OVER (ORDER BY competencia) AS ordem_inicio "
    "FROM sem_kpis_mensais) SELECT count(*) AS total FROM meses WHERE ordem_inicio <= 12"
)


async def test_a_window_relative_to_the_base_nobody_asked_for_asks_the_period(layer):
    executor = ScriptedExecutor(result())

    answer = await use_case(
        layer, ScriptedGenerator(generation(sql=BASE_WINDOW_SQL)), executor
    ).ask(
        "Quantas unidades com painel solar em Olinda tiveram queda de consumo acima de 30%?", "s1"
    )

    assert answer.clarification == PERIOD_NOT_GIVEN
    assert executor.queries == []


async def test_a_window_relative_to_the_base_the_question_asked_for_is_answered(layer):
    answer = await use_case(layer, ScriptedGenerator(generation(sql=BASE_WINDOW_SQL))).ask(
        "Quantas UCs faturaram nos últimos 12 meses?", "s1"
    )

    assert answer.status is AnswerStatus.ANSWERED


@pytest.mark.parametrize(
    "question",
    [
        "A energia caiu nos últimos doze meses comparando com o período inicial da série?",
        "Comparando o arranque da base com os últimos doze meses, quanto variou a receita?",
        "Quanto a receita mudou do começo do histórico até o ano mais recente dos dados?",
    ],
)
async def test_a_window_relative_to_the_base_asked_in_other_words_is_answered(layer, question):
    answer = await use_case(layer, ScriptedGenerator(generation(sql=BASE_WINDOW_SQL))).ask(
        question, "s1"
    )

    assert answer.status is AnswerStatus.ANSWERED


async def test_a_number_of_an_assumption_that_the_sql_uses_can_be_cited(layer):
    writer = FixedWriter(text="O DEC usa a média mensal de UCs, dividida por 3, e foi de 8.")
    eight = ScriptedExecutor(table(("total",), (8,)))
    draft = generation(
        sql="SELECT sum(n_uc) / 3.0 AS total FROM sem_kpis_segmento_mensal",
        assumptions=("A média mensal de UCs é a soma de n_uc dividida por 3.0.",),
    )

    answer = await use_case(layer, ScriptedGenerator(draft), eight, writer).ask(
        "Qual foi o DEC de Olinda no primeiro trimestre de 2025?", "s1"
    )

    assert answer.answer == "O DEC usa a média mensal de UCs, dividida por 3, e foi de 8."
    assert answer.assumptions == ("A média mensal de UCs é a soma de UCs dividida por 3.",)


async def test_a_forbidden_calculation_goes_back_to_the_model_as_a_correctable_error(layer):
    wrong = generation(sql="SELECT avg(satisfacao_media) AS total FROM sem_kpis_mensais")
    right = generation(sql=COUNT_SQL)
    generator = ScriptedGenerator(wrong, right)
    executor = ScriptedExecutor(result())

    answer = await use_case(layer, generator, executor).ask("satisfação de 2025?", "s1")

    assert answer.status is AnswerStatus.ANSWERED
    assert "soma_notas" in generator.feedbacks[1].message
    assert len(executor.queries) == 1


async def test_a_filter_value_that_is_not_in_the_column_goes_back_to_the_model(layer):
    known = layer.model_copy(update={"categorical_values": {"municipio": ("Olinda", "Recife")}})
    wrong = generation(
        sql="SELECT count(*) AS total FROM sem_uc WHERE municipio = 'Região Metropolitana'"
    )
    right = generation(sql=COUNT_SQL)
    generator = ScriptedGenerator(wrong, right)
    executor = ScriptedExecutor(result())

    answer = await use_case(known, generator, executor).ask("Quantas UCs na região?", "s1")

    assert answer.status is AnswerStatus.ANSWERED
    assert "'Região Metropolitana' não existe em municipio" in generator.feedbacks[1].message
    assert len(executor.queries) == 1
