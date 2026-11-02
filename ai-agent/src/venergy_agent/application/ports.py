from collections.abc import AsyncIterator, Mapping
from typing import Protocol

from venergy_agent.domain.answer import AgentAnswer, Insight
from venergy_agent.domain.conversation import ConversationTurn
from venergy_agent.domain.events import AgentEvent
from venergy_agent.domain.judge import JudgeRun
from venergy_agent.domain.narration import Narration
from venergy_agent.domain.question import Question
from venergy_agent.domain.semantic import SemanticLayer
from venergy_agent.domain.sql import (
    AttemptFeedback,
    Generation,
    QueryResult,
    SqlDraft,
    ValidatedQuery,
)


class TextToSqlAgent(Protocol):
    async def ask(self, question: str, session_id: str) -> AgentAnswer: ...

    def stream(self, question: str, session_id: str) -> AsyncIterator[AgentEvent]: ...


class ConversationHistory(Protocol):
    async def recent(self, session_id: str, limit: int) -> tuple[ConversationTurn, ...]: ...


class SessionUsage(Protocol):
    async def tokens_used(self, session_id: str) -> int: ...


class SemanticLayerSource(Protocol):
    async def load(self) -> SemanticLayer: ...


class SqlGenerator(Protocol):
    async def generate(
        self,
        question: Question,
        layer: SemanticLayer,
        feedback: AttemptFeedback | None,
        history: tuple[ConversationTurn, ...] = (),
    ) -> Generation: ...


class SqlValidator(Protocol):
    def validate(self, sql: str, allowed_views: frozenset[str]) -> ValidatedQuery: ...


class QueryExecutor(Protocol):
    async def execute(self, query: ValidatedQuery) -> QueryResult: ...


class AnswerWriter(Protocol):
    async def write(
        self, question: Question, draft: SqlDraft, result: QueryResult
    ) -> Narration: ...


class InsightWriter(Protocol):
    async def narrate(self, screen: str, metrics: Mapping[str, object]) -> Insight | None: ...


class AnswerJudge(Protocol):
    async def judge(self, question: str, answer: AgentAnswer) -> JudgeRun: ...
