# ADSTA_Project

Credit decision backend, the semester project for the ADSTA course at the University of Lucerne. The service takes the data of a loan applicant, estimates the probability of default with a baseline model ("Model A") and returns a decision.

## Team

- Gaspar Federico De Fernandez Herrera, gaspar.defernandez@stud.unilu.ch
- Desmond Okoro, uchenna.okoro@stud.unilu.ch

## Environment and tooling

| | Gaspar | Desmond |
|---|---|---|
| Python | 3.13 | 3.13.15 |
| uv | 0.12.17 | 0.12.15 |
| Git | 2.39.2 | 2.55.0 |

## Prerequisites

Git, [uv](https://docs.astral.sh/uv/) and Docker Desktop. If Python 3.13 is missing, uv installs it.

## Get the code

```bash
git clone https://github.com/Gasppi/ADSTA_Project.git
cd ADSTA_Project/lecture_02
```

The project lives in `lecture_02/`. **Run every command below from this folder.** From the repository root, `uv run` finds no project and the Docker build finds no context.

## Run the service locally

```bash
uv sync
uv run uvicorn credit_backend.main:app --reload --port 8000
```

Open http://localhost:8000/docs. To send a request, open `POST /decisions`, click **Try it out** and then **Execute**. A response with code 200 means the service works. `GET /health` is a quick check that the server is up.

Stop the server with `Ctrl+C`.

## Run the tests

```bash
uv run pytest --cov=credit_backend --cov-fail-under=80
```

This runs all tests and fails if the code coverage drops below 80%. The same command runs in CI.

## Run the container

Docker Desktop must be running.

```bash
docker build -t credit-backend .
docker run --rm -p 8000:8000 credit-backend
```

Open http://localhost:8000/docs, the same page as above. In `-p 8000:8000`, the left number is the port on your computer and the right number is the port inside the container. Stop the container with `Ctrl+C`; `--rm` deletes it.

## Project layout

```
.github/workflows/checks.yml     CI pipeline "checks"
lecture_02/
├── src/credit_backend/
│   ├── main.py                  FastAPI application
│   ├── contracts.py             request and response models
│   └── decisions/
│       ├── dependencies.py      chooses which scorer the service uses
│       ├── features.py          feature vector and feature engineering
│       ├── scoring.py           baseline scorers (Scorer protocol)
│       ├── rules.py             decision policy (threshold)
│       ├── service.py           decision service
│       └── router.py            HTTP endpoints
├── tests/                       pytest tests
├── Dockerfile
├── .dockerignore
├── pyproject.toml
└── uv.lock                      pinned dependencies
```

## Continuous integration

The GitHub Actions workflow `checks` (`.github/workflows/checks.yml`) runs on every pull request and on every push to `main`. It installs the project from `uv.lock` on Python 3.13 and runs the tests with an 80% coverage minimum.

## Troubleshooting

| Problem | Cause and fix |
|---|---|
| `No module named 'fastapi'` or `'credit_backend'` | You are in the wrong folder. Go to `lecture_02` and use `uv run pytest`. |
| `path "lecture_02" not found` when building | You are already inside `lecture_02`. Build with `docker build -t credit-backend .`. |
| `Cannot connect to the Docker daemon` | Docker Desktop is not running. Start it. |
| `port is already allocated` | Another program or container uses port 8000 on your computer. Change the left number, for example `-p 8081:8000`, and open http://localhost:8081/docs. |
| The docs page loads, but a request shows `Failed to fetch` | The server or container has stopped. Start it again. |

## Decision log

### 2026-10-17: Baseline for Model A

**Decision:** the service uses `GasparBaselineScorer`. Gaspar and Desmond compared the two baselines and agreed on this one. `dependencies.py` creates it.

**Why:**
- It uses three features: `debt_ratio`, `revolving_utilisation` and `late_90`. The probability is `0.03 + 0.35 * debt_ratio + 0.25 * revolving_utilisation + 0.18 * late_90`, rounded to four decimals and limited to the range 0 to 1.
- All weights are positive, so a worse figure never lowers the probability, as Task 6 requires.
- A test checks the result against a hand calculation (0.1625 for the sample applicant). The threshold is 0.35.
- Missing inputs fall back to fixed defaults (debt ratio 0.50, utilisation 0.30, `late_90` 0).
- TODO: add how it compared with Desmond's baseline (same applicants, same measure).

**Known limit:**contracts.py only sets lower bounds on late_90 and revolving_utilisation (ge=0). Neither it nor features.py rejects unrealistic values, so a late_90 of 98 (or a utilisation in the thousands) reaches the scorer, which only limits its output to the range 0 to 1. The result saturates at 1.0 and such applicants cannot be told apart. Possible fix: add an upper bound to late_90 in contracts.py (real counts in the training data run from 0 to 17) and reject larger values with a 422 error.

### 2026-10-17: Docker image

- **Base image `python:3.13-slim`.** It matches `requires-python = ">=3.13"` in `pyproject.toml`. With 3.12 in the image, uv has to fetch its own Python. The first build took about 130 s on 3.12 and 51 s on 3.13.
- **Dependencies are installed before the code is copied.** `pyproject.toml` and `uv.lock` are copied and installed first, then `COPY . .`. After a one-line code change, only the last two steps ran again and the build took 2.5 s.
- **`.dockerignore`.** It excludes `.venv`, `.pytest_cache`, `.coverage`, `__pycache__`, `*.pyc`, `.git`, `.gitignore`, `.ruff_cache` and `*.ipynb`. The first two additions came from listing the image (`docker run --rm credit-backend ls -a /app`), which showed `.ruff_cache` and a lecture notebook inside it.
- **`--host 0.0.0.0` in the start command.** Inside a container, `localhost` means the container itself. A server on 127.0.0.1 cannot be reached from the browser through `-p`.

### 2026-10-17: CI

- **The workflow sits at the repository root.** GitHub reads workflows only from `.github/workflows/` at the root. It was first in `lecture_02/` and did not run (the pull request showed 0 checks), so it was moved.
- **It runs on `pull_request` and on `push` to `main`**, with `--cov-fail-under=80`.
- **Open:** Ruff and ty steps in the workflow, and `checks` as a required status check in the GitHub rules.

## Fresh-clone check

2026-10-18, Windows 10 (build 19045), Desmond. Followed this README on a fresh clone of `docs/readme-and-decision-log`. `uv sync` installed 52 packages on Python 3.13.15. `uv run pytest --cov=credit_backend --cov-fail-under=80` gave 9 passed with 96.79% coverage. `docker build` finished in about 6 minutes on `python:3.13-slim`. The container served `/docs`, and `POST /decisions` returned 200 with `default_probability` 0.1625 and `model_version` `gaspar-baseline-v1`. Nothing had to be guessed.
