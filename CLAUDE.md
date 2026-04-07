# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

keep-archive-close is a single-purpose multi-user web application for quick decision-making. It provides an interface where multiple participants can simultaneously vote on items using three options: "keep", "archive", or "close". A brief countdown timer (15 seconds) enforces time pressure, encouraging participants to make gut-check assessments without over-analyzing details.

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
- CSS for styling (gradient background, card-based UI)

**Session Management:**
- Sessions identified by UUID (pseudo-anonymous, not security-focused)
- In-memory tracking via `SessionManager` and `VotingSession` classes
- Automatic cleanup when all users leave a session
- 30-second inactivity timeout with heartbeat mechanism

**Real-time Updates:**
- WebSocket endpoint at `/ws/{session_id}`
- Broadcasts: user join/leave, vote state, timer updates, results
- Client-side heartbeat every 5 seconds to maintain presence
- Automatic reconnection on disconnect

## Key Components

- `app/main.py` - FastAPI application, routes, WebSocket endpoint, broadcast logic
- `app/models.py` - Session state classes (`VotingSession`, `User`, `VotingRound`, `SessionManager`)
- `app/templates/` - Jinja2 HTML templates (landing page, voting page)
- `app/static/` - CSS styling
- `pyproject.toml` - Project metadata and dependencies (managed by uv)
- `uv.lock` - Locked dependency versions for reproducible installs

## Development Commands

**Run locally (recommended for development):**
```bash
./run-local.sh
```

**Run with Podman:**
```bash
./run-container.sh
```

Or manually:
```bash
podman build -t keep-archive-close .
podman run --rm -p 8000:8000 keep-archive-close
```

**Run manually (local Python):**
```bash
uv sync
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Access at: http://localhost:8000

## Code Quality & CI

**GitHub Actions CI:**
- Runs automatically on pull requests and pushes to main
- Checks: Python syntax validation, dependency installation, import checks, app startup
- Workflow file: `.github/workflows/ci.yml`

**Manual syntax check:**
```bash
uv run python -m py_compile app/__init__.py app/main.py app/models.py
```

**Verify imports:**
```bash
uv run python -c "from app import main, models"
```

## Key Behaviors

1. **User Flow**: Name entry → Create/join session → Real-time voting interface
2. **Voting Round**: Any user starts vote → 15s countdown → Buttons enable → Timer ends → Results display
3. **Vote State Tracking**: Users are "dimmed" in participant list until they vote
4. **Session Lifecycle**: Auto-created on first user → Auto-deleted when last user leaves
5. **Name Changes**: Click your name to rename (broadcasts update to all users)
6. **Presence Detection**: Heartbeat every 5s, cleanup every 10s, 30s timeout

## Configuration

- Vote timer duration: `VOTE_DURATION = 15` in `app/main.py`
- Heartbeat interval: 5 seconds (client-side in `voting.html`)
- Cleanup interval: 10 seconds (server-side in `app/main.py`)
- Inactivity timeout: 30 seconds (configurable in `app/models.py`)

## Design Constraints

- **Local team use**: Not designed for high-scale or geographically distributed users
- **No persistence**: Session state is in-memory; server restart clears all sessions
- **No authentication**: Sessions use UUID obscurity, not security
- **Single container**: Everything runs in one Podman container for simplicity
- **Dependency management**: Uses `uv` for fast, reproducible Python dependency installation
