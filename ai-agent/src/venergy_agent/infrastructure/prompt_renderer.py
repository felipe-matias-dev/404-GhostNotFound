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

DELIMITER_TAG = re.compile(r"<\s*(/?)\s*(dados|pergunta)\s*>", flags=re.IGNORECASE)
PLACEHOLDER = re.compile(r"\{\{(\w+)\}\}")


def render_system_prompt(template: str, layer: SemanticLayer) -> str:
    sections = [
        _section("Regras de negócio", [f"- {rule.text}" for rule in layer.rules]),
        _section("Glossário", [_glossary_line(term) for term in layer.glossary]),
        _section("Views disponíveis", [_view_block(view) for view in layer.views]),
        _section(
            "Relações",
            [
                f"- {r.left_view}.{r.left_column} = {r.right_view}.{r.right_column}"
                for r in layer.relations
            ],
        ),
        _section("Exemplos", [_example_block(example) for example in layer.examples]),
    ]
    return _fill(template, contexto="\n\n".join(section for section in sections if section))


def render_user_prompt(
    question: Question,
    feedback: AttemptFeedback | None,
    correction_template: str,
    layer: SemanticLayer,
) -> str:
    asked = f"<pergunta>\n{_escape(question.text)}\n</pergunta>"
    if feedback is None:
        return asked
    involved = [
        view for view in layer.views if _mentions(feedback.previous_sql, view.name)
    ] or list(layer.views)
    correction = _fill(
        correction_template,
        sql_anterior=_data(feedback.previous_sql),
        tipo_erro=feedback.error_kind.value,
        mensagem=_data(feedback.message),
        colunas="\n".join(_columns_line(view) for view in involved),
    )
    return f"{correction}\n\n{asked}"


def _section(title: str, lines: list[str]) -> str:
    return f"## {title}\n\n" + "\n".join(lines) if lines else ""


def _glossary_line(term: GlossaryTerm) -> str:
    words = ", ".join(f'"{word}"' for word in (term.term, *term.synonyms))
    return f"- {words} → {term.maps_to}"


def _view_block(view: ViewSpec) -> str:
    lines = [f"### {view.name}", f"{view.description}. Grão: {view.grain}.", "Colunas:"]
    lines += [_column_line(column) for column in view.columns]
    if view.sample_rows:
        rows = "\n".join(
            json.dumps(row, ensure_ascii=False, default=str) for row in view.sample_rows
        )
        lines += ["Linhas de exemplo:", _data(rows)]
    return "\n".join(lines)


def _column_line(column: ColumnSpec) -> str:
    unit = f", {column.unit}" if column.unit else ""
    line = f"- {column.name} ({column.type}{unit}): {column.description}"
    if column.allowed_values:
        line += f". Valores possíveis: {_data(', '.join(column.allowed_values))}"
    return line


def _columns_line(view: ViewSpec) -> str:
    return f"- {view.name}: " + ", ".join(column.name for column in view.columns)


def _example_block(example: FewShotExample) -> str:
    sql = f"```sql\n{example.sql}\n```" if example.sql else "(sem SQL)"
    return f"Pergunta: {example.question}\nStatus esperado: {example.expected_status.value}\n{sql}"


def _data(text: str) -> str:
    return f"<dados>\n{_escape(text)}\n</dados>"


def _escape(text: str) -> str:
    return DELIMITER_TAG.sub(r"&lt;\1\2&gt;", text)


def _mentions(sql: str, name: str) -> bool:
    return re.search(rf"\b{re.escape(name)}\b", sql, flags=re.IGNORECASE) is not None


def _fill(template: str, **values: str) -> str:
    return PLACEHOLDER.sub(lambda match: values.get(match.group(1), match.group(0)), template)
