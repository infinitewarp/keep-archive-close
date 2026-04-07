"""Tests for FastAPI endpoints."""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import session_manager


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def clear_sessions():
    """Clear all sessions before each test."""
    session_manager.sessions.clear()
    yield
    session_manager.sessions.clear()


class TestLandingPage:
    """Test the landing page endpoint."""

    def test_landing_page_renders(self, client):
        """Test that landing page returns HTML."""
        response = client.get("/")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert b"keep-archive-close" in response.content


class TestCreateSession:
    """Test session creation endpoint."""

    def test_create_session_success(self, client):
        """Test creating a new session."""
        response = client.post(
            "/create-session",
            data={"name": "Alice", "color": "#ff0000"},
            follow_redirects=False
        )

        assert response.status_code == 303
        assert response.headers["location"].startswith("/session/")

        # Check cookies were set
        assert "user_name" in response.cookies
        assert response.cookies["user_name"] == "Alice"
        assert "user_color" in response.cookies
        assert response.cookies["user_color"] == "#ff0000"

    def test_create_session_default_color(self, client):
        """Test creating a session with default color."""
        response = client.post(
            "/create-session",
            data={"name": "Bob"},
            follow_redirects=False
        )

        assert response.status_code == 303
        assert response.cookies["user_color"] == "#667eea"

    def test_create_session_creates_in_manager(self, client):
        """Test that session is created in session manager."""
        response = client.post(
            "/create-session",
            data={"name": "Charlie", "color": "#00ff00"},
            follow_redirects=False
        )

        # Extract session ID from redirect location
        location = response.headers["location"]
        session_id = location.split("/")[-1]

        assert session_id in session_manager.sessions


class TestJoinSession:
    """Test session joining endpoint."""

    def test_join_existing_session(self, client):
        """Test joining an existing session."""
        # Create a session first
        session_id = session_manager.create_session()

        response = client.post(
            "/join-session",
            data={"session_id": session_id, "name": "Diana", "color": "#0000ff"},
            follow_redirects=False
        )

        assert response.status_code == 303
        assert response.headers["location"] == f"/session/{session_id}"
        assert response.cookies["user_name"] == "Diana"
        assert response.cookies["user_color"] == "#0000ff"

    def test_join_nonexistent_session(self, client):
        """Test joining a session that doesn't exist."""
        response = client.post(
            "/join-session",
            data={"session_id": "nonexistent-id", "name": "Eve", "color": "#ff00ff"},
            follow_redirects=False
        )

        assert response.status_code == 303
        assert response.headers["location"] == "/?error=session_not_found"


class TestVotingPage:
    """Test the voting page endpoint."""

    def test_voting_page_with_valid_session(self, client):
        """Test accessing a valid voting session page."""
        session_id = session_manager.create_session()

        response = client.get(
            f"/session/{session_id}",
            cookies={"user_name": "Frank", "user_color": "#ffff00"}
        )

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert session_id.encode() in response.content
        assert b"Frank" in response.content

    def test_voting_page_with_nonexistent_session(self, client):
        """Test accessing a nonexistent session redirects."""
        response = client.get(
            "/session/nonexistent-id",
            follow_redirects=False
        )

        assert response.status_code == 303
        assert response.headers["location"] == "/?error=session_not_found"

    def test_voting_page_without_cookies(self, client):
        """Test voting page works even without cookies."""
        session_id = session_manager.create_session()

        response = client.get(f"/session/{session_id}")

        assert response.status_code == 200
        # Should render with default values (empty name, default color)
        assert b"#667eea" in response.content  # Default color
