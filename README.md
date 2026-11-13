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

## Run the whole system with Docker Compose

Docker Desktop must be running. The system has four services: `postgres` (the database), `extraction` (Model B, reads the documents), `ollama` (Model C, words the explanation) and `backend` (the API).

**1. Create your settings file.** Copy the template and fill it in:

```bash
cp .env.example .env
```

| Variable | Value |
|---|---|
| `POSTGRES_USER`, `POSTGRES_DB` | `credit` (already in the template) |
| `POSTGRES_PASSWORD` | A password you choose |
| `DATABASE_URL` | `postgresql+psycopg://credit:YOUR_PASSWORD@postgres:5432/credit`, with the same password |
| `MODEL_B_CHECKPOINT` | `impira/layoutlm-document-qa` |
| `MODEL_B_REVISION` | `beed3c4d02d86017ebca5bd0fdf210046b907aa6` |
| `MODEL_C` | `llama3.2:3b` |
| `MODEL_A`, `WANDB_API_KEY` | Leave `MODEL_A` empty to score with the baseline. `WANDB_API_KEY` is not used while `MODEL_A` is empty. |

`.env` holds secrets. Never commit it or paste it into a chat.

**2. Start everything:**

```bash
docker compose up --build
```

The first start builds the images and downloads Model B, so `extraction` can take several minutes to become healthy. The `backend` starts after the other three report healthy.

**3. Download Model C once.** In a second terminal, in the same folder:

```bash
docker compose exec ollama ollama pull llama3.2:3b
```

**4. Try it.** Open http://localhost:8000/docs. `POST /extractions` reads a document, `POST /decisions` returns a decision and stores it, and `GET /decisions/recent` lists the stored decisions. The extraction service itself is on port 8001.

**5. Stop.** Press `Ctrl+C`, or run `docker compose down`. The database and the downloaded models stay in Docker volumes. `docker compose down -v` deletes those volumes too, so use it only when you want to start from nothing.

**Memory.** On one team machine, the default 4 GB for Docker was not enough for all four services. Give Docker more memory in Docker Desktop, or on Windows in `~/.wslconfig`. If Model C takes longer than 60 seconds to answer, the backend still returns the decision, without the wording, and logs a warning.

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

### 2026-10-31: Model B (reading the documents)

**Decision:** `impira/layoutlm-document-qa`, pinned to revision `beed3c4d02d86017ebca5bd0fdf210046b907aa6`. Both values come from `.env` (`MODEL_B_CHECKPOINT`, `MODEL_B_REVISION`), never from the code.

**Why:**
- It is a LayoutLM model for the Hub task Document Question Answering, as the task hint suggests, and it works with what `reader.py` hands it.
- The revision is pinned because a tag can move, and the same checkpoint must give the same reading.
- A second model was compared on 2026-11-13, see "Comparison" below. The decision stays with this model.

**First run (Task 4):** I sent both sample documents to the extraction service with this model. Both returned 200 (success), so the model loads and reads a document from start to finish. Task 5 then measured it on all 40 applicants (below).

**Metrics** (all 40 sample applicants, `scripts/evaluate_extraction.py`):

| Field | Metric | Result |
|---|---|---|
| gross salary | exact match | 0.900 |
| gross salary | mean absolute error, over the documents that were read | 639.198 CHF |
| open loss certificate | precision and recall | 1.0 and 1.0 |
| applicant name | exact match after case and spaces are normalised | 0.750 |
| date of birth | exact match | 1.0 |
| every field | no-answer rate | 0 |

**Why these metrics:**
- Exact match for the salary, the name and the date of birth, because a figure that is nearly right is still wrong in a loan decision.
- The mean absolute error shows how far off the wrong salaries are.
- Precision and recall for the loss certificate, because it is a rare yes or no. Plain accuracy would hide a missed certificate.

**What they showed:**
- The salary errors occur only in the layouts `coded` and `letterhead` (0.75 each).
- The name is the weakest field: 0.75 overall, and 0.5 in `dense`, 0.625 in `centred` and in `letter`.
- The loss certificate is `nan` for `centred` and `dense`. Those layouts have no open certificate, so there is nothing to measure.
- Because the name is read wrongly in one case of four, a case worker confirms every figure before a decision. The backend never decides on what Model B read.

