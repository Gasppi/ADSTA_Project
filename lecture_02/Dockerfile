# Task 7: the Dockerfile for your backend service, ported from the slide.
# The slide follows uv's Docker guide, https://docs.astral.sh/uv/guides/integration/docker/
FROM python:3.12-slim

# Copia los binarios de uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# 1. Copiar primero solo los archivos de dependencias
COPY pyproject.toml uv.lock ./

# 2. Instalar dependencias (esta capa quedará cacheada si los paquetes no cambian)
RUN uv sync --frozen --no-install-project

# 3. Copiar el resto del código del proyecto
COPY . .
RUN uv sync --frozen

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "credit_backend.main:app", "--host", "0.0.0.0", "--port", "8000"]