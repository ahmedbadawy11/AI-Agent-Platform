"""
Agent management endpoints: list, get, create, update, delete.
"""
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from models.AgentModel import AgentModel
from models.ai_agent_platform_DB.schemes import Agent
from routes.schemes import (
    AgentCreate,
    AgentUpdate,
    AgentResponse,
    ErrorResponse,
)

agents_router = APIRouter()


def get_db(request: Request):
    return request.app.db_client


def agent_to_response(a) -> AgentResponse:
    return AgentResponse(
        agent_id=a.agent_id,
        name=a.name,
        prompt=a.prompt,
        voice_id=a.voice_id,
        created_at=a.created_at.isoformat() if a.created_at else None,
        updated_at=a.updated_at.isoformat() if a.updated_at else None,
    )


@agents_router.get("", summary="List all agents", response_model=list[AgentResponse])
async def list_agents(request: Request):
    model = AgentModel(get_db(request))
    agents = await model.list_all()
    return [agent_to_response(a) for a in agents]




@agents_router.post("", summary="Create agent", response_model=AgentResponse)
async def create_agent(request: Request, body: AgentCreate):
    model = AgentModel(get_db(request))
    created = await model.create_agent(Agent(name=body.name, prompt=body.prompt, voice_id=body.voice_id))
    return agent_to_response(created)


@agents_router.put("/{agent_id}", summary="Update agent", response_model=AgentResponse, responses={404: {"model": ErrorResponse}})
async def update_agent(request: Request, agent_id: int, body: AgentUpdate):
    model = AgentModel(get_db(request))
    agent = await model.get_by_id(agent_id)
    if agent is None:
        return JSONResponse(status_code=404, content=ErrorResponse(detail="Agent not found").model_dump())
    if body.name is not None:
        agent.name = body.name
    if body.prompt is not None:
        agent.prompt = body.prompt
    if body.voice_id is not None:
        agent.voice_id = body.voice_id
    updated = await model.update_agent(agent)
    return agent_to_response(updated)



