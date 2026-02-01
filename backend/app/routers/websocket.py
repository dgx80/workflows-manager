"""WebSocket endpoint for real-time updates."""

import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.connection_manager import connection_manager
from app.models.event import EventCreate
from app.services.event_store import event_store

router = APIRouter(tags=["websocket"])


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time event streaming."""
    await connection_manager.connect(websocket)

    try:
        # Send initial state and recent events
        events = event_store.get_events(limit=100)
        state = event_store.get_state()

        await connection_manager.send_personal(websocket, {
            "type": "init",
            "events": [e.model_dump() for e in events],
            "state": state.model_dump()
        })

        # Listen for incoming events (agents can send events via WebSocket too)
        while True:
            data = await websocket.receive_text()
            try:
                payload = json.loads(data)
                # Create event from WebSocket message
                event_create = EventCreate(**payload)
                event = event_store.add_event(event_create)

                # Broadcast to all clients
                await connection_manager.broadcast({
                    "type": "event",
                    "event": event.model_dump()
                })
            except json.JSONDecodeError:
                await connection_manager.send_personal(websocket, {
                    "type": "error",
                    "message": "Invalid JSON"
                })
            except Exception as e:
                await connection_manager.send_personal(websocket, {
                    "type": "error",
                    "message": str(e)
                })

    except WebSocketDisconnect:
        connection_manager.disconnect(websocket)
