#!/bin/bash
# Run unit tests for keep-archive-close

set -e

echo "Running tests..."
uv run pytest -v

echo ""
echo "All tests passed!"
