"""
Session endpoints: list by agent, get, create, delete.
"""
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from models.SessionModel import SessionModel
from models.ai_agent_platform_DB.schemes import Session
from routes.schemes import SessionResponse, DeletedResponse, ErrorResponse

sessions_router = APIRouter()


def get_db(request: Request):
    return request.app.db_client


def session_to_response(s) -> SessionResponse:
    return SessionResponse(
        session_id=s.session_id,
        agent_id=s.agent_id,
        created_at=s.created_at.isoformat() if s.created_at else None,
        updated_at=s.updated_at.isoformat() if s.updated_at else None,
    )


# More specific paths first so "sessions" is not captured as agent_id
@sessions_router.get("/sessions/{session_id}", summary="Get session by id", response_model=SessionResponse, responses={404: {"model": ErrorResponse}})
async def get_session(request: Request, session_id: int):
    model = SessionModel(get_db(request))
    session = await model.get_by_id(session_id)
    if session is None:
        return JSONResponse(status_code=404, content=ErrorResponse(detail="Session not found").model_dump())
    return session_to_response(session)


@sessions_router.delete("/sessions/{session_id}", summary="Delete session", response_model=DeletedResponse, responses={404: {"model": ErrorResponse}})
async def delete_session(request: Request, session_id: int):
    model = SessionModel(get_db(request))
    ok = await model.delete_session(session_id)
    if not ok:
        return JSONResponse(status_code=404, content=ErrorResponse(detail="Session not found").model_dump())
    return DeletedResponse()


@sessions_router.get("/{agent_id}/sessions", summary="List sessions for an agent", response_model=list[SessionResponse])
async def list_sessions(request: Request, agent_id: int):
    model = SessionModel(get_db(request))
    sessions = await model.list_by_agent(agent_id)
    return [session_to_response(s) for s in sessions]


@sessions_router.post("/{agent_id}/sessions", summary="Create a new chat session", response_model=SessionResponse)
async def create_session(request: Request, agent_id: int):
    model = SessionModel(get_db(request))
    created = await model.create_session(Session(agent_id=agent_id))
    return session_to_response(created)
