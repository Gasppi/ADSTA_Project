"""The connection to Weights & Biases that every run of the training job shares."""

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

import joblib
import numpy as np
import wandb
from sklearn.metrics import average_precision_score, precision_score, recall_score, roc_auc_score
from sklearn.pipeline import Pipeline

from credit_training import metrics
from credit_training.data import FEATURES, SEED

# Task 1: the name of your team on W&B, so that all three of you log into one project.
# None logs into your own account.
ENTITY: Final[str | None] = os.getenv("WANDB_ENTITY", "desmonduchenna503-university-of-luzern")
PROJECT: Final = "credit-model-a"

# W&B keeps a local copy of every run in WANDB_DIR. Outside the repository it stays out of Git.
os.environ.setdefault("WANDB_DIR", tempfile.gettempdir())


@dataclass(frozen=True)
class TrainedModel:
    """What one training run produces. The pipeline holds the fitted preprocessing and the model."""

    name: str
    pipeline: Pipeline
    score: float


def start_run(model: str, config: dict[str, Any], job_type: str = "train") -> wandb.Run:
    """One run in the project. In a sweep, W&B replaces the config values it searches."""
    return wandb.init(
        entity=ENTITY,
        project=PROJECT,
        job_type=job_type,
        group=model,
        tags=[model],
        config=config,
        name=f"{model}-run",
    )


def project_path(api: wandb.Api) -> str:
    return f"{ENTITY or api.default_entity}/{PROJECT}"


def save_model(trained: TrainedModel, folder: Path) -> dict[str, Any]:
    """The two files the backend loads: the pipeline, and what it needs to know about it."""
    metadata = {
        "model": trained.name,
        "features": list(FEATURES),
        "threshold": metrics.THRESHOLD,
        metrics.KEY: trained.score,
    }
    joblib.dump(trained.pipeline, folder / "model.joblib", compress=3)
    (folder / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return metadata


def log_model(run: wandb.Run, trained: TrainedModel) -> None:
    """Logs the model as an artifact. The sweep and the registry pick the best one by its score."""
    run.summary[metrics.KEY] = trained.score
    run.log({metrics.KEY: trained.score})
    with tempfile.TemporaryDirectory() as folder:
        metadata = save_model(trained, Path(folder))
        artifact = wandb.Artifact(f"model-a-{trained.name}", type="model", metadata=metadata)
        artifact.add_dir(folder)
        run.log_artifact(artifact)


def log_details(run: wandb.Run, splits: Any, y_val: Any, p_val: Any) -> None:
    """Everything a teammate needs to repeat the run (slide "What to log")."""
    run.config.update(
        {
            "metric": metrics.NAME,
            "threshold": metrics.THRESHOLD,
            "split_seed": SEED,
            "model_seed": SEED,
            "features": list(FEATURES),
            "n_train": len(splits.train.y),
            "n_val": len(splits.val.y),
        },
        allow_val_change=True,
    )
    y_true = [int(v) for v in y_val]
    refused = (np.asarray(p_val) >= metrics.THRESHOLD).astype(int)
    run.log(
        {
            "val/recall": recall_score(y_true, refused),
            "val/precision": precision_score(y_true, refused, zero_division=0),
            "val/ap": average_precision_score(y_true, p_val),
            "val/auc": roc_auc_score(y_true, p_val),
            "val/confusion": wandb.plot.confusion_matrix(
                y_true=y_true, preds=refused.tolist(), class_names=["no default", "default"]
            ),
        }
    )
    if Path("uv.lock").exists():
        run.save("uv.lock")
