from collections.abc import Callable
from pathlib import Path
from typing import Any

import pandas as pd
import pytest
from evaluate_extraction import (
    METRICS,
    applicant_name_accuracy,
    date_of_birth_accuracy,
    gross_accuracy,
    gross_mean_absolute_error,
    loss_certificate_precision_recall,
    measured,
    no_answer_rate,
    report,
    rows_for,
)

PAYSLIP = Path("payslip_000_letterhead.pdf")
REGISTER = Path("register_000_form.pdf")


def applicant(index: int, gross: str, certificate: bool, name: str, born: str) -> dict[str, Any]:
    return {
        "index": index,
        "gross_monthly": gross,
        "has_loss_certificate": certificate,
        "employee": name,
        "born": born,
    }


def reading(gross: str | None, certificate: bool | None, name: str | None, born: str | None):
    return {
        "payslip": {
            "gross": None
            if gross is None
            else {"amount": gross, "currency": "CHF", "period": "monthly"}
        },
        "debt_register": {
            "has_loss_certificate": certificate,
            "applicant_name": name,
            "date_of_birth": born,
        },
        "checkpoint": "model-b@0123abc",
    }


FRAME = pd.DataFrame(
    [
        *rows_for(
            applicant(0, "6000.00", True, "Anna Furrer", "1990-01-02"),
            PAYSLIP,
            REGISTER,
            reading("6000.00", True, "anna  furrer", "1990-01-02"),
        ),
        *rows_for(
            applicant(1, "5000.00", True, "Beat Duss", "1980-03-04"),
            PAYSLIP,
            REGISTER,
            reading("5100.00", False, "Beat Dus", None),
        ),
        *rows_for(
            applicant(2, "7000.00", False, "Chiara Gut", "1970-05-06"),
            PAYSLIP,
            REGISTER,
            reading("7000", True, None, "1970-05-07"),
        ),
        *rows_for(
            applicant(3, "8000.00", False, "Daniel Bucher", "1960-07-08"),
            PAYSLIP,
            REGISTER,
            reading("8000.00", False, "Daniel Bucher", "1960-07-08"),
        ),
    ]
)


def field(name: str) -> pd.DataFrame:
    return FRAME[FRAME["field"] == name]


def value_of[T](metric: Callable[[pd.DataFrame], T], rows: pd.DataFrame) -> T:
    try:
        return metric(rows)
    except NotImplementedError as error:
        pytest.skip(str(error))


def test_every_applicant_gives_one_row_per_field_with_its_layout() -> None:
    assert len(FRAME) == 4 * len(METRICS)
    assert set(FRAME["field"]) == set(METRICS)
    assert set(FRAME["layout"]) == {"letterhead", "form"}


def test_a_date_nobody_could_read_counts_as_wrong() -> None:
    assert date_of_birth_accuracy(field("date_of_birth")) == 0.5


def test_the_report_runs_before_every_metric_is_written(capsys: pytest.CaptureFixture[str]) -> None:
    report(FRAME)

    assert "date_of_birth, over 4 documents" in capsys.readouterr().out


def test_a_metric_that_is_not_written_names_its_task() -> None:
    def unwritten(rows: pd.DataFrame) -> float:
        raise NotImplementedError("Task 5: unwritten")

    assert measured(unwritten, FRAME) == "Task 5: unwritten"


def test_the_gross_salary_matches_after_normalising() -> None:
    assert value_of(gross_accuracy, field("gross")) == 0.75


def test_the_mean_absolute_error_is_in_chf() -> None:
    assert value_of(gross_mean_absolute_error, field("gross")) == pytest.approx(25.0)


def test_precision_and_recall_count_an_open_loss_certificate_as_positive() -> None:
    measured = value_of(loss_certificate_precision_recall, field("has_loss_certificate"))

    assert measured["precision"] == pytest.approx(0.5)
    assert measured["recall"] == pytest.approx(0.5)


def test_a_name_matches_whatever_its_case_and_spaces() -> None:
    assert value_of(applicant_name_accuracy, field("applicant_name")) == 0.5


def test_a_field_nobody_could_read_is_counted_apart() -> None:
    assert value_of(no_answer_rate, field("applicant_name")) == 0.25
    assert value_of(no_answer_rate, field("gross")) == 0.0
