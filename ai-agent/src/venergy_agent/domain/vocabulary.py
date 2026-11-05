import difflib
import re
import unicodedata
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

MIN_LENGTH = 5
CUTOFF = 0.8
CANDIDATES = 3
WORD = re.compile(r"[^\W\d_]+")
STOPWORDS = frozenset({"entre", "quanto", "quantos", "quantas", "mostre", "dessa", "desse"})


def _fold(word: str) -> str:
    decomposed = unicodedata.normalize("NFKD", word.lower())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def _words(text: str) -> list[str]:
    return WORD.findall(text)


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
