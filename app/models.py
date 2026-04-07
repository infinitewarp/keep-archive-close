"""Session and voting state management."""
import asyncio
import time
from dataclasses import dataclass, field
from typing import Dict, Optional, Set
from uuid import uuid4


@dataclass
class User:
    """Represents a user in a voting session."""
    connection_id: str
    name: str
    websocket: object
    last_seen: float = field(default_factory=time.time)
    has_voted: bool = False
    vote: Optional[str] = None


@dataclass
class VotingRound:
    """Represents a single voting round."""
    active: bool = False
    start_time: Optional[float] = None
    votes: Dict[str, str] = field(default_factory=dict)  # connection_id -> vote choice


class VotingSession:
    """Manages a voting session with multiple users."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.users: Dict[str, User] = {}  # connection_id -> User
        self.current_round: VotingRound = VotingRound()
        self.created_at = time.time()

    def add_user(self, connection_id: str, name: str, websocket) -> User:
        """Add a user to the session."""
        user = User(connection_id=connection_id, name=name, websocket=websocket)
        self.users[connection_id] = user
        return user

    def remove_user(self, connection_id: str) -> None:
        """Remove a user from the session."""
        self.users.pop(connection_id, None)

    def update_user_activity(self, connection_id: str) -> None:
        """Update the last seen time for a user."""
        if connection_id in self.users:
            self.users[connection_id].last_seen = time.time()

    def rename_user(self, connection_id: str, new_name: str) -> None:
        """Change a user's name."""
        if connection_id in self.users:
            self.users[connection_id].name = new_name

    def start_vote(self) -> None:
        """Start a new voting round."""
        self.current_round = VotingRound(active=True, start_time=time.time())
        # Reset vote state for all users
        for user in self.users.values():
            user.has_voted = False
            user.vote = None

    def cast_vote(self, connection_id: str, vote: str) -> None:
        """Record a user's vote."""
        if self.current_round.active and connection_id in self.users:
            self.users[connection_id].has_voted = True
            self.users[connection_id].vote = vote
            self.current_round.votes[connection_id] = vote

    def abandon_vote(self) -> None:
        """Abandon the current voting round without tallying results."""
        self.current_round.active = False
        # Reset vote state for all users
        for user in self.users.values():
            user.has_voted = False
            user.vote = None

    def end_vote(self) -> Dict[str, int]:
        """End the current voting round and return results."""
        self.current_round.active = False

        # Tally votes
        results = {"keep": 0, "archive": 0, "close": 0}
        for vote in self.current_round.votes.values():
            if vote in results:
                results[vote] += 1

        return results

    def get_inactive_users(self, timeout_seconds: int = 30) -> Set[str]:
        """Get connection IDs of users who haven't been seen recently."""
        now = time.time()
        inactive = set()
        for connection_id, user in self.users.items():
            if now - user.last_seen > timeout_seconds:
                inactive.add(connection_id)
        return inactive

    def is_empty(self) -> bool:
        """Check if the session has no users."""
        return len(self.users) == 0

    def get_user_list(self):
        """Get list of users with their vote status."""
        return [
            {
                "connection_id": user.connection_id,
                "name": user.name,
                "has_voted": user.has_voted
            }
            for user in self.users.values()
        ]


class SessionManager:
    """Manages all active voting sessions."""

    def __init__(self):
        self.sessions: Dict[str, VotingSession] = {}

    def create_session(self) -> str:
        """Create a new voting session and return its ID."""
        session_id = str(uuid4())
        self.sessions[session_id] = VotingSession(session_id)
        return session_id

    def get_session(self, session_id: str) -> Optional[VotingSession]:
        """Get a session by ID."""
        return self.sessions.get(session_id)

    def delete_session(self, session_id: str) -> None:
        """Delete a session."""
        self.sessions.pop(session_id, None)

    def cleanup_inactive_users(self):
        """Remove inactive users from all sessions."""
        sessions_to_delete = []

        for session_id, session in self.sessions.items():
            inactive = session.get_inactive_users()
            for connection_id in inactive:
                session.remove_user(connection_id)

            if session.is_empty():
                sessions_to_delete.append(session_id)

        for session_id in sessions_to_delete:
            self.delete_session(session_id)


# Global session manager
session_manager = SessionManager()
