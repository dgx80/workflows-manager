"""WebSocket and HTTP server for CICD Monitor.

Provides real-time event broadcasting and REST API for the dashboard.
"""

import asyncio
import json
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

from wfm.monitor import DEFAULT_PORT, get_dashboard_path

# Use single port for both HTTP and WS (FastAPI handles both)
DEFAULT_HTTP_PORT = DEFAULT_PORT
DEFAULT_WS_PORT = DEFAULT_PORT + 1

# Store for events and connected clients
MAX_EVENTS = 1000
events_store: deque = deque(maxlen=MAX_EVENTS)
ws_clients: set = set()
current_state: dict = {
    "active_agent": None,
    "active_workflow": None,
    "started_at": None,
}


def update_state(event: dict) -> None:
    """Update current state based on event."""
    action = event.get("action", "")
    if action == "start":
        current_state["active_agent"] = event.get("agent")
        current_state["active_workflow"] = event.get("workflow")
        current_state["started_at"] = event.get("timestamp")
    elif action == "end":
        if current_state["active_agent"] == event.get("agent"):
            current_state["active_agent"] = None
            current_state["active_workflow"] = None
            current_state["started_at"] = None


async def broadcast(message: str) -> None:
    """Broadcast message to all connected WebSocket clients."""
    if ws_clients:
        await asyncio.gather(
            *[client.send(message) for client in ws_clients],
            return_exceptions=True,
        )


async def handle_websocket(websocket) -> None:
    """Handle WebSocket connection."""
    ws_clients.add(websocket)
    try:
        # Send current state and recent events on connect
        await websocket.send(json.dumps({
            "type": "init",
            "state": current_state,
            "events": list(events_store),
        }))

        async for message in websocket:
            try:
                event = json.loads(message)
                events_store.append(event)
                update_state(event)
                await broadcast(json.dumps({"type": "event", "event": event}))
            except json.JSONDecodeError:
                pass
    finally:
        ws_clients.discard(websocket)


async def handle_http(reader, writer) -> None:
    """Handle HTTP requests."""
    try:
        request_line = await asyncio.wait_for(reader.readline(), timeout=5.0)
        if not request_line:
            return

        request = request_line.decode().strip()
        parts = request.split()
        if len(parts) < 2:
            return

        method, path = parts[0], parts[1]

        # Read headers
        headers = {}
        content_length = 0
        while True:
            line = await reader.readline()
            if line == b"\r\n" or not line:
                break
            header = line.decode().strip()
            if ":" in header:
                key, value = header.split(":", 1)
                headers[key.strip().lower()] = value.strip()
                if key.strip().lower() == "content-length":
                    content_length = int(value.strip())

        # Read body if present
        body = b""
        if content_length > 0:
            body = await reader.read(content_length)

        # Route request
        if method == "GET" and path == "/api/events":
            response_body = json.dumps(list(events_store))
            send_json_response(writer, 200, response_body)

        elif method == "GET" and path == "/api/state":
            response_body = json.dumps(current_state)
            send_json_response(writer, 200, response_body)

        elif method == "POST" and path == "/api/events":
            try:
                event = json.loads(body.decode())
                events_store.append(event)
                update_state(event)
                asyncio.create_task(broadcast(json.dumps({"type": "event", "event": event})))
                send_json_response(writer, 200, '{"status": "ok"}')
            except json.JSONDecodeError:
                send_json_response(writer, 400, '{"error": "Invalid JSON"}')

        elif method == "GET":
            # Serve static files
            await serve_static(writer, path)

        else:
            send_json_response(writer, 404, '{"error": "Not found"}')

    except asyncio.TimeoutError:
        pass
    except Exception:
        pass
    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass


def send_json_response(writer, status: int, body: str) -> None:
    """Send JSON HTTP response."""
    status_text = {200: "OK", 400: "Bad Request", 404: "Not Found"}.get(status, "Unknown")
    response = (
        f"HTTP/1.1 {status} {status_text}\r\n"
        f"Content-Type: application/json\r\n"
        f"Access-Control-Allow-Origin: *\r\n"
        f"Content-Length: {len(body)}\r\n"
        f"\r\n"
        f"{body}"
    )
    writer.write(response.encode())


async def serve_static(writer, path: str) -> None:
    """Serve static files from dashboard directory."""
    dashboard_path = get_dashboard_path()

    # Default to index.html
    if path == "/" or path == "":
        path = "/index.html"

    # Security: prevent path traversal
    file_path = dashboard_path / path.lstrip("/")
    try:
        file_path = file_path.resolve()
        if not str(file_path).startswith(str(dashboard_path.resolve())):
            send_404(writer)
            return
    except Exception:
        send_404(writer)
        return

    if not file_path.exists() or not file_path.is_file():
        send_404(writer)
        return

    # Determine content type
    content_types = {
        ".html": "text/html",
        ".css": "text/css",
        ".js": "application/javascript",
        ".json": "application/json",
        ".png": "image/png",
        ".svg": "image/svg+xml",
    }
    content_type = content_types.get(file_path.suffix, "application/octet-stream")

    # Read and send file
    content = file_path.read_bytes()
    response = (
        f"HTTP/1.1 200 OK\r\n"
        f"Content-Type: {content_type}\r\n"
        f"Access-Control-Allow-Origin: *\r\n"
        f"Content-Length: {len(content)}\r\n"
        f"\r\n"
    )
    writer.write(response.encode() + content)


def send_404(writer) -> None:
    """Send 404 response."""
    body = "<html><body><h1>404 Not Found</h1></body></html>"
    response = (
        f"HTTP/1.1 404 Not Found\r\n"
        f"Content-Type: text/html\r\n"
        f"Content-Length: {len(body)}\r\n"
        f"\r\n"
        f"{body}"
    )
    writer.write(response.encode())


async def run_server(
    ws_port: int = DEFAULT_WS_PORT,
    http_port: int = DEFAULT_HTTP_PORT,
) -> None:
    """Run both WebSocket and HTTP servers."""
    try:
        import websockets
    except ImportError:
        print("[ERROR] websockets package not installed.")
        print("Install with: pip install 'cicd-workflow[monitor]'")
        print("         or: pip install websockets")
        return

    # Start WebSocket server
    ws_server = await websockets.serve(handle_websocket, "localhost", ws_port)
    print(f"[OK] WebSocket server running on ws://localhost:{ws_port}/ws")

    # Start HTTP server
    http_server = await asyncio.start_server(handle_http, "localhost", http_port)
    print(f"[OK] HTTP server running on http://localhost:{http_port}")
    print()
    print("Dashboard: http://localhost:{http_port}")
    print("Press Ctrl+C to stop")

    # Run forever
    await asyncio.gather(
        ws_server.wait_closed(),
        http_server.serve_forever(),
    )


def serve(ws_port: int = DEFAULT_WS_PORT, http_port: int = DEFAULT_HTTP_PORT) -> None:
    """Start the monitor server (blocking)."""
    try:
        asyncio.run(run_server(ws_port, http_port))
    except KeyboardInterrupt:
        print("\n[OK] Server stopped")
