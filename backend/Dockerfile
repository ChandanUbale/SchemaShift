FROM python:3.12-slim

WORKDIR /app

# Install system deps (pymysql needs no C extensions; keep image lean)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# --only-binary :all: ensures pydantic-core uses its pre-built cp313 wheel
# (avoids Rust compilation, which would require cargo + build-essential)
RUN pip install --no-cache-dir --only-binary :all: -r requirements.txt

COPY . .

EXPOSE 8000

# WORKDIR is /app; uvicorn runs from /app so pydantic-settings finds .env
# at /app/.env — compose.yml injects it via `env_file: .env` at repo root.
# Base image is python:3.12-slim; pydantic 2.13.5 ships cp312 binary wheels
# so no Rust/cargo compilation is needed during docker build.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
