import re
from typing import Annotated

from pydantic import StringConstraints

NonBlankText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


UNITS = {
    "um": 1,
    "dois": 2,
    "três": 3,
    "tres": 3,
    "quatro": 4,
    "cinco": 5,
    "seis": 6,
    "sete": 7,
    "oito": 8,
    "nove": 9,
    "dez": 10,
    "onze": 11,
    "doze": 12,
    "treze": 13,
    "quatorze": 14,
    "catorze": 14,
    "quinze": 15,
    "dezesseis": 16,
    "dezessete": 17,
    "dezoito": 18,
    "dezenove": 19,
}
TENS = {
    "vinte": 20,
    "trinta": 30,
    "quarenta": 40,
    "cinquenta": 50,
    "sessenta": 60,
    "setenta": 70,
    "oitenta": 80,
    "noventa": 90,
}
_UNIT = "|".join(sorted(UNITS, key=len, reverse=True))
_TEN = "|".join(TENS)
SPELLED_YEAR = re.compile(
    rf"\bdois\s+mil(?:\s+e\s+(?:(?P<ten>{_TEN})(?:\s+e\s+(?P<tail>{_UNIT}))?|(?P<unit>{_UNIT})))?\b",
    re.IGNORECASE,
)


def _as_digits(match: re.Match[str]) -> str:
    ten = TENS.get((match["ten"] or "").lower(), 0)
    unit = UNITS.get((match["tail"] or match["unit"] or "").lower(), 0)
    return str(2000 + ten + unit)


def with_spelled_years_as_digits(text: str) -> str:
    return SPELLED_YEAR.sub(_as_digits, text)
