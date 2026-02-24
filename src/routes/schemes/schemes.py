"""
Pydantic request and response schemas for API endpoints (single module).
"""
from pydantic import BaseModel


# ----- Error (for JSONResponse) -----


class ErrorResponse(BaseModel):
    """Schema for error responses returned as JSONResponse."""

    detail: str


# ----- Common -----


class DeletedResponse(BaseModel):
    """Response for successful delete operations."""

    deleted: bool = True


# ----- Agents -----


class AgentCreate(BaseModel):
    """Request body for creating an agent."""

    name: str
    prompt: str


class AgentUpdate(BaseModel):
    """Request body for updating an agent (all fields optional)."""

    name: str | None = None
    prompt: str | None = None


class AgentResponse(BaseModel):
    """Response for a single agent (get, create, update)."""

    agent_id: int
    name: str
    prompt: str
    created_at: str | None
    updated_at: str | None


# ----- Sessions -----


class SessionResponse(BaseModel):
    """Response for a single session (get, create)."""

    session_id: int
    agent_id: int
    created_at: str | None
    updated_at: str | None


# ----- Chat / Messages -----


class SendMessageRequest(BaseModel):
    """Request body for sending a text message (session_id + content)."""

    session_id: int
    content: str


class MessageResponse(BaseModel):
    """Response for a single message (e.g. assistant reply)."""

    message_id: int
    session_id: int
    role: str
    content: str
    created_at: str | None
