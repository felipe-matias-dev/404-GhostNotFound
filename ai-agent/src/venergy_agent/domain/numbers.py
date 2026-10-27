import re
from collections.abc import Iterable
from decimal import Decimal, InvalidOperation

PT_BR_NUMBER = re.compile(r"(?<![\d.,])(?<![^\W\d_])(?<![^\W\d_]-)\d+(?:[.,]\d+)*")
MACHINE_NUMBER = re.compile(r"\d+(?:\.\d+)?")


def _from_pt_br(token: str) -> Decimal | None:
    try:
        return Decimal(token.replace(".", "").replace(",", "."))
    except InvalidOperation:
        return None


def _numbers_in_value(value: object) -> set[Decimal]:
    if isinstance(value, bool):
        return set()
    if isinstance(value, int | float | Decimal):
        return {abs(Decimal(str(value)))}
    text = str(value)
    if any(char.isalpha() for char in text):
        return set()
    return {Decimal(token) for token in MACHINE_NUMBER.findall(text)}


def unsupported_numbers(text: str, values: Iterable[object]) -> tuple[str, ...]:
    known: set[Decimal] = set()
    for value in values:
        known |= _numbers_in_value(value)
    return tuple(
        token
        for token in PT_BR_NUMBER.findall(text)
        if (number := _from_pt_br(token)) is None or number not in known
    )
