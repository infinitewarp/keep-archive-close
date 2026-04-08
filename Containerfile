# Build stage
FROM python:3.14-alpine AS builder

# Capture version at build time (git commit hash)
ARG VERSION=dev

WORKDIR /app

# Install build dependencies for Python packages with C extensions
RUN apk add --no-cache gcc musl-dev linux-headers libffi-dev

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies and strip debug symbols
RUN uv sync --frozen --no-dev && \
    find /app/.venv -name "*.so" -exec strip {} \;

# Runtime stage
FROM python:3.14-alpine

WORKDIR /app

# Install runtime dependencies only
RUN apk add --no-cache libffi

# Copy installed dependencies from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code only (not tests, docs, etc.)
COPY app ./app

# Write version file for cache busting
ARG VERSION=dev
RUN echo "$VERSION" > /app/VERSION

EXPOSE 8000

# Python optimizations and use virtual environment directly
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONOPTIMIZE=2

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
