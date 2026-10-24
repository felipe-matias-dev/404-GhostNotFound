from venergy_agent.application.ask import AskUseCase
from venergy_agent.domain.sql import DraftStatus, Generation, QueryResult, SqlDraft
from venergy_agent.infrastructure.sql_validator import SqlglotValidator

MODEL = "google-gla:gemini-test"
CONFIGURED = "google-gla:configured"
COUNT_SQL = "SELECT count(*) AS total FROM sem_uc"


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
