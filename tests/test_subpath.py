"""Tests for ROOT_PATH subpath deployment functionality."""

import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.models import session_manager


@pytest.fixture(autouse=True)
def clear_sessions():
    """Clear all sessions before each test."""
    session_manager.sessions.clear()
    yield
    session_manager.sessions.clear()


class TestRootPathDefault:
    """Test app behavior with default ROOT_PATH (empty string)."""

    @pytest.fixture
    def client(self):
        """Create test client with default ROOT_PATH."""
        # Need to reload app with ROOT_PATH="" to ensure clean state
        with patch.dict(os.environ, {"ROOT_PATH": ""}):
            # Import fresh to pick up environment variable
            import importlib

            import app.main

            importlib.reload(app.main)
            return TestClient(app.main.app)

    def test_landing_page_has_empty_root_path(self, client):
        """Test landing page renders with empty root_path."""
        response = client.get("/")

        assert response.status_code == 200
        assert b"const ROOT_PATH = '';" in response.content
        assert b'href="/static/style.css?v=' in response.content

    def test_create_session_redirects_without_prefix(self, client):
        """Test session creation redirects to /session/{id}."""
        response = client.post(
            "/create-session", data={"name": "Alice", "color": "#ff0000"}, follow_redirects=False
        )

        assert response.status_code == 303
        location = response.headers["location"]
        assert location.startswith("/session/")
        assert not location.startswith("//")  # Ensure no double slash

    def test_join_session_redirect_without_prefix(self, client):
        """Test join session error redirects to /?error=..."""
        response = client.post(
            "/join-session",
            data={"session_id": "nonexistent", "name": "Bob", "color": "#00ff00"},
            follow_redirects=False,
        )

        assert response.status_code == 303
        assert response.headers["location"] == "/?error=session_not_found"

    def test_voting_page_has_empty_root_path(self, client):
        """Test voting page renders with empty root_path."""
        # Create a session first
        session_id = session_manager.create_session()

        response = client.get(f"/session/{session_id}")

        assert response.status_code == 200
        assert b"const ROOT_PATH = '';" in response.content
        assert b'href="/static/style.css?v=' in response.content


class TestRootPathWithSubpath:
    """Test app behavior with ROOT_PATH set to a subpath."""

    @pytest.fixture
    def client(self):
        """Create test client with ROOT_PATH=/kac."""
        with patch.dict(os.environ, {"ROOT_PATH": "/kac"}):
            # Import fresh to pick up environment variable
            import importlib

            import app.main

            importlib.reload(app.main)
            return TestClient(app.main.app)

    def test_landing_page_has_subpath_root_path(self, client):
        """Test landing page renders with /kac root_path."""
        response = client.get("/kac/")

        assert response.status_code == 200
        assert b"const ROOT_PATH = '/kac';" in response.content
        assert b'href="/kac/static/style.css?v=' in response.content

    def test_create_session_redirects_with_prefix(self, client):
        """Test session creation redirects to /kac/session/{id}."""
        response = client.post(
            "/kac/create-session",
            data={"name": "Alice", "color": "#ff0000"},
            follow_redirects=False,
        )

        assert response.status_code == 303
        location = response.headers["location"]
        assert location.startswith("/kac/session/")
        # Ensure session ID is present
        assert len(location.split("/")) == 4  # ['', 'kac', 'session', '{uuid}']

    def test_join_session_redirect_with_prefix(self, client):
        """Test join session error redirects to /kac/?error=..."""
        response = client.post(
            "/kac/join-session",
            data={"session_id": "nonexistent", "name": "Bob", "color": "#00ff00"},
            follow_redirects=False,
        )

        assert response.status_code == 303
        assert response.headers["location"] == "/kac/?error=session_not_found"

    def test_join_existing_session_redirect_with_prefix(self, client):
        """Test joining existing session redirects with subpath prefix."""
        # Create a session first
        session_id = session_manager.create_session()

        response = client.post(
            "/kac/join-session",
            data={"session_id": session_id, "name": "Bob", "color": "#00ff00"},
            follow_redirects=False,
        )

        assert response.status_code == 303
        assert response.headers["location"] == f"/kac/session/{session_id}"

    def test_voting_page_has_subpath_root_path(self, client):
        """Test voting page renders with /kac root_path."""
        # Create a session first
        session_id = session_manager.create_session()

        response = client.get(f"/kac/session/{session_id}")

        assert response.status_code == 200
        assert b"const ROOT_PATH = '/kac';" in response.content
        assert b'href="/kac/static/style.css?v=' in response.content

    def test_voting_page_nonexistent_redirects_with_prefix(self, client):
        """Test voting page for nonexistent session redirects with prefix."""
        response = client.get("/kac/session/nonexistent-id", follow_redirects=False)

        assert response.status_code == 303
        assert response.headers["location"] == "/kac/?error=session_not_found"

    def test_app_accessible_both_paths_in_test(self, client):
        """Test that app is accessible at both / and /kac in test mode.

        Note: In production with a reverse proxy, the proxy ensures only /kac
        reaches the app. In test mode, both paths work because TestClient
        doesn't enforce root_path routing restrictions.
        """
        # Both paths work in test mode
        response_root = client.get("/")
        response_subpath = client.get("/kac/")

        assert response_root.status_code == 200
        assert response_subpath.status_code == 200

        # But they render with the correct ROOT_PATH value
        assert b"const ROOT_PATH = '/kac';" in response_subpath.content


