"""Model A as a random forest.

uv run python -m credit_training.random_forest
"""

from typing import Any, Final

from credit_training.tracking import TrainedModel

NAME: Final = "random-forest"
# Task 5: the settings your forest starts from.
PARAMS: Final[dict[str, Any]] = {}


def train(params: dict[str, Any] | None = None) -> TrainedModel:
    """Trains one random forest on the training set and judges it on the validation set."""
    # Task 5: train the forest, compute your metric and track the run, as the logistic regression
    # does. Return a TrainedModel and log it with log_model, so the sweep and the registry find it.
    raise NotImplementedError("Task 5: train the random forest")


if __name__ == "__main__":
    train()
