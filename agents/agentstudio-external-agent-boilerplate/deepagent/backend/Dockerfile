FROM python:3.13-slim-bookworm AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    build-essential \
    gcc \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Build with repository root as context so shared SDK sources are available.
COPY backend/pyproject.toml /app/backend/pyproject.toml
RUN python -m venv /app/.venv && \
    /app/.venv/bin/python -m pip install --upgrade pip setuptools wheel && \
    /app/.venv/bin/python -m pip install --no-cache-dir /app/backend

COPY agentstudio-sdk/ /app/agentstudio-sdk/
RUN /app/.venv/bin/python -m pip install --no-cache-dir /app/agentstudio-sdk

COPY backend/src/ /app/src/

FROM python:3.13-slim-bookworm

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src

ENV PATH="/app/.venv/bin:$PATH" \
    VIRTUAL_ENV="/app/.venv" \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH="/app/src:/app"

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--loop", "uvloop"]
