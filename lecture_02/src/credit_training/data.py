"""The training data for Model A, loaded, cleaned and split before anything learns from it."""

from dataclasses import dataclass, fields
from pathlib import Path
from typing import Final

import pandas as pd
from sklearn.model_selection import train_test_split

from credit_backend.decisions.features import FeatureVector

FILE_NAME: Final = "credit_risk_dataset.csv"
TARGET: Final = "dlq_2yrs"
FEATURES: Final = tuple(field.name for field in fields(FeatureVector))
LATE_PAYMENTS: Final = ("late_30_59", "late_60_89", "late_90")
CODES: Final = (96, 98)
SEED: Final = 42


@dataclass(frozen=True)
class Split:
    X: pd.DataFrame
    y: pd.Series


@dataclass(frozen=True)
class Splits:
    train: Split
    val: Split
    test: Split


def find_data() -> Path:
    """data/credit_risk_dataset.csv in the folder you run from, or in the nearest folder above."""
    for folder in (Path.cwd(), *Path.cwd().parents):
        path = folder / "data" / FILE_NAME
        if path.is_file():
            return path
    raise FileNotFoundError(f"There is no data/{FILE_NAME} in {Path.cwd()} or above it.")


def load_raw(path: Path | None = None) -> pd.DataFrame:
    """The file as it is, duplicates and codes included."""
    return pd.read_csv(path or find_data())


def clean(raw: pd.DataFrame) -> pd.DataFrame:
    """The fixes that learn nothing from the data, so they come before the split."""
    data = raw.drop_duplicates()
    coded = data[list(LATE_PAYMENTS)].isin(CODES).any(axis=1)
    return data[~coded]


def split(data: pd.DataFrame, seed: int = SEED) -> Splits:
    """70% training, 15% validation and 15% test, each with the class balance of the whole."""
    train, rest = train_test_split(data, test_size=0.30, stratify=data[TARGET], random_state=seed)
    val, test = train_test_split(rest, test_size=0.50, stratify=rest[TARGET], random_state=seed)
    return Splits(*(Split(X=part[list(FEATURES)], y=part[TARGET]) for part in (train, val, test)))


def load_splits(path: Path | None = None) -> Splits:
    """The cleaned data, split. The features keep their raw units, as your baseline expects them."""
    return split(clean(load_raw(path)))
