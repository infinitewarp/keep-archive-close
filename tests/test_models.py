"""Tests for session and voting state management."""

import time
from unittest.mock import Mock

from app.models import SessionManager, User, VotingRound, VotingSession


class TestUser:
    """Test User dataclass."""

    def test_user_creation(self):
        """Test creating a user with default values."""
        ws = Mock()
        user = User(connection_id="test-id", name="Alice", websocket=ws)

        assert user.connection_id == "test-id"
        assert user.name == "Alice"
        assert user.websocket == ws
        assert user.color == "#667eea"
        assert user.has_voted is False
        assert user.vote is None
        assert isinstance(user.last_seen, float)

    def test_user_with_custom_color(self):
        """Test creating a user with a custom color."""
        ws = Mock()
        user = User(connection_id="test-id", name="Bob", websocket=ws, color="#ff0000")

        assert user.color == "#ff0000"


class TestVotingRound:
    """Test VotingRound dataclass."""

    def test_voting_round_defaults(self):
        """Test VotingRound with default values."""
        round = VotingRound()

        assert round.active is False
        assert round.start_time is None
        assert round.duration == 15
        assert round.votes == {}

    def test_voting_round_with_values(self):
        """Test VotingRound with custom values."""
        now = time.time()
        round = VotingRound(active=True, start_time=now, duration=30)

        assert round.active is True
        assert round.start_time == now
        assert round.duration == 30


class TestVotingSession:
    """Test VotingSession class."""

    def test_session_creation(self):
        """Test creating a new voting session."""
        session = VotingSession("test-session-id")

        assert session.session_id == "test-session-id"
        assert session.users == {}
        assert isinstance(session.current_round, VotingRound)
        assert session.current_round.active is False
        assert isinstance(session.created_at, float)

    def test_add_user(self):
        """Test adding a user to a session."""
        session = VotingSession("test-session-id")
        ws = Mock()

        user = session.add_user("conn-1", "Alice", ws, "#ff0000")

        assert user.connection_id == "conn-1"
        assert user.name == "Alice"
        assert user.color == "#ff0000"
        assert "conn-1" in session.users
        assert session.users["conn-1"] == user

    def test_remove_user(self):
        """Test removing a user from a session."""
        session = VotingSession("test-session-id")
        ws = Mock()
        session.add_user("conn-1", "Alice", ws)

        session.remove_user("conn-1")

        assert "conn-1" not in session.users
        assert len(session.users) == 0

    def test_remove_nonexistent_user(self):
        """Test removing a user that doesn't exist (should not error)."""
        session = VotingSession("test-session-id")

        session.remove_user("nonexistent")  # Should not raise
        assert len(session.users) == 0

    def test_update_user_activity(self):
        """Test updating user activity timestamp."""
        session = VotingSession("test-session-id")
        ws = Mock()
        session.add_user("conn-1", "Alice", ws)

        original_time = session.users["conn-1"].last_seen
        time.sleep(0.01)

        session.update_user_activity("conn-1")

        assert session.users["conn-1"].last_seen > original_time

    def test_rename_user(self):
        """Test renaming a user."""
        session = VotingSession("test-session-id")
        ws = Mock()
        session.add_user("conn-1", "Alice", ws)

        session.rename_user("conn-1", "Alice Smith")

        assert session.users["conn-1"].name == "Alice Smith"

    def test_change_user_color(self):
        """Test changing a user's color."""
        session = VotingSession("test-session-id")
        ws = Mock()
        session.add_user("conn-1", "Alice", ws)

        session.change_user_color("conn-1", "#00ff00")

        assert session.users["conn-1"].color == "#00ff00"

    def test_start_vote(self):
        """Test starting a new voting round."""
        session = VotingSession("test-session-id")
        ws1, ws2 = Mock(), Mock()
        session.add_user("conn-1", "Alice", ws1)
        session.add_user("conn-2", "Bob", ws2)
        session.users["conn-1"].has_voted = True
        session.users["conn-1"].vote = "keep"

        session.start_vote(duration=20)

        assert session.current_round.active is True
        assert session.current_round.duration == 20
        assert isinstance(session.current_round.start_time, float)
        # Check that user vote state was reset
        assert session.users["conn-1"].has_voted is False
        assert session.users["conn-1"].vote is None
        assert session.users["conn-2"].has_voted is False

    def test_cast_vote(self):
        """Test casting a vote."""
        session = VotingSession("test-session-id")
        ws = Mock()
        session.add_user("conn-1", "Alice", ws)
        session.start_vote()

        session.cast_vote("conn-1", "archive")

        assert session.users["conn-1"].has_voted is True
        assert session.users["conn-1"].vote == "archive"
        assert session.current_round.votes["conn-1"] == "archive"

    def test_cast_vote_when_inactive(self):
        """Test that votes aren't recorded when round is inactive."""
        session = VotingSession("test-session-id")
        ws = Mock()
        session.add_user("conn-1", "Alice", ws)

        session.cast_vote("conn-1", "keep")

        assert session.users["conn-1"].has_voted is False
        assert "conn-1" not in session.current_round.votes

    def test_abandon_vote(self):
        """Test abandoning an active vote."""
        session = VotingSession("test-session-id")
        ws1, ws2 = Mock(), Mock()
        session.add_user("conn-1", "Alice", ws1)
        session.add_user("conn-2", "Bob", ws2)
        session.start_vote()
        session.cast_vote("conn-1", "keep")

        session.abandon_vote()

        assert session.current_round.active is False
        assert session.users["conn-1"].has_voted is False
        assert session.users["conn-1"].vote is None
        assert session.users["conn-2"].has_voted is False

    def test_end_vote(self):
        """Test ending a vote and getting results."""
        session = VotingSession("test-session-id")
        ws1, ws2, ws3, ws4 = Mock(), Mock(), Mock(), Mock()
        session.add_user("conn-1", "Alice", ws1)
        session.add_user("conn-2", "Bob", ws2)
        session.add_user("conn-3", "Charlie", ws3)
        session.add_user("conn-4", "Diana", ws4)
        session.start_vote()
        session.cast_vote("conn-1", "keep")
        session.cast_vote("conn-2", "keep")
        session.cast_vote("conn-3", "archive")
        session.cast_vote("conn-4", "close")

        results = session.end_vote()

        assert session.current_round.active is False
        assert results == {"keep": 2, "archive": 1, "close": 1}

    def test_end_vote_no_votes(self):
        """Test ending a vote with no votes cast."""
        session = VotingSession("test-session-id")
        session.start_vote()

        results = session.end_vote()

        assert results == {"keep": 0, "archive": 0, "close": 0}

    def test_get_inactive_users(self):
        """Test getting inactive users based on timeout."""
        session = VotingSession("test-session-id")
        ws1, ws2 = Mock(), Mock()
        user1 = session.add_user("conn-1", "Alice", ws1)
        user2 = session.add_user("conn-2", "Bob", ws2)

        # Manually set last_seen times
        user1.last_seen = time.time() - 40  # 40 seconds ago
        user2.last_seen = time.time() - 10  # 10 seconds ago

        inactive = session.get_inactive_users(timeout_seconds=30)

        assert "conn-1" in inactive
        assert "conn-2" not in inactive

    def test_is_empty(self):
        """Test checking if session is empty."""
        session = VotingSession("test-session-id")

        assert session.is_empty() is True

        ws = Mock()
        session.add_user("conn-1", "Alice", ws)

        assert session.is_empty() is False

        session.remove_user("conn-1")

        assert session.is_empty() is True

    def test_get_user_list(self):
        """Test getting list of users with vote status."""
        session = VotingSession("test-session-id")
        ws1, ws2 = Mock(), Mock()
        session.add_user("conn-1", "Alice", ws1, "#ff0000")
        session.add_user("conn-2", "Bob", ws2, "#00ff00")
        session.start_vote()
        session.cast_vote("conn-1", "keep")

        user_list = session.get_user_list()

        assert len(user_list) == 2
        assert user_list[0] == {
            "connection_id": "conn-1",
            "name": "Alice",
            "color": "#ff0000",
            "has_voted": True,
        }
        assert user_list[1] == {
            "connection_id": "conn-2",
            "name": "Bob",
            "color": "#00ff00",
            "has_voted": False,
        }


