"""Where the probability of default comes from."""

import json
import tempfile
from dataclasses import asdict, fields
from pathlib import Path
from typing import Protocol

import joblib
import numpy as np
import pandas as pd

from credit_backend.decisions.features import FeatureVector


class Scorer(Protocol):
    @property
    def model_version(self) -> str: ...

    @property
    def threshold(self) -> float: ...

    def probability_of_default(self, features: FeatureVector) -> float | None: ...


class PlaceholderScorer(Scorer):
    """The same probability for every applicant."""

    @property
    def model_version(self) -> str:
        return "placeholder"

    @property
    def threshold(self) -> float:
        return 0.30

    def probability_of_default(self, features: FeatureVector) -> float:
        return 0.10


# Your baseline from lecture 2 stays here, such as BaselineScorer(Scorer).


class MismatchedFeaturesError(RuntimeError):
    """The registered model was trained on other features than the backend builds."""


class RegisteredScorer(Scorer):
    """Model A as the training job registered it, preprocessing included."""

    def __init__(self, folder: Path, version: str) -> None:
        metadata = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
        built = {field.name for field in fields(FeatureVector)}
        if set(metadata["features"]) != built:
            raise MismatchedFeaturesError(
                f"The model was trained on {sorted(metadata['features'])}, "
                f"but the backend builds {sorted(built)}."
            )
        self._features: list[str] = metadata["features"]
        self._threshold = float(metadata["threshold"])
        self._pipeline = joblib.load(folder / "model.joblib")
        self._version = version

    @classmethod
    def from_registry(cls, path: str) -> "RegisteredScorer":
        """Downloads a registered version, such as wandb-registry-model/model-a:production."""
        import wandb

        artifact = wandb.Api().artifact(path, type="model")
        folder = artifact.download(root=tempfile.mkdtemp(prefix="model-a-"))
        return cls(Path(folder), version=f"{artifact.collection.name}:{artifact.version}")

    @property
    def model_version(self) -> str:
        return self._version

    @property
    def threshold(self) -> float:
        return self._threshold

    def probabilities(self, rows: pd.DataFrame) -> np.ndarray:
        return self._pipeline.predict_proba(rows[self._features])[:, 1]

    def probability_of_default(self, features: FeatureVector) -> float | None:
        """None when a feature is missing, because the model cannot score what nobody read."""
        row = asdict(features)
        if any(value is None for value in row.values()):
            return None
        return float(self.probabilities(pd.DataFrame([row]))[0])
# Task 6: each of you adds a scorer here, such as BaselineScorer(Scorer). It works out a
# probability of default by hand from the features, until Model A replaces it in lecture 3.
# Ask yourself: if I judged an applicant from these features alone, which figures would
# worry me, and how much?

class GasparBaselineScorer(Scorer):
    """Hand-built credit risk estimate incorporating debt ratio, revolving utilisation, and severe lateness."""

    @property
    def model_version(self) -> str:
        return "gaspar-baseline-v1"

    @property
    def threshold(self) -> float:
        return 0.35

    def probability_of_default(self, features: FeatureVector) -> float:
        debt_ratio = features.debt_ratio if features.debt_ratio is not None else 0.50
        revolving_util = (
            features.revolving_utilisation
            if features.revolving_utilisation is not None
            else 0.30
        )
        late_90 = features.late_90 if features.late_90 is not None else 0.0

        raw_prob = (
            0.03
            + (debt_ratio * 0.35)
            + (revolving_util * 0.25)
            + (late_90 * 0.18)
        )

        return max(0.0, min(1.0, round(raw_prob, 4)))

