#!/bin/bash
# Build and run the app with Podman

echo "Building container..."
podman build -t keep-archive-close .

echo "Starting keep-archive-close on http://localhost:8000"
podman run --rm -p 8000:8000 keep-archive-close
