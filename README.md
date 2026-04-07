# keep-archive-close

keep-archive-close is a very simple single-purpose multi-user web app that presents an interface for a group of participants to vote "keep", "archive", or "close" while a brief timer counts down. This provides a short window for the participants to make a "gut check" assessment of an issue without allowing themselves to get bogged down in the details.

## Features

- Real-time multi-user voting sessions
- Timer-enforced decision making (15 seconds)
- Anonymous session URLs (UUID-based)
- Live participant tracking
- WebSocket-based real-time updates
- Lightweight single-container deployment

## Quick Start

### Run with Podman

```bash
./run-container.sh
```

Or manually:

```bash
podman build -t keep-archive-close .
podman run --rm -p 8000:8000 keep-archive-close
```

Then open http://localhost:8000 in your browser.

### Run locally (development)

```bash
./run-local.sh
```

Or manually:

```bash
uv sync
uv run uvicorn app.main:app --reload
```

## How It Works

1. Enter your name on the landing page
2. Create a new session or join an existing one with a session ID
3. Share the session URL with your team
4. Anyone in the session can click "Start New Vote"
5. A 15-second countdown begins and voting buttons activate
6. Cast your vote (keep, archive, or close)
7. During voting, the button changes to "Abandon Vote" to cancel if needed
8. When the timer ends, results are displayed with the winner
9. Start another vote to continue evaluating more items

## Technical Stack

- **Backend**: FastAPI with WebSocket support
- **Frontend**: Server-side rendered HTML (Jinja2) with vanilla JavaScript
- **Real-time**: WebSocket connections for live updates
- **Deployment**: Single Podman container
- **Dependency management**: uv with locked dependencies (pyproject.toml)
- **Resource usage**: ~50-100MB memory footprint