class TestSessionManager:
    """Test SessionManager class."""

    def test_create_session(self):
        """Test creating a new session."""
        manager = SessionManager()

        session_id = manager.create_session()

        assert isinstance(session_id, str)
        assert len(session_id) == 36  # UUID format
        assert session_id in manager.sessions
        assert isinstance(manager.sessions[session_id], VotingSession)

    def test_get_session(self):
        """Test getting a session by ID."""
        manager = SessionManager()
        session_id = manager.create_session()

        session = manager.get_session(session_id)

        assert session is not None
        assert session.session_id == session_id

    def test_get_nonexistent_session(self):
        """Test getting a session that doesn't exist."""
        manager = SessionManager()

        session = manager.get_session("nonexistent-id")

        assert session is None

    def test_delete_session(self):
        """Test deleting a session."""
        manager = SessionManager()
        session_id = manager.create_session()

        manager.delete_session(session_id)

        assert session_id not in manager.sessions

    def test_delete_nonexistent_session(self):
        """Test deleting a session that doesn't exist (should not error)."""
        manager = SessionManager()

        manager.delete_session("nonexistent-id")  # Should not raise

    def test_cleanup_inactive_users(self):
        """Test cleaning up inactive users from sessions."""
        manager = SessionManager()
        session_id = manager.create_session()
        session = manager.get_session(session_id)

        ws1, ws2 = Mock(), Mock()
        user1 = session.add_user("conn-1", "Alice", ws1)
        session.add_user("conn-2", "Bob", ws2)

        # Make user1 inactive
        user1.last_seen = time.time() - 40

        manager.cleanup_inactive_users()

        assert "conn-1" not in session.users
        assert "conn-2" in session.users

    def test_cleanup_deletes_empty_sessions(self):
        """Test that cleanup deletes sessions with no users."""
        manager = SessionManager()
        session_id = manager.create_session()
        session = manager.get_session(session_id)

        ws = Mock()
        user = session.add_user("conn-1", "Alice", ws)
        user.last_seen = time.time() - 40  # Make inactive

        manager.cleanup_inactive_users()

        assert session_id not in manager.sessions
