import re
import unicodedata
from collections.abc import Iterable, Mapping, Sequence

MAX_LISTED = 15
COLUMN = r"(?:(?:lower|upper|unaccent)\s*\(\s*)?(?:\w+\.)?(?P<column>\w+)\s*\)?"
LITERAL = r"'(?P<value>(?:[^']|'')*)'"
COMPARISON = re.compile(rf"{COLUMN}\s*(?:=|i?like)\s*{LITERAL}", re.IGNORECASE)
IN_LIST = re.compile(rf"{COLUMN}\s+in\s*\((?P<items>[^)]*)\)", re.IGNORECASE)
SUBQUERY = re.compile(r"\s*select\b", re.IGNORECASE)
ITEM = re.compile(r"'((?:[^']|'')*)'")


def known_values(columns: Iterable[tuple[str, Sequence[str]]]) -> dict[str, tuple[str, ...]]:
    known: dict[str, tuple[str, ...]] = {}
    for name, values in columns:
        known[name] = tuple(dict.fromkeys((*known.get(name, ()), *values)))
    return known


def filter_value_problem(sql: str, known: Mapping[str, Sequence[str]]) -> str | None:
    for column, value in _filters(sql):
        values = known.get(column.lower())
        if not values or _matches(value, values):
            continue
        written = value.replace("%", "").strip()
        elsewhere = [
            other
            for other, options in known.items()
            if other != column.lower() and _matches(value, options)
        ]
        if elsewhere:
            return (
                f"'{written}' não é um valor de {column}: existe em {', '.join(elsewhere)}. "
                f"Filtre a coluna certa e só filtre {column} se a pergunta citar um {column}."
            )
        listed = ", ".join(values[:MAX_LISTED]) + (", …" if len(values) > MAX_LISTED else "")
        return (
            f"'{written}' não existe em {column} (valores: {listed}). Use o valor da lista que a "
            f"pergunta quer dizer; se ela fala da área toda da distribuidora, não filtre {column}."
        )
    return None


def _filters(sql: str) -> list[tuple[str, str]]:
    found = [(match["column"], match["value"]) for match in COMPARISON.finditer(sql)]
    for match in IN_LIST.finditer(sql):
        if SUBQUERY.match(match["items"]):
            continue
        found.extend((match["column"], item) for item in ITEM.findall(match["items"]))
    return found


def _matches(value: str, options: Sequence[str]) -> bool:
    pattern = re.compile(
        ".*".join(
            ".".join(re.escape(piece) for piece in part.split("_"))
            for part in _normalized(value).split("%")
        ),
        re.DOTALL,
    )
    return any(pattern.fullmatch(_normalized(option)) for option in options)


def _normalized(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.replace("''", "'").lower().strip())
    return "".join(char for char in decomposed if not unicodedata.combining(char))
