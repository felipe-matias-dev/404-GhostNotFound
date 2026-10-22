import re
from collections.abc import Iterable
from decimal import Decimal, InvalidOperation

TOKEN = re.compile(r"\d+(?:[.,]\d+)*")


def _candidates(token: str) -> set[Decimal]:
    # "1.234,56" (pt-BR), "1,234.56" (en) e "1234.5" (valor do banco) são lidos de duas
    # maneiras: o mesmo texto pode ser milhar ou decimal, e a verificação aceita qualquer leitura.
    readings = {
        token.replace(".", "").replace(",", "."),
        token.replace(",", ""),
        token.replace(",", "."),
    }
    numbers: set[Decimal] = set()
    for reading in readings:
        try:
            numbers.add(Decimal(reading))
        except InvalidOperation:
            continue
    return numbers


def numbers_in(text: str) -> set[Decimal]:
    numbers: set[Decimal] = set()
    for token in TOKEN.findall(text):
        numbers |= _candidates(token)
    return numbers


def unsupported_numbers(text: str, sources: Iterable[str]) -> tuple[str, ...]:
    """Números do texto que nenhuma fonte contém. Vazio: o texto é fiel às fontes."""
    known: set[Decimal] = set()
    for source in sources:
        known |= numbers_in(source)
    return tuple(token for token in TOKEN.findall(text) if not (_candidates(token) & known))
