import json
import logging
import re
import time
from collections.abc import Mapping
from decimal import Decimal
from uuid import uuid4

from pydantic import ValidationError

from venergy_agent.application.ports import (
    AnswerWriter,
    QueryExecutor,
    SqlGenerator,
    SqlValidator,
)
from venergy_agent.domain.answer import AgentAnswer, AnswerStatus, Confidence
from venergy_agent.domain.errors import ErrorKind, QueryExecutionError, SqlRejected
from venergy_agent.domain.numbers import unsupported_numbers
from venergy_agent.domain.question import Question
from venergy_agent.domain.semantic import SemanticLayer
from venergy_agent.domain.sql import (
    AttemptFeedback,
    DraftStatus,
    Generation,
    QueryResult,
    SqlDraft,
    ValidatedQuery,
)

logger = logging.getLogger("venergy_agent.ask")

TECHNICAL_NAME = re.compile(r"\b[a-zA-Z]+_\w+")

EMPTY_QUESTION = "A pergunta está vazia. Escreva o que você quer saber sobre a distribuidora."
TOO_LONG_QUESTION = (
    "A pergunta passou do limite de {limit} caracteres. Escreva uma pergunta mais curta."
)
UNKNOWN_REASON = (
    "Não tenho essa informação nas tabelas que consulto, então não vou inventar uma resposta."
)
REFUSED_REASON = (
    "Esse pedido está fora do que o agente faz: ele só responde perguntas sobre consumo, "
    "faturamento, interrupções e atendimento da distribuidora, consultando os dados."
)
MODEL_FAILED = "Não consegui consultar o modelo de linguagem agora. Tente de novo em instantes."
INTERNAL_FAILED = "Algo deu errado do nosso lado. Tente de novo em instantes."
ATTEMPTS_FAILED = "Não consegui montar uma consulta válida depois de {attempts} tentativas."
DATABASE_FAILED = "Não consegui consultar o banco agora. Tente de novo em instantes."
CLARIFY_PREFIX = "Preciso de um esclarecimento antes de consultar: "
UNITS_WITHOUT_SUFFIX = frozenset({"contagem", "nota"})
GENERIC_CLARIFICATION = (
    "Pode dizer o período e o recorte (município, bairro ou classe) que você quer consultar?"
)
COMPETENCIA = re.compile(r"\d{4}-\d{2}")
MONTH_NAMES = (
    "janeiro",
    "fevereiro",
    "março",
    "abril",
    "maio",
    "junho",
    "julho",
    "agosto",
    "setembro",
    "outubro",
    "novembro",
    "dezembro",
)
FALLBACK_MAX_ROWS = 5
FALLBACK_MAX_COLUMNS = 4
MISSING_VALUE = "sem valor"
MAX_DECIMAL_PLACES = 6
TEXT_VALUE_MAX_CHARS = 120
EMPTY_RESULT = (
    "Nenhum registro atende à consulta. O agente não distingue zero de dado ausente, "
    "então confira os filtros."
)


