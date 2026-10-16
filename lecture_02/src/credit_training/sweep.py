"""Sweeps the settings of one model, then registers the best model found so far.

uv run python -m credit_training.sweep logistic-regression --runs 20 --method bayes
"""

import argparse
from types import ModuleType
from typing import Any, Final

import wandb

from credit_training import logistic_regression, metrics, random_forest
from credit_training.registry import register_best
from credit_training.tracking import ENTITY, PROJECT

MODELS: Final[dict[str, ModuleType]] = {
    module.NAME: module for module in (logistic_regression, random_forest)
}

# Task 6: the settings each sweep searches, written as on the slide "Hyperparameter Sweeps".
# Name only settings that the model's PARAMS has, so that the training reads them.
SEARCH_SPACES: Final[dict[str, dict[str, Any]]] = {
    logistic_regression.NAME: {},
    random_forest.NAME: {},
}


def sweep(model: str, runs: int, method: str) -> None:
    parameters = SEARCH_SPACES[model]
    if not parameters:
        raise SystemExit(f"Task 6: add the settings to search for {model} to SEARCH_SPACES.")

    config = {
        "name": model,
        "method": method,
        "metric": {"name": metrics.KEY, "goal": metrics.GOAL},
        "parameters": parameters,
    }
    sweep_id = wandb.sweep(config, entity=ENTITY, project=PROJECT)
    wandb.agent(sweep_id, function=MODELS[model].train, entity=ENTITY, project=PROJECT, count=runs)
    register_best(model)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("model", choices=MODELS)
    parser.add_argument("--runs", type=int, default=20)
    parser.add_argument("--method", choices=["grid", "random", "bayes"], default="bayes")
    arguments = parser.parse_args()
    sweep(arguments.model, arguments.runs, arguments.method)


if __name__ == "__main__":
    main()
