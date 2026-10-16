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

## 🛠️ Task 10: Local Setup & Development Instructions

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

## 🐳 Docker Deployment

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

### Baseline Scorer Selection (Task 6)
- **Decision:** Implemented `GasparBaselineScorer` using `revolving_utilisation`, `debt_ratio`, and `late_90`.
- **Rationale:** Revolving credit utilization and past severe delinquency (`late_90`) are stronger financial indicators of credit risk compared to static demographic metrics like the number of dependents.

### Containerization & CI Strategy (Tasks 7–9)
- **Multi-Stage Docker Layer Caching:** Separated dependency sync (`COPY pyproject.toml uv.lock ./` + `RUN uv sync --frozen --no-install-project`) from code copying to optimize Docker layer caching and reduce build times during local development and CI runs.
- **Continuous Integration Pipeline:** Configured GitHub Actions (`.github/workflows/checks.yml`) to enforce automated testing and a strict 80% minimum coverage policy on every pull request.