class TestRootPathTrailingSlash:
    """Test ROOT_PATH handling with trailing slashes."""

    @pytest.fixture
    def client(self):
        """Create test client with ROOT_PATH=/kac/ (with trailing slash)."""
        with patch.dict(os.environ, {"ROOT_PATH": "/kac/"}):
            # Import fresh to pick up environment variable
            import importlib

            import app.main

            importlib.reload(app.main)
            return TestClient(app.main.app)

    def test_trailing_slash_is_stripped(self, client):
        """Test that trailing slashes in ROOT_PATH are removed."""
        # The app should strip trailing slashes, so /kac/ becomes /kac
        response = client.get("/kac/")

        assert response.status_code == 200
        # Should have /kac not /kac/
        assert b"const ROOT_PATH = '/kac';" in response.content
        assert b'href="/kac/static/style.css?v=' in response.content
        # Should not have double slashes
        assert b'href="/kac//static' not in response.content


class TestRootPathCookies:
    """Test that cookies work correctly with subpath deployment."""

    @pytest.fixture
    def client(self):
        """Create test client with ROOT_PATH=/kac."""
        with patch.dict(os.environ, {"ROOT_PATH": "/kac"}):
            import importlib

            import app.main

            importlib.reload(app.main)
            return TestClient(app.main.app)

    def test_cookies_set_on_create_session(self, client):
        """Test cookies are set correctly when creating session with subpath."""
        response = client.post(
            "/kac/create-session",
            data={"name": "Alice", "color": "#ff0000"},
            follow_redirects=False,
        )

        assert response.status_code == 303
        assert "user_name" in response.cookies
        assert response.cookies["user_name"] == "Alice"
        assert "user_color" in response.cookies
        assert response.cookies["user_color"] == "#ff0000"

    def test_cookies_set_on_join_session(self, client):
        """Test cookies are set correctly when joining session with subpath."""
        session_id = session_manager.create_session()

        response = client.post(
            "/kac/join-session",
            data={"session_id": session_id, "name": "Bob", "color": "#00ff00"},
            follow_redirects=False,
        )

        assert response.status_code == 303
        assert "user_name" in response.cookies
        assert response.cookies["user_name"] == "Bob"
        assert "user_color" in response.cookies
        assert response.cookies["user_color"] == "#00ff00"
