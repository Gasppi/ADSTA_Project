FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1
COPY --from=ghcr.io/astral-sh/uv:0.12.17 /uv /bin/uv

WORKDIR /app
COPY pyproject.toml uv.lock* ./
RUN uv sync --no-dev --no-install-project
COPY src src
RUN uv sync --no-dev

# BACKEND_URL, EXTRACTION_TIMEOUT_SECONDS and DECISION_TIMEOUT_SECONDS come from Compose.
# The page has no default for them.
EXPOSE 8501
CMD ["uv", "run", "--no-sync", "streamlit", "run", "src/credit_frontend/app.py", "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true", "--browser.gatherUsageStats=false"]
