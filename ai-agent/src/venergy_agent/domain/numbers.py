import re
from collections.abc import Iterable
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

PT_BR_NUMBER = re.compile(r"(?<![\d.,])(?<![^\W\d_])(?<![^\W\d_]-)\d+(?:[.,]\d+)*")
MACHINE_NUMBER = re.compile(r"\d+(?:\.\d+)?")
PERIOD_UNIT = r"(?:meses|anos|trimestres|semestres|competências)\b"
DURATION = re.compile(
    rf"(?:primeir|últim)[oa]s\s+(\d+)\s+{PERIOD_UNIT}"
    rf"|(?<![\d.,])(\d+)\s+(?:primeir|últim)[oa]s\s+{PERIOD_UNIT}",
    re.IGNORECASE,
)
WRITTEN_DURATION = re.compile(
    rf"(?<![\d.,])(\d+)\s+(?:(?:primeir|últim)[oa]s\b|{PERIOD_UNIT})", re.IGNORECASE
)
DISPLAY_DECIMALS = 2
DISPLAY_SIGNIFICANT = 3


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


def _rounds_to(value: Decimal, number: Decimal, decimals: int) -> bool:
    try:
        return value.quantize(Decimal(1).scaleb(-decimals), rounding=ROUND_HALF_UP) == number
    except InvalidOperation:
        return False


def _supported(token: str, known: set[Decimal]) -> bool:
    number = _from_pt_br(token)
    if number is None:
        return False
    if number in known:
        return True
    _, comma, decimals = token.rpartition(",")
    if not comma:
        return any(rounded_for_display(value) == number for value in known)
    return any(_rounds_to(value, number, len(decimals)) for value in known)


UNIT_BEFORE = re.compile(r"R\$\s*-?(\d+(?:[.,]\d+)*)")
UNIT_AFTER = re.compile(r"(?<![\d.,])(\d+(?:[.,]\d+)*)\s*(kWh|%|h\b)")


def written_units(text: str) -> tuple[tuple[str, str], ...]:
    before = ((match.group(1), "R$") for match in UNIT_BEFORE.finditer(text))
    after = ((match.group(1), match.group(2)) for match in UNIT_AFTER.finditer(text))
    return (*before, *after)


def supports(token: str, value: object) -> bool:
    return _supported(token, _numbers_in_value(value))


def pt_br_numbers(text: str) -> set[Decimal]:
    found = (_from_pt_br(token) for token in PT_BR_NUMBER.findall(text))
    return {number for number in found if number is not None}


def durations(text: str) -> set[Decimal]:
    return {Decimal(match.group(1) or match.group(2)) for match in DURATION.finditer(text)}


def unsupported_numbers(
    text: str, values: Iterable[object], allowed_durations: Iterable[Decimal] = ()
) -> tuple[str, ...]:
    known: set[Decimal] = set()
    for value in values:
        known |= _numbers_in_value(value)
    allowed = set(allowed_durations)
    written_as_duration = {
        match.start(1) if match.group(1) else match.start(2) for match in DURATION.finditer(text)
    } | {match.start(1) for match in WRITTEN_DURATION.finditer(text)}
    return tuple(
        match.group()
        for match in PT_BR_NUMBER.finditer(text)
        if not _supported(match.group(), known)
        and not (match.start() in written_as_duration and Decimal(match.group()) in allowed)
    )


def rounded_for_display(value: Decimal) -> Decimal:
    exponent = value.as_tuple().exponent
    if not isinstance(exponent, int) or exponent >= -DISPLAY_DECIMALS:
        return value
    places = DISPLAY_DECIMALS if abs(value) >= 1 else DISPLAY_SIGNIFICANT - value.adjusted() - 1
    rounded = value.quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)
    return _trimmed(rounded)


def _trimmed(value: Decimal) -> Decimal:
    sign, digits, exponent = value.as_tuple()
    digits_list = list(digits)
    while isinstance(exponent, int) and exponent < 0 and digits_list and digits_list[-1] == 0:
        digits_list.pop()
        exponent += 1
    return Decimal((sign, tuple(digits_list), exponent))


TWO_DECIMAL_UNITS = frozenset({"h", "%", "R$"})
INTEGER_UNITS = frozenset({"kWh", "contagem"})


def display_for_unit(value: Decimal, unit: str | None) -> Decimal:
    """Política de exibição por unidade (DEC-080): h, % e R$ com até 2 casas; kWh e contagem
    inteiros; sem unidade, a regra antiga."""
    if unit in TWO_DECIMAL_UNITS:
        return _trimmed(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
    if unit in INTEGER_UNITS:
        return value.quantize(Decimal(1), rounding=ROUND_HALF_UP)
    return rounded_for_display(value)
