"""Measures Model B on the forty sample applicants, field by field and layout by layout.

Start the Information Extraction Service first. Then run this from the root of your repository.

    uv run python scripts/evaluate_extraction.py

Each metric is taken over all forty documents. A field the service could not read counts
as wrong, and the no-answer rate reports how often that happened.
"""

import argparse
import json
from collections.abc import Callable, Mapping
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any, Final

import httpx
import pandas as pd

SERVICE: Final = "http://localhost:8001"
TIMEOUT_SECONDS: Final = 300.0

type Measured = float | Mapping[str, float]
type Metric = Callable[[pd.DataFrame], Measured]


def date_of_birth_accuracy(rows: pd.DataFrame) -> float:
    """The share of documents whose date of birth was read exactly."""
    return float((rows["read"] == rows["expected"]).mean())

CENTIMES: Final = Decimal("0.01")


def _cents(value: object) -> Decimal | None:
    """A salary as a Decimal rounded to centimes, or None when nothing was read."""
    return None if pd.isna(value) else Decimal(str(value)).quantize(CENTIMES)


def _same_name(value: object) -> str | None:
    """A name without case and extra spaces, or None when nothing was read."""
    return None if pd.isna(value) else " ".join(str(value).split()).lower()


def _ratio(part: int, whole: int) -> float:
    return part / whole if whole else float("nan")


def gross_accuracy(rows: pd.DataFrame) -> float:
    """The share of documents whose gross salary was read exactly, to the centime."""
    expected = rows["expected"].map(_cents)
    read = rows["read"].map(_cents)
    return float((read == expected).mean())


def gross_mean_absolute_error(rows: pd.DataFrame) -> float:
    """The mean absolute error of the gross salary in CHF, over the documents that were read."""
    read = rows[rows["read"].notna()]
    errors = (read["read"].astype(float) - read["expected"].astype(float)).abs()
    return float(errors.mean())


def loss_certificate_precision_recall(rows: pd.DataFrame) -> dict[str, float]:
    """Precision and recall of an open loss certificate, over the documents that were read."""
    read = rows[rows["read"].notna()]
    matrix = pd.crosstab(read["expected"].astype(bool), read["read"].astype(bool))
    matrix = matrix.reindex(index=[False, True], columns=[False, True], fill_value=0)
    true_positive = int(matrix.at[True, True])
    false_positive = int(matrix.at[False, True])
    false_negative = int(matrix.at[True, False])
    return {
        "precision": _ratio(true_positive, true_positive + false_positive),
        "recall": _ratio(true_positive, true_positive + false_negative),
    }


def applicant_name_accuracy(rows: pd.DataFrame) -> float:
    """The share of documents whose name was read exactly, ignoring case and extra spaces."""
    expected = rows["expected"].map(_same_name)
    read = rows["read"].map(_same_name)
    return float((read == expected).mean())


def no_answer_rate(rows: pd.DataFrame) -> float:
    """The share of documents for which the service read nothing."""
    return float(rows["read"].isna().mean())


METRICS: Final[dict[str, dict[str, Metric]]] = {
    "gross": {
        "accuracy": gross_accuracy,
        "mean absolute error in CHF": gross_mean_absolute_error,
        "no-answer rate": no_answer_rate,
    },
    "has_loss_certificate": {
        "precision and recall": loss_certificate_precision_recall,
        "no-answer rate": no_answer_rate,
    },
    "applicant_name": {"accuracy": applicant_name_accuracy, "no-answer rate": no_answer_rate},
    "date_of_birth": {"accuracy": date_of_birth_accuracy, "no-answer rate": no_answer_rate},
}


def find_documents() -> Path:
    """data/sample-documents in the folder you run from, or in the nearest folder above."""
    for folder in (Path.cwd(), *Path.cwd().parents):
        documents = folder / "data" / "sample-documents"
        if documents.is_dir():
            return documents
    raise FileNotFoundError(f"There is no data/sample-documents in {Path.cwd()} or above it.")


def layout_of(document: Path) -> str:
    """The layout a document was drawn with, which its name carries, as in payslip_007_ledger."""
    return document.stem.split("_", 2)[2]


def only(documents: Path, pattern: str) -> Path:
    found = sorted(documents.glob(pattern))
    if len(found) != 1:
        raise FileNotFoundError(f"{len(found)} documents match {pattern} in {documents}")
    return found[0]


def rows_for(
    known: Mapping[str, Any], payslip: Path, register: Path, read: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """One row for each field of one applicant: what the document says, and what was read."""
    gross = read["payslip"]["gross"]
    extract = read["debt_register"]
    born = extract["date_of_birth"]

    def row(field: str, document: Path, expected: object, value: object) -> dict[str, Any]:
        return {
            "applicant": known["index"],
            "field": field,
            "document": document.name,
            "layout": layout_of(document),
            "expected": expected,
            "read": value,
        }

    return [
        row(
            "gross",
            payslip,
            Decimal(known["gross_monthly"]),
            None if gross is None else Decimal(gross["amount"]),
        ),
        row(
            "has_loss_certificate",
            register,
            known["has_loss_certificate"],
            extract["has_loss_certificate"],
        ),
        row("applicant_name", register, known["employee"], extract["applicant_name"]),
        row(
            "date_of_birth",
            register,
            date.fromisoformat(known["born"]),
            None if born is None else date.fromisoformat(born),
        ),
    ]


def read_all(client: httpx.Client, documents: Path) -> pd.DataFrame:
    truth = json.loads((documents / "ground_truth.json").read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = []
    for known in truth:
        payslip = only(documents, f"payslip_{known['index']:03d}_*.pdf")
        register = only(documents, f"register_{known['index']:03d}_*.pdf")
        response = client.post(
            "/extractions",
            files={"payslip": payslip.read_bytes(), "debt_register": register.read_bytes()},
        )
        response.raise_for_status()
        rows.extend(rows_for(known, payslip, register, response.json()))
        print(f"read applicant {known['index']:03d}", flush=True)
    return pd.DataFrame(rows)


def measured(metric: Metric, rows: pd.DataFrame) -> str:
    """The value of one metric as text, or the task that it still waits for."""
    try:
        value = metric(rows)
    except NotImplementedError as error:
        return str(error)
    if isinstance(value, Mapping):
        return "  ".join(f"{name} {number:.3f}" for name, number in value.items())
    return f"{value:.3f}"


def report(frame: pd.DataFrame) -> None:
    for field, metrics in METRICS.items():
        rows = frame[frame["field"] == field]
        print(f"\n{field}, over {len(rows)} documents")
        for name, metric in metrics.items():
            print(f"  {name:28s} {measured(metric, rows)}")

        by_layout = pd.DataFrame(
            {
                name: {
                    layout: measured(metric, group).split(":")[0]
                    for layout, group in rows.groupby("layout")
                }
                for name, metric in metrics.items()
            }
        )
        print("\n  by layout")
        print("  " + by_layout.to_string().replace("\n", "\n  "))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--service", default=SERVICE, help="where the extraction service answers")
    parser.add_argument("--documents", type=Path, default=None)
    parser.add_argument("--csv", type=Path, default=None, help="also write every row to this file")
    arguments = parser.parse_args()

    documents = arguments.documents or find_documents()
    with httpx.Client(base_url=arguments.service, timeout=TIMEOUT_SECONDS) as client:
        frame = read_all(client, documents)
    if arguments.csv is not None:
        frame.to_csv(arguments.csv, index=False)
    report(frame)


if __name__ == "__main__":
    main()
