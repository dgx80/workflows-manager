"""WebSocket connection manager for CICD Monitor."""

import json
from typing import Any

from fastapi import WebSocket


class ConnectionManager:
    """Manages WebSocket connections."""

    def __init__(self):
        self._connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        """Accept and register a new connection."""
        await websocket.accept()
        self._connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a connection."""
        if websocket in self._connections:
            self._connections.remove(websocket)

    async def broadcast(self, message: dict[str, Any]) -> None:
        """Broadcast a message to all connected clients."""
        if not self._connections:
            return

        data = json.dumps(message)
        disconnected = []

        for connection in self._connections:
            try:
                await connection.send_text(data)
            except Exception:
                disconnected.append(connection)

        # Clean up disconnected clients
        for conn in disconnected:
            self.disconnect(conn)

    async def send_personal(self, websocket: WebSocket, message: dict[str, Any]) -> None:
        """Send a message to a specific client."""
        try:
            await websocket.send_text(json.dumps(message))
        except Exception:
            self.disconnect(websocket)

    @property
    def connection_count(self) -> int:
        """Get current connection count."""
        return len(self._connections)


# Global singleton instance
connection_manager = ConnectionManager()
