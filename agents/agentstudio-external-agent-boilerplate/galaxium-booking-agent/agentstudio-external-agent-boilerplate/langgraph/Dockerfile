FROM python:3.13-slim-bookworm AS builder

WORKDIR /app

# Install uv from official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy lock files and metadata first (layer caching)
COPY backend/pyproject.toml backend/uv.lock /app/backend/
COPY agentstudio-sdk/pyproject.toml agentstudio-sdk/uv.lock /app/agentstudio-sdk/

# Install dependencies
RUN cd /app/backend && uv sync --frozen --no-dev

# Install SDK as non-editable package with its dependencies
RUN cd /app/backend && uv pip install /app/agentstudio-sdk

# Copy source code (separate layer for better caching)
COPY backend/src/ /app/backend/src/
COPY agentstudio-sdk/src/ /app/agentstudio-sdk/src/

FROM python:3.13-slim-bookworm

WORKDIR /app/backend

# Copy venv and source from builder
COPY --from=builder /app/backend/.venv /app/backend/.venv
COPY --from=builder /app/backend/src /app/backend/src
COPY --from=builder /app/agentstudio-sdk/src /app/agentstudio-sdk/src

# Environment configuration
ENV PATH="/app/backend/.venv/bin:$PATH" \
    VIRTUAL_ENV="/app/backend/.venv" \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH="/app/backend/src:/app/agentstudio-sdk/src" \
    HOME=/tmp

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--loop", "uvloop"]
