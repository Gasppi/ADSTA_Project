# ADSTA_Project

#Team members -> Gaspar Federico De Fernandez Herrera - gaspar.defernandez@stud.unilu.ch / Desmond Okoro - uchenna.okoro@stud.unilu.ch

## Environment & Tooling

Gaspar:
- Python version: 3.13
- uv version: 0.12.17
- Git version: 2.39.2

Desmond:
- Python version: 3.13.15
- uv version: 0.12.15
- Git version: 2.55.0

---

##  Task 10: Local Setup & Development Instructions

### 1. Install Dependencies
```bash
uv sync
```

### 2. Run Tests & Coverage Verification
Run unit tests across the codebase:
```bash
uv run pytest
```

Verify that code coverage meets the mandatory 80% threshold:
```bash
uv run pytest --cov=credit_backend --cov-fail-under=80
```

### 3. Run Local Server
```bash
uv run uvicorn credit_backend.main:app --reload --port 8000
```
Access the interactive documentation at `http://localhost:8000/docs`.

---

##  Docker Deployment

### 1. Build Container Image
```bash
docker build -t credit-backend .
```

### 2. Run Container
```bash
docker run -p 8000:8000 credit-backend
```

---

## 📝 Task 11: Decision Log

### Baseline Scorer Selection
- **Decision:** Implemented `GasparBaselineScorer` using `revolving_utilisation`, `debt_ratio`, and `late_90`.
- **Rationale:** Revolving credit utilization and past severe delinquency (`late_90`) are stronger financial indicators of credit risk compared to static demographic metrics like the number of dependents.

### Containerization & CI Strategy
- **Multi-Stage Docker Layer Caching:** Separated dependency sync (`COPY pyproject.toml uv.lock ./` + `RUN uv sync --frozen --no-install-project`) from code copying to optimize Docker layer caching and reduce build times during local development and CI runs.
- **Continuous Integration Pipeline:** Configured GitHub Actions (`.github/workflows/checks.yml`) to enforce automated testing and a strict 80% minimum coverage policy on every pull request.

### 2026-10-31: Model B (reading the documents)

**Decision:** `impira/layoutlm-document-qa`, pinned to revision `beed3c4d02d86017ebca5bd0fdf210046b907aa6`. Both values come from `.env` (`MODEL_B_CHECKPOINT`, `MODEL_B_REVISION`), never from the code.

**Why:**
- It is a LayoutLM model for the Hub task Document Question Answering, as the task hint suggests, and it works with what `reader.py` hands it.
- The revision is pinned because a tag can move, and the same checkpoint must give the same reading.
- TODO (Desmond): no other model is compared in this entry. If one was tried, add its scores here.

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

**Result so far (not yet verified):** the wording itself has not been seen. On Desmond's laptop the first call timed out after 60 s (`No wording from llama3.2:3b: ReadTimeout`). The decision still came back with code 200 and was stored, without wording. At that moment 1.2 GB of the 8 GB were free (`systeminfo`), and Docker had read only 1.12 GB of the model in 30 minutes. TODO (Gaspar): run it on a machine with enough memory and add the first wordings here.

### 2026-10-31: Backend (Task 7)

- **7a, rules.** An open loss certificate refuses (`LOSS_CERTIFICATE_OPEN`). A loss certificate nobody could read refuses with its own reason (`LOSS_CERTIFICATE_UNKNOWN`), and so does an income nobody could read (`INCOME_UNKNOWN`). An unreadable value is not a clean one, and every refusal names its reason, so a case worker can check and correct the figure. Every reason refuses, so `decide` stays unchanged. The boundary test (0.29, 0.30, 0.31) from lecture 2 is kept and updated.
- **7b, database.** The URL comes from `DATABASE_URL`, with no default, because it carries a password. Inside Compose the host is `postgres`.
- **7c, table.** One row for every decision: the six features named like `FeatureVector`, `has_loss_certificate`, `extraction_checkpoint`, `default_probability`, `model_version`, `outcome`, `reasons` (JSON), `wording`. An unknown value is `NULL`, never 0. My first version used wrong feature names, and `POST /decisions` answered 500 (`'dependents' is an invalid keyword argument`). The unit tests had not stored a real feature vector. `tests/test_record_features.py` now does.
- **7d, service.** After the rules, Model C words the decision, but only if `MODEL_C` is set. Then the row is stored, and the answer carries its id as `record_id`.
- **7e, timeouts.** The extraction service gets connect 5 s, read 180 s, write 30 s, pool 5 s, and no retry: a second try would double the wait, and the case worker can send the documents again. Any failure (no answer, too late, error status, unexpected answer) becomes a 503 with a clear message. Ollama gets 60 s. If it is down, too slow or has no model, the decision goes on without wording, and a warning names the cause. The 180 s and 60 s are my choices and are not measured.

### 2026-10-31: Compose and images

- **Health checks and order.** Every service has a health check, and the backend starts only when `postgres`, `extraction` and `ollama` are healthy. The extraction service gets 600 s to start, because Model B is downloaded at the first start. The `postgres` check got 120 s and 30 retries, because on a slow disk the first start took about 80 s, and Compose had declared it unhealthy too early.
- **Secrets.** All come from `.env`. The compose file stops with a message if one is missing.
- **`.dockerignore`.** It now excludes `.env` and `extraction_service`. Before, the backend build context was 774.59 MB and the image would have contained `.env` with the passwords. Now it is 1.98 MB.
- **Missing package.** The README's `uv add` list does not include `python-multipart`, which the upload endpoint needs. We added it.
- **Memory.** On an 8 GB laptop Docker got 4 GB by default. Raising it to 6 GB left Windows with 1.2 GB free, and everything slowed down. The services need less than 1 GB, plus about 2.5 GB when Model C is loaded.