class AskUseCase:
    def __init__(
        self,
        *,
        layer: SemanticLayer,
        generator: SqlGenerator,
        validator: SqlValidator,
        executor: QueryExecutor,
        answer_writer: AnswerWriter | None,
        max_question_chars: int,
        max_correction_attempts: int,
        answer_sample_rows: int,
        prompt_version: str,
        configured_model: str,
    ) -> None:
        self._layer = layer
        self._generator = generator
        self._validator = validator
        self._executor = executor
        self._answer_writer = answer_writer
        self._max_question_chars = max_question_chars
        self._max_attempts = max_correction_attempts
        self._sample_rows = answer_sample_rows
        self._prompt_version = prompt_version
        self._configured_model = configured_model

    async def ask(self, question: str, session_id: str) -> AgentAnswer:
        started = time.perf_counter()
        request_id = uuid4().hex
        try:
            return await self._answer(question, session_id, request_id, started)
        except Exception as error:
            self._log(
                request_id, session_id, step="ask", status="internal_error", error=repr(error)
            )
            return self._unanswered(
                AnswerStatus.FAILED,
                INTERNAL_FAILED,
                request_id=request_id,
                session_id=session_id,
                started=started,
            )

    async def _answer(
        self, text: str, session_id: str, request_id: str, started: float
    ) -> AgentAnswer:
        if not text.strip():
            return self._unanswered(
                AnswerStatus.REFUSED, EMPTY_QUESTION, request_id, session_id, started
            )
        try:
            question = Question(text=text, session_id=session_id, request_id=request_id)
        except ValidationError:
            return self._unanswered(
                AnswerStatus.REFUSED, EMPTY_QUESTION, request_id, session_id, started
            )
        self._log(request_id, session_id, step="pergunta", status="recebida", chars=len(text))
        if len(question.text) > self._max_question_chars:
            return self._unanswered(
                AnswerStatus.REFUSED,
                TOO_LONG_QUESTION.format(limit=self._max_question_chars),
                request_id,
                session_id,
                started,
            )

        feedback: AttemptFeedback | None = None
        last_sql: str | None = None
        last_model: str | None = None
        for attempt in range(1, self._max_attempts + 1):
            generation = await self._generate(question, feedback, attempt)
            if generation is None:
                return self._unanswered(
                    AnswerStatus.FAILED,
                    MODEL_FAILED,
                    request_id,
                    session_id,
                    started,
                    sql=last_sql,
                    model=last_model,
                )
            draft = generation.draft
            last_sql = draft.sql or last_sql
            last_model = generation.model

            if draft.status is DraftStatus.UNKNOWN:
                return self._unanswered(
                    AnswerStatus.UNKNOWN,
                    UNKNOWN_REASON,
                    request_id,
                    session_id,
                    started,
                    model=generation.model,
                )
            if draft.status is DraftStatus.REFUSE:
                return self._unanswered(
                    AnswerStatus.REFUSED,
                    REFUSED_REASON,
                    request_id,
                    session_id,
                    started,
                    model=generation.model,
                )
            if draft.status is DraftStatus.CLARIFY:
                clarification = draft.clarification_question or ""
                if TECHNICAL_NAME.search(clarification):
                    self._log(
                        request_id,
                        session_id,
                        step="resposta",
                        status="nome_tecnico_no_esclarecimento",
                    )
                    clarification = GENERIC_CLARIFICATION
                self._log(request_id, session_id, step="resposta", status="clarify")
                return self._clarify(clarification, request_id, started, model=generation.model)

            began = time.perf_counter()
            try:
                validated = self._validator.validate(draft.sql, self._layer.allowed_views)
            except SqlRejected as rejection:
                self._log(
                    request_id,
                    session_id,
                    step="validacao",
                    status="rejeitado",
                    attempt=attempt,
                    sql=draft.sql,
                    reason=rejection.reason,
                    latency_ms=_elapsed_ms(began),
                )
                feedback = AttemptFeedback(
                    previous_sql=draft.sql, error_kind=ErrorKind.REJECTED, message=rejection.reason
                )
                continue
            self._log(
                request_id,
                session_id,
                step="validacao",
                status="aceito",
                attempt=attempt,
                sql=validated.sql,
                latency_ms=_elapsed_ms(began),
            )
            began = time.perf_counter()

            try:
                result = await self._executor.execute(validated)
            except QueryExecutionError as error:
                self._log(
                    request_id,
                    session_id,
                    step="execucao",
                    status="erro_corrigivel",
                    attempt=attempt,
                    sql=validated.sql,
                    error_kind=error.kind.value,
                    latency_ms=_elapsed_ms(began),
                )
                feedback = AttemptFeedback(
                    previous_sql=draft.sql, error_kind=error.kind, message=error.message
                )
                continue
            except Exception as error:
                self._log(
                    request_id,
                    session_id,
                    step="execucao",
                    status="erro_nao_classificado",
                    attempt=attempt,
                    sql=validated.sql,
                    error=type(error).__name__,
                    latency_ms=_elapsed_ms(began),
                )
                return self._unanswered(
                    AnswerStatus.FAILED,
                    DATABASE_FAILED,
                    request_id,
                    session_id,
                    started,
                    sql=validated.sql,
                    model=generation.model,
                )

            self._log(
                request_id,
                session_id,
                step="execucao",
                status="ok",
                attempt=attempt,
                sql=validated.sql,
                row_count=result.row_count,
                truncated=result.truncated,
                latency_ms=_elapsed_ms(began),
            )
            return await self._answered(
                question, draft, validated, result, generation, attempt, started
            )

        return self._unanswered(
            AnswerStatus.FAILED,
            ATTEMPTS_FAILED.format(attempts=self._max_attempts),
            request_id,
            session_id,
            started,
            sql=last_sql,
            model=last_model,
        )

    async def _generate(
        self, question: Question, feedback: AttemptFeedback | None, attempt: int
    ) -> Generation | None:
        began = time.perf_counter()
        try:
            generation = await self._generator.generate(question, self._layer, feedback)
        except Exception as error:
            self._log(
                question.request_id,
                question.session_id,
                step="geracao",
                status="erro_do_modelo",
                attempt=attempt,
                error=type(error).__name__,
            )
            return None
        self._log(
            question.request_id,
            question.session_id,
            step="geracao",
            status=generation.draft.status.value,
            attempt=attempt,
            sql=generation.draft.sql,
            model=generation.model,
            input_tokens=generation.input_tokens,
            output_tokens=generation.output_tokens,
            prompt_version=self._prompt_version,
            latency_ms=_elapsed_ms(began),
        )
        return generation

    async def _answered(
        self,
        question: Question,
        draft: SqlDraft,
        validated: ValidatedQuery,
        result: QueryResult,
        generation: Generation,
        attempt: int,
        started: float,
    ) -> AgentAnswer:
        sample = result.rows[: self._sample_rows]
        visible = result.model_copy(update={"rows": sample})
        text = self._deterministic_text(
            result, draft, validated, _period(result) or _endpoints(validated.periods)
        )
        text = await self._narrate(
            question, draft, visible, text, _period(visible), validated.periods
        )

        return AgentAnswer(
            answer=text,
            status=AnswerStatus.ANSWERED,
            sql=validated.sql,
            rows=sample,
            row_count=result.row_count,
            truncated=result.truncated,
            confidence=self._confidence(result, draft, attempt),
            sources=tuple(sorted(validated.views)),
            assumptions=draft.assumptions,
            clarification=None,
            refused_reason=None,
            request_id=question.request_id,
            model=generation.model,
            prompt_version=self._prompt_version,
            latency_ms=_elapsed_ms(started),
        )

    async def _narrate(
        self,
        question: Question,
        draft: SqlDraft,
        visible: QueryResult,
        fallback: str,
        period: tuple[str, str] | None,
        filtered_periods: tuple[str, ...],
    ) -> str:
        if self._answer_writer is None:
            return fallback
        try:
            narrative = await self._answer_writer.write(question, draft, visible)
        except Exception as error:
            self._log(
                question.request_id,
                question.session_id,
                step="resposta",
                status="narrativa_falhou",
                error=type(error).__name__,
            )
            return fallback

        if TECHNICAL_NAME.search(narrative):
            self._log(
                question.request_id,
                question.session_id,
                step="resposta",
                status="nome_tecnico_na_resposta",
            )
            return fallback

        required = period if period is not None else _endpoints(filtered_periods)
        if required is not None and not all(_mentions(narrative, value) for value in required):
            self._log(
                question.request_id,
                question.session_id,
                step="resposta",
                status="periodo_ausente_na_resposta",
            )
            return fallback

        values = [
            visible.row_count,
            *filtered_periods,
            *(value for row in visible.rows for value in row.values()),
        ]
        unsupported = unsupported_numbers(narrative, values)
        if unsupported:
            self._log(
                question.request_id,
                question.session_id,
                step="resposta",
                status="verificacao_numerica_falhou",
                unsupported=list(unsupported),
            )
            return fallback
        self._log(question.request_id, question.session_id, step="resposta", status="narrativa_ok")
        return narrative

    def _deterministic_text(
        self,
        result: QueryResult,
        draft: SqlDraft,
        validated: ValidatedQuery,
        period: tuple[str, str] | None,
    ) -> str:
        if result.row_count == 0:
            text = EMPTY_RESULT
        else:
            text = f"A consulta devolveu {result.row_count} linha(s)."
            if period is not None:
                text += _period_sentence(period)
            if (
                len(result.rows) <= FALLBACK_MAX_ROWS
                and len(result.columns) <= FALLBACK_MAX_COLUMNS
            ):
                text += (
                    " Resultado: "
                    + "; ".join(
                        _row_text(result.columns, row, self._layer.column_units)
                        for row in result.rows
                    )
                    + "."
                )
        if result.truncated:
            text += (
                f" O resultado foi limitado a {validated.applied_limit} linhas, "
                "então o total pode ser maior."
            )
        assumptions = [item for item in draft.assumptions if not TECHNICAL_NAME.search(item)]
        if assumptions:
            text += " Suposições: " + "; ".join(assumptions) + "."
        return text

    def _confidence(self, result: QueryResult, draft: SqlDraft, attempt: int) -> Confidence:
        if result.row_count == 0 or result.truncated:
            return Confidence.LOW
        if draft.assumptions or attempt > 1:
            return Confidence.MEDIUM
        return Confidence.HIGH

    def _clarify(
        self, clarification: str, request_id: str, started: float, *, model: str
    ) -> AgentAnswer:
        return AgentAnswer(
            answer=CLARIFY_PREFIX + clarification,
            status=AnswerStatus.CLARIFY,
            sql=None,
            rows=(),
            row_count=0,
            truncated=False,
            confidence=Confidence.UNKNOWN,
            sources=(),
            assumptions=(),
            clarification=clarification,
            refused_reason=None,
            request_id=request_id,
            model=model,
            prompt_version=self._prompt_version,
            latency_ms=_elapsed_ms(started),
        )

    def _unanswered(
        self,
        status: AnswerStatus,
        reason: str,
        request_id: str,
        session_id: str,
        started: float,
        *,
        sql: str | None = None,
        model: str | None = None,
    ) -> AgentAnswer:
        self._log(
            request_id,
            session_id,
            step="resposta",
            status=status.value,
            reason=reason,
            sql=sql,
        )
        return AgentAnswer(
            answer=reason,
            status=status,
            sql=sql,
            rows=(),
            row_count=0,
            truncated=False,
            confidence=Confidence.UNKNOWN,
            sources=(),
            assumptions=(),
            clarification=None,
            refused_reason=reason,
            request_id=request_id,
            model=model or self._configured_model,
            prompt_version=self._prompt_version,
            latency_ms=_elapsed_ms(started),
        )

    def _log(
        self, request_id: str, session_id: str, *, step: str, status: str, **fields: object
    ) -> None:
        line = {"request_id": request_id, "session_id": session_id, "step": step, "status": status}
        line.update(fields)
        logger.info(json.dumps(line, ensure_ascii=False, default=str))


