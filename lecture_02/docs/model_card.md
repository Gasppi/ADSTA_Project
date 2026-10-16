---
model: model-a
registry: wandb-registry-model/model-a
version: <v n, the version that carries the alias production>
run: <the name of the run that trained it>
commit: <the commit of the training code>
---

<!-- Task 9: replace every placeholder in angle brackets. -->

# Model A: probability of default

## Intended use

<Who uses the score, for which decision, and what it must not be used for.>

## Data

<The source, the number of rows, the cleaning steps and the split.>

## Metric

<Your metric>, because <your reason>.

## Threshold

0.5 for every team. <The share of applicants your model refuses at it.>

## Results

<Validation and test scores, next to the baseline.>

<The same results per group, for example per age band.>

## Limitations

<Where the model is weak, and what it has never seen.>

## Contact

<Your team, and the date of this card.>
