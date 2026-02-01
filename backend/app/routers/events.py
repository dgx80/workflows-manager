"""REST API routes for events."""

from typing import List

from fastapi import APIRouter

from app.core.connection_manager import connection_manager
from app.models.event import Event, EventCreate, MonitorState
from app.services.event_store import event_store

router = APIRouter(prefix="/api", tags=["events"])


@router.get("/events", response_model=List[Event])
async def get_events(limit: int | None = None) -> List[Event]:
    """Get all events, optionally limited to most recent."""
    return event_store.get_events(limit=limit)


@router.post("/events", response_model=Event)
async def create_event(event_create: EventCreate) -> Event:
    """Create a new event and broadcast to WebSocket clients."""
    event = event_store.add_event(event_create)

    # Broadcast to all connected WebSocket clients
    await connection_manager.broadcast({
        "type": "event",
        "event": event.model_dump()
    })

    return event


@router.get("/state", response_model=MonitorState)
async def get_state() -> MonitorState:
    """Get current monitor state."""
    return event_store.get_state()


@router.delete("/events")
async def clear_events() -> dict:
    """Clear all events and reset state."""
    event_store.clear()
    return {"status": "ok", "message": "Events cleared"}
