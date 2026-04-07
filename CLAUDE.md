# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

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
- `app/models.py` - Session state classes (`VotingSession`, `User`, `VotingRound`, `SessionManager`)
- `app/templates/` - Jinja2 HTML templates (landing page, voting page)
- `app/static/style.css` - CSS styling with CSS custom properties for theming
  - All colors defined as variables at top of file for easy customization
  - Dark mode overrides using `@media (prefers-color-scheme: dark)`
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
