import re

from venergy_agent.domain.vocabulary import folded_words

MAX_ELLIPTICAL_WORDS = 4

SAME_AS_BEFORE = re.compile(
    r"\b(?:fa[çz]a|faz|fazer|refa[çz]a|repita|repete)\s+(?:isso\s+)?(?:o\s+mesmo|a\s+mesma)\b"
    r"|^(?:agora\s+)?o\s+mesmo\s+(?:para|em|n[oa]|d[oa])\b"
    r"|\bmesma\s+coisa\b",
    re.IGNORECASE,
)


def depends_on_previous_turn(text: str) -> bool:
    stripped = text.strip()
    if SAME_AS_BEFORE.search(stripped):
        return True
    words = stripped.split()
    return len(words) <= MAX_ELLIPTICAL_WORDS and words[0].lower() == "e"


INTERROGATIVE_START = re.compile(
    r"^(?:qual|quais|quanto|quanta|quantos|quantas|como|por\s+que|onde|quem|quando)\b",
    re.IGNORECASE,
)
REQUEST_START = re.compile(
    r"^(?:liste|listar|mostre|mostra|mostrar|compare|comparar|traga|traz|calcule|calcular|"
    r"apresente|apresenta|informe|diga|me\s+(?:diga|mostre|mostra|informe|traga)|"
    r"quero|preciso|gere|gera)\b",
    re.IGNORECASE,
)
LONG_REPLY_WORDS = 5


def answers_a_clarification(reply: str, known: frozenset[str]) -> bool:
    """Resposta curta a um pedido de esclarecimento, e não uma pergunta nova.

    Pergunta nova é: tem "?", começa com palavra interrogativa, começa com verbo de pedido,
    ou tem cinco palavras ou mais e alguma delas é métrica do vocabulário. "percentual" ou
    "entre 2024 e 2025" respondem ao esclarecimento; "Receita de junho de 2026" não.
    """
    text = reply.strip()
    if not text or "?" in text:
        return False
    if INTERROGATIVE_START.match(text) or REQUEST_START.match(text):
        return False
    words = folded_words(text)
    return not (len(words) >= LONG_REPLY_WORDS and any(word in known for word in words))


def complete_question(original: str, reply: str) -> str:
    return f"{original.rstrip(' ?.')} Esclarecimento: {reply.strip()}"


CALENDAR_PERIOD = re.compile(
    r"\b(?:[úu]ltim[oa]|passad[oa])\s+(?:ano|trimestre|semestre|m[êe]s)\b"
    r"|\b(?:ano|trimestre|semestre|m[êe]s)\s+passado\b"
    r"|\b[úu]ltimos\s+(\d+)\s+meses\b",
    re.IGNORECASE,
)
BASE_PERIOD = re.compile(
    r"\b(?:primeiro|[úu]ltimo)\s+ano\s+da\s+(?:nossa\s+)?base\b", re.IGNORECASE
)
WRITTEN_YEAR = re.compile(r"\b(?:19|20)\d{2}\b")
BASE_WINDOW_MONTHS = "12"


def needs_a_calendar_period(text: str) -> bool:
    if WRITTEN_YEAR.search(text) or BASE_PERIOD.search(text):
        return False
    matches = list(CALENDAR_PERIOD.finditer(text))
    if any(match.group(1) == BASE_WINDOW_MONTHS for match in matches):
        return False
    return bool(matches)
