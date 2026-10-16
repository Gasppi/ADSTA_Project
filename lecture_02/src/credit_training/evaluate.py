"""The final comparison, made once at the end: your baseline and the best model of each kind.

uv run python -m credit_training.evaluate
"""

from typing import Final

import numpy as np
import pandas as pd
import wandb
from sklearn.metrics import confusion_matrix

from credit_backend.decisions.dependencies import build_baseline
from credit_backend.decisions.features import FeatureVector
from credit_backend.decisions.scoring import RegisteredScorer, Scorer
from credit_training import logistic_regression, metrics, random_forest
from credit_training.data import Split, load_splits
from credit_training.registry import REGISTRY, best_alias
from credit_training.tracking import start_run

KINDS: Final = (logistic_regression.NAME, random_forest.NAME)


def candidates() -> dict[str, Scorer]:
    found: dict[str, Scorer] = {"baseline": build_baseline()}
    for kind in KINDS:
        path = f"{REGISTRY}:{best_alias(kind)}"
        try:
            found[kind] = RegisteredScorer.from_registry(path)
        except wandb.errors.CommError:
            print(f"There is no {path} yet, so the comparison leaves out {kind}.")
    return found


def probabilities(scorer: Scorer, rows: pd.DataFrame) -> np.ndarray:
    if isinstance(scorer, RegisteredScorer):
        return scorer.probabilities(rows)
    vectors = [FeatureVector(**row) for row in rows.to_dict("records")]
    return np.array([scorer.probability_of_default(vector) for vector in vectors])


def evaluate(scorer: Scorer, split: Split) -> dict[str, float]:
    p_default = probabilities(scorer, split.X)
    refused = p_default >= scorer.threshold
    tp, fn, fp, tn = confusion_matrix(split.y, refused, labels=[1, 0]).ravel()
    score = metrics.score(split.y, p_default, scorer.threshold)
    return {metrics.NAME: score, "TP": tp, "FN": fn, "FP": fp, "TN": tn}


def main() -> None:
    splits = load_splits()
    rows = []
    for name, scorer in candidates().items():
        val, test = evaluate(scorer, splits.val), evaluate(scorer, splits.test)
        rows.append(
            {
                "candidate": name,
                "version": scorer.model_version,
                "threshold": scorer.threshold,
                f"val/{metrics.NAME}": val[metrics.NAME],
                f"test/{metrics.NAME}": test[metrics.NAME],
                **{f"test/{cell}": test[cell] for cell in ("TP", "FN", "FP", "TN")},
            }
        )
    table = pd.DataFrame(rows)
    print(table.to_string(index=False))

    with start_run("evaluation", config={"metric": metrics.NAME}, job_type="evaluate") as run:
        run.log({"comparison": wandb.Table(dataframe=table)})


if __name__ == "__main__":
    main()
