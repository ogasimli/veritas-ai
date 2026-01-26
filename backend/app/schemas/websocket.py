"""Pydantic schemas for WebSocket messages."""

from typing import Literal

from pydantic import BaseModel


class AgentStartedMessage(BaseModel):
    """Message sent when an agent starts execution."""

    type: Literal["agent_started"]
    agent_id: str  # e.g. "numeric_validation", "logic_consistency"
    timestamp: str  # ISO format


class AgentCompletedMessage(BaseModel):
    """Message sent when an agent completes execution."""

    type: Literal["agent_completed"]
    agent_id: str
    findings: list[dict]  # Agent-specific finding structure
    timestamp: str  # ISO format


class AgentErrorMessage(BaseModel):
    """Message sent when an agent encounters an error."""

    type: Literal["agent_error"]
    agent_id: str
    error: str
    timestamp: str  # ISO format


class AuditCompleteMessage(BaseModel):
    """Message sent when the entire audit is complete."""

    type: Literal["audit_complete"]
    timestamp: str  # ISO format