**Comparison (Task 5, Gaspar, 2026-11-13):** the same 40 applicants and the same script, run on Gaspar's machine. The first column reproduces the numbers above exactly.

| Field | `impira/layoutlm-document-qa` (kept) | `impira/layoutlm-invoices` |
|---|---|---|
| gross, exact match | 0.900 | 0.950 |
| gross, mean absolute error | 639.198 CHF | 162.320 CHF |
| applicant name | 0.750 | 0.950 |
| date of birth | 1.000 | 1.000 |
| open loss certificate, precision and recall | 1.0 and 1.0 | 1.0 and 1.0 |
| no-answer rate | 0 | 0 |

- `layoutlm-invoices` is pinned to `fdf56765f8bdf236b2bd45d23347066475aa730a`. It has the same architecture (`layoutlm`, `LayoutLMForQuestionAnswering`), about 0.1 billion weights and a safetensors file, so it works with `reader.py` unchanged.
- It improves the layouts that failed: `coded` gross 0.750 to 0.875 (error 2236.6 to 61.6 CHF), `letterhead` gross 0.750 to 0.875 (error 959.4 to 750.0 CHF), and the names in `centred` and `dense` (0.625 and 0.500 to 1.000). The names in `letter` rise from 0.625 to 0.750. One document moves a layout by 0.125, so single layouts are noisy, but the overall name gain is large.
- **Licences:** `layoutlm-document-qa` is MIT. `layoutlm-invoices` is `cc-by-nc-sa-4.0` (non-commercial, share-alike), which would block a commercial deployment.

**Decision:** the team keeps `impira/layoutlm-document-qa`. It is the model already in the project, its MIT licence has no use restriction, and a case worker confirms every figure before a decision. `layoutlm-invoices` reads better on this data and is the first candidate if its licence is acceptable.

### 2026-10-31: Model C (wording)

**Decision:** `llama3.2:3b`, run by Ollama. The tag comes from `MODEL_C`.

