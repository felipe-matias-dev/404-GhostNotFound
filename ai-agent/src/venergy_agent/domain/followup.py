import re

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
