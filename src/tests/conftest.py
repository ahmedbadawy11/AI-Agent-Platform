"""
Shared pytest fixtures: in-memory SQLite database, FastAPI test client, mock OpenAI provider.
"""
import sys
import asyncio
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

src_dir = Path(__file__).resolve().parent.parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from models.ai_agent_platform_DB.schemes import SQLAlchemyBase


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture()
async def db_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(SQLAlchemyBase.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(SQLAlchemyBase.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture()
async def db_session_factory(db_engine):
    return sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)


def _make_mock_openai_provider():
    provider = MagicMock()
    provider.generate_chat.return_value = "Hello from the assistant!"
    provider.generate_chat_stream.return_value = iter(["Hello ", "from ", "stream!"])
    provider.speech_to_text.return_value = "transcribed text"
    provider.text_to_speech.return_value = b"\x00\x01\x02\x03"
    provider.text_to_speech_stream.return_value = iter([b"\x00\x01", b"\x02\x03"])
    provider.tts_voice = "alloy"
    return provider


@pytest_asyncio.fixture()
async def app(db_session_factory):
    from main import app as fastapi_app

    fastapi_app.db_client = db_session_factory
    fastapi_app.openai_provider = _make_mock_openai_provider()
    return fastapi_app


@pytest_asyncio.fixture()
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