**Why:**
- It has 3 billion weights, inside the 1 to 4 billion that the task names, and its download is 2.0 GB (source: the list at https://needtoknowit.com.au/blog/best-ollama-models-to-download.md).
- No other model is compared. `qwen2.5:3b` (1.9 GB) is the fallback.

**Prompt:**
- The system prompt tells Model C to use only the reasons it receives, to add no names, figures, dates, advice or promises, and never to change, question or soften the outcome. It answers as JSON with one field, `text`.
- The user prompt carries the outcome and the reasons and nothing else, for example `outcome "refused", reasons ["loss_certificate_open"]`.
- The answer is validated with `Worded`, which forbids extra fields. Anything else counts as no wording.

**Options:** `temperature` 0 and `seed` 42, so that the same decision gets the same wording. `num_predict` 120 stops a long answer. `num_ctx` 2048 keeps the memory small.

**Result (Gaspar, 2026-11-08, Mac with 8 GB, Docker limit 7.75 GiB, CPU only):**
- Ollama showed `llama3.2:3b` at 2.9 GB, 100% CPU. With extraction running and swap nearly full (16.4 of 17.4 GB), the first cold load took about 2.5 minutes and generation ran at 0.46 tokens per second.
- After stopping extraction, generation rose to 5.04 tokens per second. A cold load still took 90 seconds to 3 minutes, longer than the 60 s timeout.
- Six decisions in a row timed out (`No wording from llama3.2:3b: ReadTimeout`) after the model had been loaded with `ollama run`, whose context is 4096. After loading it with the backend's own `num_ctx` of 2048, the wording arrived. A context mismatch fits this, but memory pressure also changed, so it is the likely cause and not a proven one.
- Each timed-out decision still returned 200 and was stored without wording, as Task 7e asks.
- Ollama needs the model loaded and free memory, so on an 8 GB machine run Model B and Model C one at a time.

**Prompt fix (PR #24).** The first wordings called an open loss certificate "a loss of certificate", which reads as a lost document. The system prompt now explains each reason code.

| Reason | Before | After |
|---|---|---|
| `loss_certificate_open` | "refused due to a loss of certificate" | "refused due to an outstanding loss certificate" |
| `default_probability_above_threshold` | "...a default probability above the threshold" | "...above the accepted limit" |
| `income_unknown` | "...unknown income" | "...unknown monthly income" |
| `loss_certificate_unknown` | "...an unknown loss certificate" | "...unknown debt records" |

A longer meaning for `loss_certificate_unknown` fixed that last wording but made the open case say the certificate "could not be read". The two meanings are too close for a 3B model, so the shorter version stayed. `qwen2.5:3b` was not tried.

### 2026-10-31: Backend (Task 7)

- **7a, rules.** An open loss certificate refuses (`LOSS_CERTIFICATE_OPEN`). A loss certificate nobody could read refuses with its own reason (`LOSS_CERTIFICATE_UNKNOWN`), and so does an income nobody could read (`INCOME_UNKNOWN`). An unreadable value is not a clean one, and every refusal names its reason, so a case worker can check and correct the figure. Every reason refuses, so `decide` stays unchanged. The boundary test (0.29, 0.30, 0.31) from lecture 2 is kept and updated.
- **7b, database.** The URL comes from `DATABASE_URL`, with no default, because it carries a password. Inside Compose the host is `postgres`.
- **7c, table.** One row for every decision: the six features named like `FeatureVector`, `has_loss_certificate`, `extraction_checkpoint`, `default_probability`, `model_version`, `outcome`, `reasons` (JSON), `wording`. An unknown value is `NULL`, never 0. My first version used wrong feature names, and `POST /decisions` answered 500 (`'dependents' is an invalid keyword argument`). The unit tests had not stored a real feature vector. `tests/test_record_features.py` now does.
- **7d, service.** After the rules, Model C words the decision, but only if `MODEL_C` is set. Then the row is stored, and the answer carries its id as `record_id`.
- **7e, timeouts.** The extraction service gets connect 5 s, read 180 s, write 30 s, pool 5 s, and no retry: a second try would double the wait, and the case worker can send the documents again. Any failure (no answer, too late, error status, unexpected answer) becomes a 503 with a clear message. Ollama gets 60 s. If it is down, too slow or has no model, the decision goes on without wording, and a warning names the cause. The 180 s and 60 s are my choices and are not measured.
- **Checks run by Gaspar (2026-11-08 to 2026-11-13).** `GET /decisions/recent` lists the stored decisions, with `NULL` for unknown values. With Ollama stopped, `POST /decisions` returns 200 without wording and logs `ConnectionError`. With extraction stopped, `POST /extractions` through the backend answers 503. Decisions survive `docker compose down` and `up` (without `-v`).

### 2026-10-31: Compose and images

- **Health checks and order.** Every service has a health check, and the backend starts only when `postgres`, `extraction` and `ollama` are healthy. The extraction service gets 600 s to start, because Model B is downloaded at the first start. The `postgres` check got 120 s and 30 retries, because on a slow disk the first start took about 80 s, and Compose had declared it unhealthy too early.
- **Secrets.** All come from `.env`. The compose file stops with a message if one is missing.
- **`.dockerignore`.** It now excludes `.env` and `extraction_service`. Before, the backend build context was 774.59 MB and the image would have contained `.env` with the passwords. Now it is 1.98 MB.
- **Missing package.** The README's `uv add` list does not include `python-multipart`, which the upload endpoint needs. We added it.
- **Memory.** On an 8 GB laptop Docker got 4 GB by default. Raising it to 6 GB left Windows with 1.2 GB free, and everything slowed down. The services need less than 1 GB, plus about 2.5 GB when Model C is loaded.

## Fresh-clone check

2026-10-18, Windows 10 (build 19045), Desmond. Followed this README on a fresh clone of `docs/readme-and-decision-log`. `uv sync` installed 52 packages on Python 3.13.15. `uv run pytest --cov=credit_backend --cov-fail-under=80` gave 9 passed with 96.79% coverage. `docker build` finished in about 6 minutes on `python:3.13-slim`. The container served `/docs`, and `POST /decisions` returned 200 with `default_probability` 0.1625 and `model_version` `gaspar-baseline-v1`. Nothing had to be guessed.