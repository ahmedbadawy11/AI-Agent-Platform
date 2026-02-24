"""
API router: agents, sessions, chat (text + voice).
Mounts under /api/v1 in main.py.
"""
from fastapi import APIRouter
from routes.agents_router import agents_router
from routes.sessions_router import sessions_router
from routes.chat_router import chat_router

api_router = APIRouter(tags=["AI Agent Platform"])

api_router.include_router(agents_router, prefix="/agents", tags=["Agents"])
api_router.include_router(sessions_router, prefix="/agents", tags=["Sessions"])
api_router.include_router(chat_router, prefix="/sessions", tags=["Chat & Voice"])
