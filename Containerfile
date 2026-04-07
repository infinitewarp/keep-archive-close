# Build stage
FROM python:3.14-alpine AS builder

WORKDIR /app

# Install build dependencies for Python packages with C extensions
RUN apk add --no-cache gcc musl-dev linux-headers libffi-dev

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Runtime stage
FROM python:3.14-alpine

WORKDIR /app

# Install runtime dependencies only
RUN apk add --no-cache libffi

# Copy uv binary
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy installed dependencies from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code only (not tests, docs, etc.)
COPY app ./app

EXPOSE 8000

# Use virtual environment directly
ENV PATH="/app/.venv/bin:$PATH"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
