#!/bin/bash
# Quick script to run the app locally without containers

# Install dependencies using uv
echo "Installing dependencies..."
uv sync

# Run the application
echo "Starting keep-archive-close on http://localhost:8000"
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