def _row_text(columns: tuple[str, ...], row: dict[str, object], units: Mapping[str, str]) -> str:
    return ", ".join(
        f"{column.replace('_', ' ')} = {_with_unit(row.get(column), units.get(column))}"
        for column in columns
    )


def _with_unit(value: object, unit: str | None) -> str:
    text = _pt_br(value)
    if value is None or unit is None or unit in UNITS_WITHOUT_SUFFIX:
        return text
    return f"R$ {text}" if unit == "R$" else f"{text} {unit}"


def _pt_br(value: object) -> str:
    if value is None:
        return MISSING_VALUE
    if isinstance(value, bool):
        return "sim" if value else "não"
    if isinstance(value, int | float | Decimal):
        number = Decimal(str(value))
        exponent = number.as_tuple().exponent
        if isinstance(exponent, int) and exponent < -MAX_DECIMAL_PLACES:
            number = number.quantize(Decimal(1).scaleb(-MAX_DECIMAL_PLACES)).normalize()
        grouped = format(number, ",f")
        return grouped.replace(",", "_").replace(".", ",").replace("_", ".")
    return _shorten(str(value))


def _shorten(text: str) -> str:
    if len(text) <= TEXT_VALUE_MAX_CHARS:
        return text
    return text[: TEXT_VALUE_MAX_CHARS - 3] + "..."


def _elapsed_ms(since: float) -> int:
    return int((time.perf_counter() - since) * 1000)


def _period(result: QueryResult) -> tuple[str, str] | None:
    found = sorted(
        {
            str(row["competencia"])
            for row in result.rows
            if COMPETENCIA.fullmatch(str(row.get("competencia", "")))
        }
    )
    if not found:
        return None
    return found[0], found[-1]


def _endpoints(periods: tuple[str, ...]) -> tuple[str, str] | None:
    if not periods:
        return None
    return periods[0], periods[-1]


def _period_sentence(period: tuple[str, str]) -> str:
    first, last = period
    if first == last:
        return f" Período: {first}."
    return f" Período: {first} a {last}."


def _mentions(text: str, competencia: str) -> bool:
    year, month = competencia.split("-")
    name = MONTH_NAMES[int(month) - 1]
    lowered = text.lower()
    if any(form in lowered for form in (competencia, f"{month}/{year}", f"{name[:3]}/{year}")):
        return True
    return re.search(rf"\b{name}(?:/|\b[^.;]{{0,40}}?\b){year}\b", lowered) is not None
