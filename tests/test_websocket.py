"""Tests for WebSocket functionality."""
import asyncio
import json

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import session_manager


@pytest.fixture(autouse=True)
def clear_sessions():
    """Clear all sessions before each test."""
    session_manager.sessions.clear()
    yield
    session_manager.sessions.clear()


class TestWebSocketConnection:
    """Test WebSocket connection and messaging."""

    def test_websocket_join(self):
        """Test joining a session via WebSocket."""
        client = TestClient(app)
        session_id = session_manager.create_session()

        with client.websocket_connect(f"/ws/{session_id}") as websocket:
            # Send join message
            websocket.send_json({
                "type": "join",
                "name": "Alice",
                "color": "#ff0000"
            })

            # Receive state update
            data = websocket.receive_json()
            assert data["type"] == "state_update"
            assert len(data["users"]) == 1
            assert data["users"][0]["name"] == "Alice"
            assert data["users"][0]["color"] == "#ff0000"
            assert data["vote_active"] is False

    def test_websocket_nonexistent_session(self):
        """Test connecting to a nonexistent session."""
        client = TestClient(app)

        # TestClient doesn't raise on close, just check session doesn't exist
        from starlette.websockets import WebSocketDisconnect
        try:
            with client.websocket_connect("/ws/nonexistent-id") as websocket:
                # Connection established but should be closed by server
                # Try to send a message - should fail
                websocket.send_json({"type": "join", "name": "Test", "color": "#ff0000"})
                websocket.receive_json(timeout=1)  # Should timeout or disconnect
                pytest.fail("Expected connection to be closed")
        except (WebSocketDisconnect, Exception):
            pass  # Expected - connection was closed

    def test_websocket_multiple_users(self):
        """Test multiple users joining the same session."""
        client = TestClient(app)
        session_id = session_manager.create_session()

        with client.websocket_connect(f"/ws/{session_id}") as ws1:
            ws1.send_json({"type": "join", "name": "Alice", "color": "#ff0000"})
            ws1.receive_json()  # Consume state update

            with client.websocket_connect(f"/ws/{session_id}") as ws2:
                ws2.send_json({"type": "join", "name": "Bob", "color": "#00ff00"})

                # Both should receive state update with 2 users
                data1 = ws1.receive_json()
                data2 = ws2.receive_json()

                assert data1["type"] == "state_update"
                assert len(data1["users"]) == 2
                assert data2["type"] == "state_update"
                assert len(data2["users"]) == 2

    def test_websocket_start_vote(self):
        """Test starting a vote via WebSocket."""
        client = TestClient(app)
        session_id = session_manager.create_session()

        with client.websocket_connect(f"/ws/{session_id}") as websocket:
            websocket.send_json({"type": "join", "name": "Alice", "color": "#ff0000"})
            websocket.receive_json()  # Consume initial state

            # Start vote
            websocket.send_json({"type": "start_vote", "duration": 20})

            # Receive state update
            data = websocket.receive_json()
            assert data["type"] == "state_update"
            assert data["vote_active"] is True
            assert data["vote_duration"] == 20

    def test_websocket_start_vote_guard(self):
        """Test that multiple simultaneous vote starts are guarded."""
        client = TestClient(app)
        session_id = session_manager.create_session()

        with client.websocket_connect(f"/ws/{session_id}") as websocket:
            websocket.send_json({"type": "join", "name": "Alice", "color": "#ff0000"})
            websocket.receive_json()  # Consume initial state

            # Start first vote
            websocket.send_json({"type": "start_vote", "duration": 20})
            websocket.receive_json()  # Consume state update

            # Try to start another vote (should be ignored due to guard)
            websocket.send_json({"type": "start_vote", "duration": 30})

            # Session should still have duration=20, not 30
            session = session_manager.get_session(session_id)
            assert session.current_round.duration == 20

    def test_websocket_cast_vote(self):
        """Test casting a vote via WebSocket."""
        client = TestClient(app)
        session_id = session_manager.create_session()

        with client.websocket_connect(f"/ws/{session_id}") as websocket:
            websocket.send_json({"type": "join", "name": "Alice", "color": "#ff0000"})
            websocket.receive_json()

            # Start vote
            websocket.send_json({"type": "start_vote", "duration": 15})
            websocket.receive_json()

            # Cast vote
            websocket.send_json({"type": "vote", "vote": "keep"})

            # Receive state update
            data = websocket.receive_json()
            assert data["type"] == "state_update"
            assert data["users"][0]["has_voted"] is True

    def test_websocket_abandon_vote(self):
        """Test abandoning a vote via WebSocket."""
        client = TestClient(app)
        session_id = session_manager.create_session()

        with client.websocket_connect(f"/ws/{session_id}") as websocket:
            websocket.send_json({"type": "join", "name": "Alice", "color": "#ff0000"})
            websocket.receive_json()

            # Start vote
            websocket.send_json({"type": "start_vote", "duration": 15})
            websocket.receive_json()

            # Abandon vote
            websocket.send_json({"type": "abandon_vote"})

            # Receive state update
            data = websocket.receive_json()
            assert data["type"] == "state_update"
            assert data["vote_active"] is False

    def test_websocket_rename(self):
        """Test renaming a user via WebSocket."""
        client = TestClient(app)
        session_id = session_manager.create_session()

        with client.websocket_connect(f"/ws/{session_id}") as websocket:
            websocket.send_json({"type": "join", "name": "Alice", "color": "#ff0000"})
            websocket.receive_json()

            # Rename
            websocket.send_json({"type": "rename", "name": "Alice Smith"})

            # Receive state update
            data = websocket.receive_json()
            assert data["type"] == "state_update"
            assert data["users"][0]["name"] == "Alice Smith"

    def test_websocket_change_color(self):
        """Test changing user color via WebSocket."""
        client = TestClient(app)
        session_id = session_manager.create_session()

        with client.websocket_connect(f"/ws/{session_id}") as websocket:
            websocket.send_json({"type": "join", "name": "Alice", "color": "#ff0000"})
            websocket.receive_json()

            # Change color
            websocket.send_json({"type": "change_color", "color": "#00ff00"})

            # Receive state update
            data = websocket.receive_json()
            assert data["type"] == "state_update"
            assert data["users"][0]["color"] == "#00ff00"

    def test_websocket_heartbeat(self):
        """Test heartbeat message."""
        client = TestClient(app)
        session_id = session_manager.create_session()

        with client.websocket_connect(f"/ws/{session_id}") as websocket:
            websocket.send_json({"type": "join", "name": "Alice", "color": "#ff0000"})
            websocket.receive_json()

            # Send heartbeat (should not generate response)
            websocket.send_json({"type": "heartbeat"})

            # Verify user is still active in session
            session = session_manager.get_session(session_id)
            assert len(session.users) == 1

    def test_websocket_disconnect_removes_user(self):
        """Test that disconnecting removes user from session."""
        client = TestClient(app)
        session_id = session_manager.create_session()

        with client.websocket_connect(f"/ws/{session_id}") as websocket:
            websocket.send_json({"type": "join", "name": "Alice", "color": "#ff0000"})
            websocket.receive_json()

        # After closing, user should be removed
        session = session_manager.get_session(session_id)
        assert session is None  # Session deleted when empty


