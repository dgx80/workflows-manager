"""Pydantic models for CICD Monitor events."""

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class EventCreate(BaseModel):
    """Input model for creating an event."""

    agent: str = Field(..., description="Agent name (architect, coder, etc.)")
    action: str = Field(..., description="Action type (start, end, error)")
    workflow: str | None = Field(None, description="Workflow name")
    parent: str | None = Field(None, description="Parent agent")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class Event(BaseModel):
    """Full event model with timestamp."""

    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO timestamp"
    )
    agent: str
    action: str
    workflow: str | None = None
    parent: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_create(cls, event_create: EventCreate) -> "Event":
        """Create an Event from EventCreate."""
        return cls(
            agent=event_create.agent,
            action=event_create.action,
            workflow=event_create.workflow,
            parent=event_create.parent,
            metadata=event_create.metadata,
        )


class MonitorState(BaseModel):
    """Current state of the monitor."""

    active_agent: str | None = None
    active_workflow: str | None = None
    started_at: str | None = None
    event_count: int = 0
