"""Monitor module for CICD workflow visualization.

Provides event emission, WebSocket server, and dashboard serving capabilities.

Usage in workflows:
    # Enable monitoring with: CICD_MONITOR=1
    from cicd.monitor import emit
    emit("architect", "start", workflow="design-feature")
    emit("architect", "end")
"""

import json
import os
import webbrowser
from datetime import datetime, timezone
from pathlib import Path

# Default port (FastAPI handles both HTTP and WS)
DEFAULT_PORT = 8000

# Check if monitoring is enabled (env var)
def is_enabled() -> bool:
    """Check if monitoring is enabled via CICD_MONITOR env var."""
    return os.environ.get("CICD_MONITOR", "").lower() in ("1", "true", "yes", "on")


class Event:
    """Represents a CICD monitoring event."""

    def __init__(
        self,
        agent: str,
        action: str,
        workflow: str | None = None,
        parent: str | None = None,
        metadata: dict | None = None,
    ):
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.agent = agent
        self.action = action
        self.workflow = workflow
        self.parent = parent
        self.metadata = metadata or {}

    def to_dict(self) -> dict:
        """Convert event to dictionary."""
        return {
            "timestamp": self.timestamp,
            "agent": self.agent,
            "action": self.action,
            "workflow": self.workflow,
            "parent": self.parent,
            "metadata": self.metadata,
        }

    def to_json(self) -> str:
        """Convert event to JSON string."""
        return json.dumps(self.to_dict())


class EventEmitter:
    """Emits events to the monitor server."""

    # Class-level cache for server availability
    _server_available: bool | None = None
    _last_check: float = 0
    _check_interval: float = 30.0  # Re-check every 30 seconds

    def __init__(self, host: str = "localhost", port: int = DEFAULT_PORT):
        self.host = host
        self.port = port
        self.http_url = f"http://{host}:{port}"
        self._enabled = is_enabled()

    def emit(
        self,
        agent: str,
        action: str,
        workflow: str | None = None,
        parent: str | None = None,
        metadata: dict | None = None,
    ) -> dict:
        """Emit an event to the monitor server.

        Returns dict with status and message.
        If CICD_MONITOR is not enabled, returns immediately (zero overhead).
        """
        # Fast path: if monitoring disabled, return immediately
        if not self._enabled:
            return {"status": "disabled", "message": "Monitoring disabled"}

        event = Event(agent, action, workflow, parent, metadata)

        # Check cached server availability
        if not self._check_server_available():
            return {
                "status": "offline",
                "message": "Monitor server not running",
                "event": event.to_dict(),
            }

        # Try HTTP POST (fast, short timeout)
        try:
            import urllib.request
            import urllib.error

            url = f"{self.http_url}/api/events"
            data = event.to_json().encode("utf-8")
            req = urllib.request.Request(
                url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=1) as response:
                if response.status == 200:
                    return {"status": "success", "message": "Event emitted", "event": event.to_dict()}
        except urllib.error.URLError:
            EventEmitter._server_available = False
        except Exception:
            pass

        return {
            "status": "error",
            "message": "Failed to emit event",
            "event": event.to_dict(),
        }

    def _check_server_available(self) -> bool:
        """Check if server is available (with caching)."""
        import time

        now = time.time()

        # Use cached result if recent
        if (
            EventEmitter._server_available is not None
            and (now - EventEmitter._last_check) < EventEmitter._check_interval
        ):
            return EventEmitter._server_available

        # Quick health check
        try:
            import urllib.request
            import urllib.error

            req = urllib.request.Request(f"{self.http_url}/health", method="GET")
            with urllib.request.urlopen(req, timeout=0.5) as response:
                EventEmitter._server_available = response.status == 200
        except Exception:
            EventEmitter._server_available = False

        EventEmitter._last_check = now
        return EventEmitter._server_available


# Singleton emitter for convenience
_emitter: EventEmitter | None = None


def emit(
    agent: str,
    action: str,
    workflow: str | None = None,
    parent: str | None = None,
    metadata: dict | None = None,
) -> dict:
    """Convenience function to emit an event.

    Usage:
        from cicd.monitor import emit
        emit("architect", "start", workflow="design-feature")

    Enable with: CICD_MONITOR=1 or CICD_MONITOR=true
    """
    global _emitter
    if _emitter is None:
        _emitter = EventEmitter()
    return _emitter.emit(agent, action, workflow, parent, metadata)


def get_dashboard_path() -> Path:
    """Get path to dashboard files."""
    return Path(__file__).parent / "dashboard"


def open_dashboard(port: int = DEFAULT_PORT) -> None:
    """Open the dashboard in the default browser."""
    url = f"http://localhost:{port}"
    webbrowser.open(url)
