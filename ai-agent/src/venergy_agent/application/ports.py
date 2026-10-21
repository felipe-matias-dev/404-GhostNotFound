from collections.abc import Mapping
from typing import Protocol

from venergy_agent.domain.answer import AgentAnswer, Insight
from venergy_agent.domain.question import Question
from venergy_agent.domain.semantic import SemanticLayer
from venergy_agent.domain.sql import AttemptFeedback, QueryResult, SqlDraft, ValidatedQuery


class TextToSqlAgent(Protocol):
    async def ask(self, question: str, session_id: str) -> AgentAnswer: ...


class SemanticLayerSource(Protocol):
    async def load(self) -> SemanticLayer: ...


class SqlGenerator(Protocol):
    async def generate(
        self, question: Question, layer: SemanticLayer, feedback: AttemptFeedback | None
    ) -> SqlDraft: ...


class SqlValidator(Protocol):
    def validate(self, sql: str, allowed_views: frozenset[str]) -> ValidatedQuery: ...


class QueryExecutor(Protocol):
    async def execute(self, query: ValidatedQuery) -> QueryResult: ...


class AnswerWriter(Protocol):
    async def write(self, question: Question, draft: SqlDraft, result: QueryResult) -> str: ...


class InsightWriter(Protocol):
    async def narrate(self, screen: str, metrics: Mapping[str, object]) -> Insight: ...
