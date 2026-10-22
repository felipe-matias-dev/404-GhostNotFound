import json
import re

from venergy_agent.domain.question import Question
from venergy_agent.domain.semantic import (
    ColumnSpec,
    FewShotExample,
    GlossaryTerm,
    SemanticLayer,
    ViewSpec,
)
from venergy_agent.domain.sql import AttemptFeedback

PLACEHOLDER = re.compile(r"\{\{(\w+)\}\}")
REDACTED = "[redigido]"


def render_system_prompt(template: str, layer: SemanticLayer, nonce: str) -> str:
    _require(nonce)
    sections = [
        _section("Regras de negócio", [f"- {rule.text}" for rule in layer.rules]),
        _section("Glossário", [_glossary_line(term) for term in layer.glossary]),
        _section("Views disponíveis", [_view_block(view, nonce) for view in layer.views]),
        _section(
            "Relações",
            [
                f"- {r.left_view}.{r.left_column} = {r.right_view}.{r.right_column}"
                for r in layer.relations
            ],
        ),
        _section("Exemplos", [_example_block(example) for example in layer.examples]),
    ]
    return _fill(
        template,
        contexto="\n\n".join(section for section in sections if section),
        nonce=nonce,
    )


def render_user_prompt(
    question: Question,
    feedback: AttemptFeedback | None,
    correction_template: str,
    layer: SemanticLayer,
    nonce: str,
) -> str:
    _require(nonce)
    asked = _delimited("pergunta", question.text, nonce)
    if feedback is None:
        return asked
    involved = [
        view for view in layer.views if _mentions(feedback.previous_sql, view.name)
    ] or list(layer.views)
    correction = _fill(
        correction_template,
        sql_anterior=_delimited("dados", feedback.previous_sql, nonce),
        tipo_erro=feedback.error_kind.value,
        mensagem=_delimited("dados", feedback.message, nonce),
        colunas="\n".join(_columns_line(view) for view in involved),
    )
    return f"{correction}\n\n{asked}"


def _section(title: str, lines: list[str]) -> str:
    return f"## {title}\n\n" + "\n".join(lines) if lines else ""


def _glossary_line(term: GlossaryTerm) -> str:
    words = ", ".join(f'"{word}"' for word in (term.term, *term.synonyms))
    return f"- {words} → {term.maps_to}"


def _view_block(view: ViewSpec, nonce: str) -> str:
    lines = [f"### {view.name}", f"{view.description}. Grão: {view.grain}.", "Colunas:"]
    lines += [_column_line(column, nonce) for column in view.columns]
    if view.sample_rows:
        rows = "\n".join(
            json.dumps(row, ensure_ascii=False, default=str) for row in view.sample_rows
        )
        lines += ["Linhas de exemplo:", _delimited("dados", rows, nonce)]
    return "\n".join(lines)


def _column_line(column: ColumnSpec, nonce: str) -> str:
    unit = f", {column.unit}" if column.unit else ""
    line = f"- {column.name} ({column.type}{unit}): {column.description}"
    if column.allowed_values:
        values = _delimited("dados", ", ".join(column.allowed_values), nonce)
        line += f". Valores possíveis: {values}"
    return line


def _columns_line(view: ViewSpec) -> str:
    return f"- {view.name}: " + ", ".join(column.name for column in view.columns)


def _example_block(example: FewShotExample) -> str:
    sql = f"```sql\n{example.sql}\n```" if example.sql else "(sem SQL)"
    return f"Pergunta: {example.question}\nStatus esperado: {example.expected_status.value}\n{sql}"


def _delimited(tag: str, text: str, nonce: str) -> str:
    return f"<{tag}-{nonce}>\n{_redact(text, nonce)}\n</{tag}-{nonce}>"


def _require(nonce: str) -> None:
    if not nonce.strip():
        raise ValueError("nonce must not be blank")


def _redact(text: str, nonce: str) -> str:
    return text.replace(nonce, REDACTED)


def _mentions(sql: str, name: str) -> bool:
    return re.search(rf"\b{re.escape(name)}\b", sql, flags=re.IGNORECASE) is not None


def _fill(template: str, **values: str) -> str:
    return PLACEHOLDER.sub(lambda match: values.get(match.group(1), match.group(0)), template)
