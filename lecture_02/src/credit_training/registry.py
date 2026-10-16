"""Model A in the W&B registry: the best model of each kind, and the one the backend loads.

uv run python -m credit_training.registry best logistic-regression
uv run python -m credit_training.registry promote logistic-regression
"""

import argparse
from typing import Final

import wandb

from credit_training import metrics
from credit_training.tracking import project_path

REGISTRY: Final = "wandb-registry-model/model-a"
PRODUCTION: Final = "production"


def best_alias(model: str) -> str:
    return f"best-{model}"


def register_best(model: str) -> None:
    """Links the model of the best run of one kind into the registry, as best-<kind>."""
    api = wandb.Api()
    runs = [
        run
        for run in api.runs(project_path(api), filters={"group": model})
        if metrics.KEY in run.summary
    ]
    if not runs:
        print(f"No {model} run has logged {metrics.KEY} yet, so nothing was registered.")
        return

    pick = max if metrics.GOAL == "maximize" else min
    best = pick(runs, key=lambda run: run.summary[metrics.KEY])
    artifact = next(artifact for artifact in best.logged_artifacts() if artifact.type == "model")
    artifact.link(REGISTRY, aliases=[best_alias(model)])
    print(
        f"{REGISTRY}:{best_alias(model)} is now the model of run {best.name}, "
        f"{metrics.KEY} = {best.summary[metrics.KEY]:.3f}"
    )


def promote(model: str) -> None:
    """Moves the alias production to the best model of one kind."""
    artifact = wandb.Api().artifact(f"{REGISTRY}:{best_alias(model)}", type="model")
    artifact.aliases.append(PRODUCTION)
    artifact.save()
    print(f"{REGISTRY}:{PRODUCTION} is now version {artifact.version}, the best {model}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("action", choices=["best", "promote"])
    parser.add_argument("model")
    arguments = parser.parse_args()
    if arguments.action == "best":
        register_best(arguments.model)
    else:
        promote(arguments.model)


if __name__ == "__main__":
    main()
