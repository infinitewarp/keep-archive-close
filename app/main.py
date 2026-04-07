"""FastAPI application for keep-archive-close voting."""
import asyncio
import json
from typing import Dict
from uuid import uuid4

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Form, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.models import session_manager

app = FastAPI(title="keep-archive-close")

# Mount static files and templates
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


@app.get("/", response_class=HTMLResponse)
async def landing_page(request: Request):
    """Landing page for entering name and creating/joining session."""
    return templates.TemplateResponse("landing.html", {"request": request})


@app.post("/create-session")
async def create_session(name: str = Form(...), color: str = Form("#667eea")):
    """Create a new voting session."""
    session_id = session_manager.create_session()
    response = RedirectResponse(f"/session/{session_id}", status_code=303)
    response.set_cookie(key="user_name", value=name, max_age=86400*30)  # 30 days
    response.set_cookie(key="user_color", value=color, max_age=86400*30)  # 30 days
    return response


@app.post("/join-session")
async def join_session(session_id: str = Form(...), name: str = Form(...), color: str = Form("#667eea")):
    """Join an existing voting session."""
    session = session_manager.get_session(session_id)
    if not session:
        return RedirectResponse("/?error=session_not_found", status_code=303)
    response = RedirectResponse(f"/session/{session_id}", status_code=303)
    response.set_cookie(key="user_name", value=name, max_age=86400*30)  # 30 days
    response.set_cookie(key="user_color", value=color, max_age=86400*30)  # 30 days
    return response


@app.get("/session/{session_id}", response_class=HTMLResponse)
async def voting_page(request: Request, session_id: str):
    """Voting session page."""
    session = session_manager.get_session(session_id)
    if not session:
        return RedirectResponse("/?error=session_not_found", status_code=303)

    # Get name and color from cookies or localStorage fallback
    user_name = request.cookies.get("user_name", "")
    user_color = request.cookies.get("user_color", "#667eea")

    return templates.TemplateResponse(
        "voting.html",
        {
            "request": request,
            "session_id": session_id,
            "user_name": user_name,
            "user_color": user_color,
        }
    )


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time voting updates."""
    await websocket.accept()

    session = session_manager.get_session(session_id)
    if not session:
        await websocket.close(code=1008, reason="Session not found")
        return

    # Generate connection ID and get user info
    connection_id = str(uuid4())

    user = None

    try:
        # Wait for initial message with user name
        initial_data = await websocket.receive_text()
        initial_msg = json.loads(initial_data)

        if initial_msg.get("type") == "join":
            user_name = initial_msg.get("name", "Anonymous")
            user_color = initial_msg.get("color", "#667eea")
            user = session.add_user(connection_id, user_name, websocket, user_color)

            # Broadcast user joined
            await broadcast_session_state(session)

            # Handle messages
            while True:
                data = await websocket.receive_text()
                message = json.loads(data)

                # Update activity timestamp
                session.update_user_activity(connection_id)

                msg_type = message.get("type")

                if msg_type == "start_vote":
                    # Guard against multiple simultaneous vote starts
                    if not session.current_round.active:
                        duration = message.get("duration", 15)
                        # Validate duration
                        if not isinstance(duration, int) or duration < 1 or duration > 999:
                            duration = 15
                        session.start_vote(duration)
                        await broadcast_session_state(session)
                        # Start countdown timer with custom duration
                        asyncio.create_task(countdown_timer(session, duration))

                elif msg_type == "abandon_vote":
                    session.abandon_vote()
                    await broadcast_session_state(session)

                elif msg_type == "vote":
                    vote = message.get("vote")
                    if vote in ["keep", "archive", "close"]:
                        session.cast_vote(connection_id, vote)
                        await broadcast_session_state(session)

                elif msg_type == "rename":
                    new_name = message.get("name", "Anonymous")
                    session.rename_user(connection_id, new_name)
                    await broadcast_session_state(session)

                elif msg_type == "change_color":
                    new_color = message.get("color", "#667eea")
                    session.change_user_color(connection_id, new_color)
                    await broadcast_session_state(session)

                elif msg_type == "heartbeat":
                    # Just update activity timestamp (already done above)
                    pass

    except WebSocketDisconnect:
        pass
    finally:
        # Clean up
        if session and user:
            session.remove_user(connection_id)
            await broadcast_session_state(session)

            # Delete session if empty
            if session.is_empty():
                session_manager.delete_session(session_id)


async def countdown_timer(session, duration=15):
    """Run countdown timer for voting round."""
    for remaining in range(duration, 0, -1):
        await asyncio.sleep(1)
        if not session.current_round.active:
            break
        await broadcast_timer(session, remaining - 1)

    if session.current_round.active:
        # End the vote
        results = session.end_vote()
        await broadcast_vote_results(session, results)


async def broadcast_session_state(session):
    """Broadcast current session state to all users."""
    message = {
        "type": "state_update",
        "users": session.get_user_list(),
        "vote_active": session.current_round.active,
        "vote_duration": session.current_round.duration if session.current_round.active else None,
    }
    await broadcast_to_session(session, message)


async def broadcast_timer(session, remaining):
    """Broadcast timer update to all users."""
    message = {
        "type": "timer_update",
        "remaining": remaining,
    }
    await broadcast_to_session(session, message)


async def broadcast_vote_results(session, results):
    """Broadcast voting results to all users."""
    # Determine winner
    max_votes = max(results.values())
    winners = [choice for choice, count in results.items() if count == max_votes]

    message = {
        "type": "vote_results",
        "results": results,
        "winner": winners[0] if len(winners) == 1 else "tie",
        "tied_options": winners if len(winners) > 1 else None,
    }
    await broadcast_to_session(session, message)


async def broadcast_to_session(session, message):
    """Send a message to all users in a session."""
    disconnected = []
    for connection_id, user in session.users.items():
        try:
            await user.websocket.send_text(json.dumps(message))
        except Exception:
            disconnected.append(connection_id)

    # Clean up disconnected users
    for connection_id in disconnected:
        session.remove_user(connection_id)


@app.on_event("startup")
async def startup_event():
    """Start background tasks on startup."""
    asyncio.create_task(cleanup_inactive_users())


async def cleanup_inactive_users():
    """Periodically clean up inactive users."""
    while True:
        await asyncio.sleep(10)  # Check every 10 seconds
        session_manager.cleanup_inactive_users()
