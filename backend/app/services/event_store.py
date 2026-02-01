"""In-memory event store for CICD Monitor."""

from collections import deque
from typing import List

from app.models.event import Event, EventCreate, MonitorState


class EventStore:
    """Thread-safe in-memory event store."""

    def __init__(self, max_events: int = 1000):
        self._events: deque[Event] = deque(maxlen=max_events)
        self._state = MonitorState()

    def add_event(self, event_create: EventCreate) -> Event:
        """Add a new event and update state."""
        event = Event.from_create(event_create)
        self._events.append(event)
        self._update_state(event)
        return event

    def _update_state(self, event: Event) -> None:
        """Update monitor state based on event."""
        if event.action == "start":
            self._state.active_agent = event.agent
            self._state.active_workflow = event.workflow
            self._state.started_at = event.timestamp
        elif event.action == "end":
            if self._state.active_agent == event.agent:
                self._state.active_agent = None
                self._state.active_workflow = None
                self._state.started_at = None
        elif event.action == "error":
            # Keep agent active on error for visibility
            pass
        self._state.event_count = len(self._events)

    def get_events(self, limit: int | None = None) -> List[Event]:
        """Get events, optionally limited."""
        events = list(self._events)
        if limit:
            return events[-limit:]
        return events

    def get_state(self) -> MonitorState:
        """Get current monitor state."""
        return self._state

    def clear(self) -> None:
        """Clear all events and reset state."""
        self._events.clear()
        self._state = MonitorState()


# Global singleton instance
event_store = EventStore()
