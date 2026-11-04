from __future__ import annotations

from decimal import Decimal

from credit_extraction.contracts import Money, Period
from credit_extraction.documents.normalisation import (
    monthly_salary,
    parse_chf,
    parse_count,
    parse_yes_no,
)


def test_a_swiss_thousands_separator_is_read() -> None:
    assert parse_chf("CHF 6'000.00") == Decimal("6000.00")


def test_a_typographic_apostrophe_is_read_as_a_separator_too() -> None:
    assert parse_chf("CHF 6’000.00") == Decimal("6000.00")  # noqa: RUF001


def test_a_bare_number_is_read() -> None:
    assert parse_chf("5232.50") == Decimal("5232.50")


def test_a_negative_deduction_keeps_its_sign_out_of_the_amount() -> None:
    assert parse_chf("-CHF 318.00") == Decimal("318.00")


def test_text_with_no_number_returns_nothing_rather_than_zero() -> None:
    assert parse_chf("nicht angegeben") is None


def test_a_count_is_read() -> None:
    assert parse_count("3") == 3


def test_a_count_inside_a_sentence_is_read() -> None:
    assert parse_count("Anzahl Betreibungen: 2") == 2


def test_an_absent_count_returns_nothing() -> None:
    assert parse_count("keine Angabe") is None


def test_a_date_read_as_a_count_yields_its_first_number() -> None:
    assert parse_count("03.12.2023") == 3


def test_a_reference_number_read_as_an_amount_yields_its_first_number() -> None:
    assert parse_chf("2021/9790") == Decimal("2021")


def test_yes_is_recognised_in_both_languages() -> None:
    assert parse_yes_no("ja") is True
    assert parse_yes_no("yes") is True


def test_no_is_recognised_by_name_rather_than_by_being_anything_else() -> None:
    assert parse_yes_no("nein") is False
    assert parse_yes_no("no") is False


def test_casing_and_surrounding_space_do_not_change_the_answer() -> None:
    assert parse_yes_no("  JA  ") is True
    assert parse_yes_no("Nein\n") is False


def test_an_answer_meaning_neither_says_so_rather_than_no() -> None:
    # A register nobody could read must not arrive as a register with nothing on it.
    assert parse_yes_no("05.07.2022") is None
    assert parse_yes_no("") is None


def test_a_salary_read_from_a_payslip_is_monthly() -> None:
    assert monthly_salary("CHF 6'000.00") == Money(
        amount=Decimal("6000.00"), currency="CHF", period=Period.MONTHLY
    )


def test_a_salary_that_could_not_be_read_is_absent_rather_than_zero() -> None:
    assert monthly_salary("keine Angabe") is None
