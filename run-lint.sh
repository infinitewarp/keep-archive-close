#!/bin/bash
# Run linting and formatting checks for keep-archive-close

set -e

echo "Running ruff linter..."
uv run ruff check .

echo ""
echo "Running ruff formatter..."
uv run ruff format --check .

echo ""
echo "All linting checks passed!"
