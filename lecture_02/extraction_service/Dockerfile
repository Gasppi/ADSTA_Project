FROM python:3.13-slim

# Model B is downloaded into /models at the first start. Mount a volume there, so that
# it is downloaded once and not on every start.
ENV PYTHONUNBUFFERED=1 \
    HF_HOME=/models
COPY --from=ghcr.io/astral-sh/uv:0.12.17 /uv /bin/uv

WORKDIR /app
COPY pyproject.toml uv.lock* ./
RUN uv sync --no-dev --no-install-project
COPY src src
RUN uv sync --no-dev

EXPOSE 8000
CMD ["uv", "run", "--no-sync", "uvicorn", "credit_extraction.main:app", "--host", "0.0.0.0", "--port", "8000"]
