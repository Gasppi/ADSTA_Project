"""Raw model answers become typed values here."""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Final

from credit_extraction.contracts import Money, Period

AFFIRMATIVE: Final = frozenset({"ja", "yes", "oui", "si", "true", "1"})
NEGATIVE: Final = frozenset({"nein", "no", "non", "keine", "false", "0"})
# Swiss payroll software prints the thousands separator as either apostrophe.
_AMOUNT: Final = re.compile(r"\d[\d'’ ,]*(?:\.\d{1,2})?")  # noqa: RUF001
_COUNT: Final = re.compile(r"\d+")
# Swiss documents print a date as day, month, year, separated by full stops.
_DAY: Final = re.compile(r"(\d{1,2})[.\-/](\d{1,2})[.\-/](\d{4})")
_NONE_WORDS: Final = frozenset({"keine", "kein", "keinen", "none", "no", "null"})
_WORDS: Final = re.compile(r"[a-zA-ZäöüÄÖÜß]+|\d+")


def parse_chf(text: str) -> Decimal | None:
    match = _AMOUNT.search(text)
    if match is None:
        return None
    digits = re.sub(r"[^\d.]", "", match.group())
    try:
        return Decimal(digits)
    except InvalidOperation:
        return None


def parse_count(text: str) -> int | None:
    match = _COUNT.search(text)
    return int(match.group()) if match else None


def parse_yes_no(text: str) -> bool | None:
    """None when the answer means neither yes nor no."""
    answer = text.strip().casefold()
    if answer in AFFIRMATIVE:
        return True
    if answer in NEGATIVE:
        return False
    return None


def monthly_salary(answer: str) -> Money | None:
    """A salary line on a Swiss payslip states what is paid for one month."""
    amount = parse_chf(answer)
    if amount is None:
        return None
    return Money(amount=amount, currency="CHF", period=Period.MONTHLY)


def birth_date(answer: str) -> date | None:
    """A date of birth out of whatever span the model returned."""
    found = _DAY.search(answer)
    if found is None:
        return None
    day, month, year = (int(part) for part in found.groups())
    try:
        return date(year, month, day)
    except ValueError:
        return None


def certificate_count(answer: str) -> bool | None:
    """Whether the count the model returned is one or more, or None if it is neither."""
    words = _WORDS.findall(answer.casefold())
    if any(word in _NONE_WORDS for word in words):
        return False
    found = _COUNT.search(answer)
    return int(found.group()) > 0 if found else None


def person_name(answer: str) -> str | None:
    """A person's name out of the span the model returned, or None if it returned nothing."""
    tidied = " ".join(answer.split()).strip(" ,.:;-")
    return tidied or None
