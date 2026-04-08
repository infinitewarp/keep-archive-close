# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## ⚠️ CRITICAL: ALWAYS CHECK YOUR BRANCH FIRST ⚠️

**BEFORE YOU START ANY WORK, RUN THIS COMMAND:**

```bash
git branch --show-current
```

**IF THE OUTPUT IS `main`, YOU MUST CREATE A FEATURE BRANCH:**

```bash
git checkout -b feature/descriptive-name
```

### Why This Matters

- ❌ **NEVER COMMIT DIRECTLY TO `main`**
- ❌ The `main` branch is protected and requires pull requests
- ❌ Direct commits to `main` violate the repository workflow
- ✅ All changes MUST go through feature branches and PRs

### Pre-Work Checklist

Before making ANY code changes, verify:

- [ ] Ran `git branch --show-current` to check current branch
- [ ] If on `main`, created a feature branch with `git checkout -b feature/name`
- [ ] Ready to commit to feature branch (NOT main)

**If you accidentally commit to `main`, you must move the commits to a feature branch before pushing.**

---

## Project Overview

keep-archive-close is a single-purpose multi-user web application for quick decision-making. It provides an interface where multiple participants can simultaneously vote on items using three options: "keep", "archive", or "close". A customizable countdown timer (default 15 seconds, adjustable 1-999) enforces time pressure, encouraging participants to make gut-check assessments without over-analyzing details. Users personalize their experience with custom names and colors that persist across sessions.

## Architecture

**Backend:** FastAPI with WebSocket support
- Async Python application using FastAPI framework
- Real-time bidirectional communication via WebSockets
- In-memory session state management (no external state store needed)
- Lightweight resource usage (~50-100MB)

**Frontend:** Server-side rendered HTML with minimal JavaScript
- Jinja2 templates served by FastAPI
- Vanilla JavaScript for WebSocket handling
- No build step or heavy frontend framework
- CSS with variable-based theming (gradient background, card-based UI)
- Automatic dark mode via `prefers-color-scheme` media query
- Automatic cache busting for CSS via version query parameter (updates with each deployment)

**Session Management:**
- Sessions identified by UUID (pseudo-anonymous, not security-focused)
- In-memory tracking via `SessionManager` and `VotingSession` classes
- User data stored in cookies (name, color) for clean shareable URLs
- User preferences also persisted in localStorage as fallback
- Automatic cleanup when all users leave a session
- 30-second inactivity timeout with heartbeat mechanism

**Real-time Updates:**
- WebSocket endpoint at `/ws/{session_id}`
- Broadcasts: user join/leave, vote state, timer updates, results
- Client-side heartbeat every 5 seconds to maintain presence
- Automatic reconnection on disconnect

## Key Components

- `app/main.py` - FastAPI application, routes, WebSocket endpoint, broadcast logic
  - Reads `VERSION` file at startup for static file cache busting
- `app/models.py` - Session state classes (`VotingSession`, `User`, `VotingRound`, `SessionManager`)
- `app/templates/` - Jinja2 HTML templates (landing page, voting page)
  - Templates include version parameter in CSS links: `style.css?v={{ version }}`
- `app/static/style.css` - CSS styling with CSS custom properties for theming
  - All colors defined as variables at top of file for easy customization
  - Dark mode overrides using `@media (prefers-color-scheme: dark)`
- `pyproject.toml` - Project metadata and dependencies (managed by uv)
- `uv.lock` - Locked dependency versions for reproducible installs
- `VERSION` - Version identifier for cache busting (created at build time, contains git commit SHA)
  - In containers: git SHA from build time (e.g., `9f0c320...`)
  - Local development: falls back to `"dev"` if file doesn't exist
- `Containerfile` - Multi-stage Alpine-based container build
  - **Build stage:** Compiles dependencies with build tools
  - **Runtime stage:** Minimal runtime with only necessary packages
  - **Size:** ~68MB (74% smaller than original)
  - **Optimizations:** Multi-stage build, Alpine Linux base, stripped binaries, explicit dependencies
  - **Cache busting:** Captures git SHA via build arg and writes to VERSION file

## Git Workflow

### Branch Protection Rules

**The `main` branch is protected.** You cannot push commits directly to it.

### Complete Workflow

**1. ALWAYS start by checking your branch:**
```bash
git branch --show-current
```

