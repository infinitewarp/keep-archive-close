#!/bin/bash
# Build and run the app with Podman

# Get git commit hash for cache busting (fallback to "dev" if not in git repo)
VERSION=$(git rev-parse HEAD 2>/dev/null || echo "dev")

echo "Building container (version: $VERSION)..."
podman build --build-arg VERSION="$VERSION" -t keep-archive-close .

echo "Starting keep-archive-close on http://localhost:8000"
podman run --rm -p 8000:8000 keep-archive-close