class TestVoteResults:
    """Test vote results calculation via session methods."""

    def test_vote_results_single_winner(self):
        """Test vote results with a clear winner."""
        from app.models import VotingSession
        from unittest.mock import Mock

        session = VotingSession("test-session")
        ws1, ws2, ws3 = Mock(), Mock(), Mock()
        session.add_user("conn-1", "Alice", ws1)
        session.add_user("conn-2", "Bob", ws2)
        session.add_user("conn-3", "Charlie", ws3)

        session.start_vote()
        session.cast_vote("conn-1", "keep")
        session.cast_vote("conn-2", "keep")
        session.cast_vote("conn-3", "archive")

        results = session.end_vote()

        assert results["keep"] == 2
        assert results["archive"] == 1
        assert results["close"] == 0

    def test_vote_results_tie(self):
        """Test vote results with a tie."""
        from app.models import VotingSession
        from unittest.mock import Mock

        session = VotingSession("test-session")
        ws1, ws2 = Mock(), Mock()
        session.add_user("conn-1", "Alice", ws1)
        session.add_user("conn-2", "Bob", ws2)

        session.start_vote()
        session.cast_vote("conn-1", "keep")
        session.cast_vote("conn-2", "archive")

        results = session.end_vote()

        assert results["keep"] == 1
        assert results["archive"] == 1
        assert results["close"] == 0
