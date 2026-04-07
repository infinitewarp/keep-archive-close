# keep-archive-close

keep-archive-close is a very simple single-purpose multi-user web app that presents an interface for a group of participants to vote "keep", "archive", or "close" while a brief timer counts down. This provides a short window for the participants to make a "gut check" assessment of an issue without allowing themselves to get bogged down in the details.

> **Note:** This project was primarily built through pair programming with [Claude Code](https://claude.ai/code). The entire codebase, tests, documentation, and tooling were collaboratively developed through conversational iteration.

## Features

- Real-time multi-user voting sessions
- Customizable countdown timer (1-999 seconds, synced across all clients)
- User personalization (choose name and color, persisted across sessions)
- Vote selection feedback (visual highlight shows your current vote)
- Anonymous session URLs (UUID-based, clean shareable links without user data)
- Live participant tracking with color-coded borders
- WebSocket-based real-time updates
- Automatic dark mode support (respects system preferences)
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

### Run tests

```bash
./run-tests.sh
```

Or manually:

```bash
uv sync --extra dev
uv run pytest
```

### Run linting

```bash
./run-lint.sh
```

Or manually:

```bash
uv run ruff check .
uv run ruff format --check .
```

## How It Works

1. Enter your name and pick a color on the landing page
2. Create a new session or join an existing one with a session ID
3. Share the clean session URL with your team (no personal data in URL)
4. Optionally adjust the countdown timer duration (defaults to 15 seconds)
5. Anyone in the session can click "Start New Vote"
6. The countdown begins and voting buttons activate
7. Cast your vote (keep, archive, or close) - a border highlights your choice
8. During voting, the button changes to "Abandon Vote" to cancel if needed
9. When the timer ends, results are displayed with the winner
10. Start another vote to continue evaluating more items

## Technical Stack

- **Backend**: FastAPI with WebSocket support
- **Frontend**: Server-side rendered HTML (Jinja2) with vanilla JavaScript
- **Real-time**: WebSocket connections for live updates
- **State persistence**: Cookies (user identity) + localStorage (preferences)
- **Deployment**: Single Podman/Docker container (multi-arch: amd64, arm64)
- **Dependency management**: uv with locked dependencies (pyproject.toml)
- **Resource usage**: ~50-100MB memory footprint

## License

MIT License - see [LICENSE](LICENSE) file for details.

