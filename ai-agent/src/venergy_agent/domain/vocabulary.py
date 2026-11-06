import difflib
import re
import unicodedata
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

MIN_LENGTH = 5
CUTOFF = 0.8
CANDIDATES = 3
VALUE_CUTOFF = 0.85
MAX_VALUE_WORDS = 4
WORD = re.compile(r"[^\W\d_]+")
STOPWORDS = frozenset({"entre", "quanto", "quantos", "quantas", "mostre", "dessa", "desse"})


def _fold(word: str) -> str:
    decomposed = unicodedata.normalize("NFKD", word.lower())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def _words(text: str) -> list[str]:
    return WORD.findall(text)


def folded_words(text: str) -> list[str]:
    return [_fold(word) for word in _words(text)]


def known_words(vocabulary: Iterable[str]) -> frozenset[str]:
    """Palavras do vocabulário, sem acento e em minúscula, que contam para detectar métrica."""
    return frozenset(
        folded
        for term in vocabulary
        for folded in folded_words(term)
        if len(folded) >= MIN_LENGTH and folded not in STOPWORDS
    )


def close_terms(question: str, vocabulary: Iterable[str]) -> dict[str, list[str]]:
    """Palavras da pergunta que não estão no vocabulário e lembram uma que está.

    Só sugere: quem decide se a sugestão vira termo do glossário é uma pessoa. Palavras
    curtas e as de STOPWORDS nunca entram, e a comparação ignora acentos e maiúsculas.
    """
    original: dict[str, str] = {}
    for term in vocabulary:
        for word in _words(term):
            original.setdefault(_fold(word), word)
    suggestions: dict[str, list[str]] = {}
    for word in _words(question):
        folded = _fold(word)
        if len(folded) < MIN_LENGTH or folded in original or folded in STOPWORDS:
            continue
        close = difflib.get_close_matches(folded, sorted(original), n=CANDIDATES, cutoff=CUTOFF)
        if close:
            suggestions[word] = [original[candidate] for candidate in close]
    return suggestions


def vocabulary_of(glossary: Sequence[Any], columns: Iterable[str]) -> list[str]:
    terms = [term for entry in glossary for term in (entry.term, *entry.synonyms)]
    return [*terms, *columns]


def unmapped_report(
    rows: Iterable[Mapping[str, Any]], vocabulary: Sequence[str]
) -> list[dict[str, Any]]:
    """Turnos de esclarecimento ou "não sei", com os termos parecidos e as suposições do agente.

    Não lê respostas nem números: só a pergunta, o status e as suposições, que a auditoria já
    guarda. Quem roda o relatório é a TI ou Dados, não o usuário do agente.
    """
    report = []
    for row in rows:
        if row["status"] not in ("clarify", "unknown"):
            continue
        assumptions = [item for item in row["assumptions"] if "entendi" in item]
        report.append(
            {
                "pergunta": row["pergunta"],
                "status": row["status"],
                "sugestoes": close_terms(row["pergunta"], vocabulary),
                "suposicoes": assumptions,
            }
        )
    return report


def value_hints(question: str, values: Mapping[str, Sequence[str]]) -> list[tuple[str, str, str]]:
    """Trechos da pergunta que são um valor da base escrito de outro jeito.

    Devolve (como foi escrito, valor da base, coluna). Sem acento, com outra caixa, com erro de
    digitação ou só o começo de um nome composto ("jaboatao" para Jaboatão dos Guararapes). O
    valor escrito igual ao da base não precisa de dica.
    """
    words = _words(question)
    folded_values = [
        (_fold(value), value, column) for column, options in values.items() for value in options
    ]
    hints: list[tuple[str, str, str]] = []
    used: set[int] = set()
    for size in range(MAX_VALUE_WORDS, 0, -1):
        for start in range(len(words) - size + 1):
            span = set(range(start, start + size))
            if span & used:
                continue
            written = " ".join(words[start : start + size])
            match = _value_match(_fold(written), folded_values, size)
            if match is None:
                continue
            used |= span
            value, column = match
            if written != value:
                hints.append((written, value, column))
    return sorted(hints, key=lambda hint: question.find(hint[0]))


def _value_match(
    folded: str, folded_values: Sequence[tuple[str, str, str]], size: int
) -> tuple[str, str] | None:
    if len(folded) < MIN_LENGTH:
        return None
    for value_folded, value, column in folded_values:
        if folded == value_folded:
            return value, column
    for value_folded, value, column in folded_values:
        if size == 1 and value_folded.startswith(f"{folded} "):
            return value, column
    for value_folded, value, column in folded_values:
        if len(value_folded.split()) == size and (
            difflib.SequenceMatcher(None, folded, value_folded).ratio() >= VALUE_CUTOFF
        ):
            return value, column
    return None
