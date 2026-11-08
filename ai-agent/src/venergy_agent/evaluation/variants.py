import re
import unicodedata
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from venergy_agent.domain.semantic import GlossaryTerm

SKIPPED_CATEGORIES = frozenset({"followup", "injecao", "manipulacao"})
MIN_TYPO_LENGTH = 5
WORD = re.compile(r"[^\W\d_]+")


def make_variants(
    items: Sequence[Mapping[str, Any]], glossary: Sequence[GlossaryTerm]
) -> list[dict[str, Any]]:
    kinds: dict[str, Callable[[str], str | None]] = {
        "sem_acento": _without_accents,
        "erro": _with_typo,
        "sinonimo": lambda question: _with_synonym(question, glossary),
        "coloquial": _colloquial,
    }
    variants = []
    for item in items:
        if item.get("follow_up_of") or item["category"] in SKIPPED_CATEGORIES:
            continue
        for kind, rewrite in kinds.items():
            question = rewrite(item["question"])
            if question is None or question == item["question"]:
                continue
            variants.append({**item, "id": f"{item['id']}~{kind}", "question": question})
    return variants


def _without_accents(question: str) -> str:
    decomposed = unicodedata.normalize("NFKD", question)
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def _with_typo(question: str) -> str | None:
    words = [match for match in WORD.finditer(question) if len(match.group()) >= MIN_TYPO_LENGTH]
    if not words:
        return None
    target = max(words, key=lambda match: (len(match.group()), -match.start()))
    word = target.group()
    middle = len(word) // 2
    swapped = word[: middle - 1] + word[middle] + word[middle - 1] + word[middle + 1 :]
    if swapped == word:
        return None
    return question[: target.start()] + swapped + question[target.end() :]


def _with_synonym(question: str, glossary: Sequence[GlossaryTerm]) -> str | None:
    for term in glossary:
        if not term.synonyms:
            continue
        for written, replacement in [
            (term.term, term.synonyms[0]),
            *((synonym, term.term) for synonym in term.synonyms),
        ]:
            pattern = re.compile(rf"(?<!\w){re.escape(written)}(?!\w)", re.IGNORECASE)
            if pattern.search(question):
                return pattern.sub(replacement, question, count=1)
    return None


def _colloquial(question: str) -> str:
    text = question.strip().rstrip("?").strip()
    return f"me diz {text[:1].lower()}{text[1:]}"