**2. If on `main`, create a feature branch BEFORE making changes:**
```bash
git checkout -b feature/descriptive-name
```

**3. Make your changes and commit to the feature branch:**
```bash
git add <files>
git commit -m "Description of changes"
```

**4. Push the feature branch:**
```bash
git push -u origin feature/descriptive-name
```

**5. Create a pull request:**
```bash
gh pr create --title "Title" --body "Description"
```

**6. After PR is approved and CI passes, merge with rebase:**
```bash
gh pr merge <number> --rebase --delete-branch
```

### Branch Naming Conventions

- Feature branches: `feature/descriptive-name`
- Bug fixes: `fix/descriptive-name`
- Documentation: `docs/descriptive-name`

### Merge Strategy

- **Rebase only**: The repository is configured to only allow rebase merges (no merge commits or squashing)
- This maintains a **linear history** without merge commits
- Feature branches are automatically deleted after merge
- When merging PRs: `gh pr merge <number> --rebase --delete-branch`

### Recovery: If You Accidentally Commit to `main`

If you realize you committed to `main` before pushing:

```bash
# Create a branch at current commit
git branch feature/your-feature-name

# Reset main to remote state
git reset --hard origin/main

# Switch to feature branch
git checkout feature/your-feature-name

# Push feature branch and create PR
git push -u origin feature/your-feature-name
```

**Never commit directly to `main`.** All changes must go through pull requests to ensure CI checks pass and maintain code quality.

## Development Commands

**Run locally (recommended for development):**
```bash
./run-local.sh
```

**Run with Podman:**
```bash
./run-container.sh
```

Or manually with local build:
```bash
podman build -t keep-archive-close .
podman run --rm -p 8000:8000 keep-archive-close
```

Or use pre-built multi-arch image from GitHub Container Registry:
```bash
podman pull ghcr.io/infinitewarp/keep-archive-close:latest
podman run --rm -p 8000:8000 ghcr.io/infinitewarp/keep-archive-close:latest
```

**Run manually (local Python):**
```bash
uv sync
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Access at: http://localhost:8000

## Reverse Proxy Deployment

**Running behind nginx with subpath:**

The application supports deployment under a subpath (e.g., `example.com/kac`) via the `ROOT_PATH` environment variable.

**Example nginx configuration:**
```nginx
location /kac {
    # Pass requests to the container
    proxy_pass http://localhost:8000;
    
    # Standard proxy headers
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    
    # WebSocket support (required for real-time updates)
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    
    # Timeouts for WebSocket connections
    proxy_read_timeout 86400;
    proxy_send_timeout 86400;
}
```

**Run container with ROOT_PATH:**
```bash
podman run -e ROOT_PATH=/kac -p 8000:8000 ghcr.io/infinitewarp/keep-archive-close:latest
```

**Docker Compose example:**
```yaml
services:
  keep-archive-close:
    image: ghcr.io/infinitewarp/keep-archive-close:latest
    environment:
      - ROOT_PATH=/kac
    ports:
      - "8000:8000"
```

The app will then be accessible at `example.com/kac/` and all URLs, WebSocket connections, and redirects will work correctly.

## Testing

**Run unit tests:**
```bash
./run-tests.sh
```

Or manually:
```bash
uv sync --extra dev
uv run pytest
```

**Test configuration:**
- Test framework: pytest with pytest-asyncio
- Test timeout: 5 seconds (configured globally to prevent hangs)
- Test coverage: models (VotingSession, SessionManager), API endpoints, WebSocket functionality, subpath deployment
- Test organization: `tests/test_models.py`, `tests/test_api.py`, `tests/test_websocket.py`, `tests/test_subpath.py`

**Run specific tests:**
```bash
uv run pytest tests/test_models.py  # Model tests only
uv run pytest tests/test_api.py     # API endpoint tests only
uv run pytest -v                     # Verbose output
uv run pytest -k test_name           # Run specific test by name
```

## Code Quality & CI

**Linting and formatting:**
```bash
./run-lint.sh  # Check linting and formatting
```

Or manually:
```bash
uv run ruff check .          # Run linter
uv run ruff check --fix .    # Auto-fix linting issues
uv run ruff format .         # Format code
uv run ruff format --check . # Check formatting without changing files
```

**Linting configuration:**
- Tool: ruff 0.15.9 (fast Rust-based linter and formatter)
- Line length: 100 characters
- Target: Python 3.14
- Enabled rules: pycodestyle, pyflakes, isort, pep8-naming, pyupgrade, flake8-bugbear, flake8-comprehensions, flake8-simplify
- Modern type hints: Uses `X | None` instead of `Optional[X]`, `dict/list/set` instead of `Dict/List/Set`

**GitHub Actions CI:**
- Runs automatically on all pull requests (required for merge to main)
- All checks must pass before PR can be merged
- Checks: Linting (ruff check), formatting (ruff format), unit tests (pytest), syntax validation, import checks, app startup, container build
- Workflow files: 
  - `.github/workflows/ci.yml` - Code quality and tests
  - `.github/workflows/container-build.yml` - Multi-arch container build and publish
    - **On PRs:** Builds for amd64 and arm64 to verify (no push)
    - **On main:** Builds and pushes to GitHub Container Registry (ghcr.io)
    - **Tags:** `latest` (main branch), `sha-<commit>` (all builds)
  - `.github/workflows/cleanup-old-images.yml` - Container image retention
    - **Runs:** Weekly (Sundays at 00:00 UTC) or manual trigger
    - **Keeps:** `latest` tag + most recent 10 sha-tagged images
    - **Deletes:** Older sha-tagged images to prevent accumulation
    - **Configurable:** Adjust `KEEP_RECENT` env var to change retention count

**Manual syntax check:**
```bash
uv run python -m py_compile app/__init__.py app/main.py app/models.py
```

**Verify imports:**
```bash
uv run python -c "from app import main, models"
```

## Key Behaviors

1. **User Flow**: Name + color selection → Create/join session → Real-time voting interface
   - User data stored in cookies and localStorage (persists across sessions)
   - Clean URLs without user data for easy sharing
   - Automatic name prompt if joining via shared URL without prior session
2. **Voting Round**: Any user starts vote → Custom countdown (1-999s) → Buttons enable → Vote or abandon → Timer ends → Results display → Ready for next vote
   - "Start New Vote" button changes to "Abandon Vote" (red) during active voting
   - Abandon resets vote state without showing results
   - After results display, button returns to "Start New Vote" for continuous voting
   - Selected vote button shows distinctive border highlight
   - Timer duration syncs across all clients when vote starts
3. **User Personalization**: 
   - Each user has a color (color picker on landing page and in session)
   - Participant list shows colored left border for each user
   - Click name to rename, click color picker to change color
   - All changes broadcast to other users in real-time
4. **Vote State Tracking**: Users are "dimmed" in participant list until they vote
5. **Session Lifecycle**: Auto-created on first user → Auto-deleted when last user leaves
6. **Presence Detection**: Heartbeat every 5s, cleanup every 10s, 30s timeout

## Configuration

**Environment Variables:**

- `ROOT_PATH` - Subpath for reverse proxy deployment (default: `""` for root)
  - Set to `/kac` to serve app at `example.com/kac` instead of `example.com/`
  - Used when running behind nginx/Apache reverse proxy with subpath routing
  - No need to rebuild container - configured at deployment time
  - Example: `podman run -e ROOT_PATH=/kac -p 8000:8000 keep-archive-close`

**Build-time Configuration:**

- Static file cache busting: Automatically versioned via VERSION file
  - Container builds: VERSION file created with git commit SHA from build arg
  - Local development: Falls back to "dev" when VERSION file absent
  - CSS links include version: `/static/style.css?v={version}`
  - No manual intervention needed - updates automatically with each build

**Application Settings:**

- Vote timer duration: Customizable per vote (1-999 seconds), default 15
  - User-adjustable input on voting page (disabled during active vote)
  - Duration stored in `VotingRound.duration` and synced to all clients
  - Fallback constant: `VOTE_DURATION = 15` in `app/main.py`
- Heartbeat interval: 5 seconds (client-side in `voting.html`)
- Cleanup interval: 10 seconds (server-side in `app/main.py`)
- Inactivity timeout: 30 seconds (configurable in `app/models.py`)
- Cookie expiration: 30 days (user name and color)

## Design Constraints

- **Local team use**: Not designed for high-scale or geographically distributed users
- **No persistence**: Session state is in-memory; server restart clears all sessions
- **No authentication**: Sessions use UUID obscurity, not security
- **Single container**: Everything runs in one Podman container for simplicity
- **Dependency management**: Uses `uv` for fast, reproducible Python dependency installation
