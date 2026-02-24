"""
Conversation: message history and sending messages (text + voice).
Single goal — support UI: type/send message, record audio and send, show user message and AI response.
"""
import json
from datetime import datetime, timezone

from openai import APIConnectionError
import httpx

from models.AgentModel import AgentModel
from models.SessionModel import SessionModel
from models.MessageModel import MessageModel
from models.ai_agent_platform_DB.schemes import Message
from stores.LLMEnums import OpenAIEnums


def _message_to_dict(m):
    return {
        "message_id": m.message_id,
        "session_id": m.session_id,
        "role": m.role,
        "content": m.content,
        "created_at": m.created_at.isoformat() if m.created_at else None,
    }


async def get_messages(db_client, session_id: int) -> list:
    """Get chronological message history for a session (chat history in UI)."""
    model = MessageModel(db_client)
    messages = await model.list_by_session(session_id)
    return [_message_to_dict(m) for m in messages]


def _build_openai_messages(agent_prompt: str, history: list) -> list[dict]:
    out = [{"role": OpenAIEnums.ROLE_SYSTEM.value, "content": agent_prompt}]
    for m in history:
        out.append({"role": m.role, "content": m.content})
    return out


async def send_text_message(db_client, openai_provider, session_id: int, content: str) -> dict | None:
    """
    Send a text message: store user message, generate assistant reply (non-streaming), store it, return.
    Use for non-streaming clients.
    """
    session_model = SessionModel(db_client)
    message_model = MessageModel(db_client)
    agent_model = AgentModel(db_client)

    session = await session_model.get_by_id(session_id)
    if not session:
        return None
    agent = await agent_model.get_by_id(session.agent_id)
    if not agent:
        return None

    user_message = Message(session_id=session_id, role=OpenAIEnums.ROLE_USER.value, content=content)
    await message_model.create_message(user_message)

    history = await message_model.list_by_session(session_id)
    openai_messages = _build_openai_messages(agent.prompt, history)
    try:
        assistant_content = openai_provider.generate_chat(openai_messages)
    except (APIConnectionError, httpx.ConnectError):
        return None
    if assistant_content is None:
        return None

    assistant_message = Message(session_id=session_id, role=OpenAIEnums.ROLE_ASSISTANT.value, content=assistant_content)
    await message_model.create_message(assistant_message)
    session.updated_at = datetime.now(timezone.utc)
    await session_model.update_session(session)

    return _message_to_dict(assistant_message)


async def stream_text_message(db_client, openai_provider, session_id: int, content: str):
    """
    Send a text message with streaming: store user message, stream LLM response, persist assistant message when done.
    Yields SSE-style text chunks (data: {"content": chunk}); after stream, saves assistant message to DB.
    """
    session_model = SessionModel(db_client)
    message_model = MessageModel(db_client)
    agent_model = AgentModel(db_client)

    session = await session_model.get_by_id(session_id)
    if not session:
        yield 'data: {"error": "Session not found"}\n\n'
        return
    agent = await agent_model.get_by_id(session.agent_id)
    if not agent:
        yield 'data: {"error": "Agent not found"}\n\n'
        return

    user_message = Message(session_id=session_id, role=OpenAIEnums.ROLE_USER.value, content=content)
    await message_model.create_message(user_message)

    history = await message_model.list_by_session(session_id)
    openai_messages = _build_openai_messages(agent.prompt, history)
    accumulated = []
    try:
        for chunk in openai_provider.generate_chat_stream(openai_messages):
            accumulated.append(chunk)
            yield f"data: {json.dumps({'content': chunk})}\n\n"
    except (APIConnectionError, httpx.ConnectError):
        yield f'data: {json.dumps({"error": "Connection to LLM failed. Check OPENAI_API_KEY and network."})}\n\n'
        return
    finally:
        full_content = "".join(accumulated)
        if full_content:
            assistant_message = Message(
                session_id=session_id,
                role=OpenAIEnums.ROLE_ASSISTANT.value,
                content=full_content,
            )
            await message_model.create_message(assistant_message)
            session.updated_at = datetime.now(timezone.utc)
            await session_model.update_session(session)
    yield 'data: {"done": true}\n\n'


async def send_voice_message(db_client, openai_provider, session_id: int, audio_bytes: bytes, audio_filename: str = "audio.webm") -> tuple[bytes | None, str | None]:
    """
    Voice flow: STT -> store user message -> LLM -> store assistant message -> TTS.
    Returns (audio_bytes, error_message). Async request/response as per assessment.
    """
    session_model = SessionModel(db_client)
    message_model = MessageModel(db_client)
    agent_model = AgentModel(db_client)

    session = await session_model.get_by_id(session_id)
    if not session:
        return None, "Session not found"
    agent = await agent_model.get_by_id(session.agent_id)
    if not agent:
        return None, "Agent not found"

    try:
        text = openai_provider.speech_to_text(audio_bytes, filename=audio_filename)
    except (APIConnectionError, httpx.ConnectError):
        return None, "Connection to LLM failed. Check OPENAI_API_KEY and network."
    except Exception as e:
        return None, f"Speech-to-text error: {str(e)}"
    if not text or not text.strip():
        return None, "Speech-to-text produced no text"

    user_message = Message(session_id=session_id, role=OpenAIEnums.ROLE_USER.value, content=text.strip())
    await message_model.create_message(user_message)

    history = await message_model.list_by_session(session_id)
    openai_messages = _build_openai_messages(agent.prompt, history)
    try:
        assistant_content = openai_provider.generate_chat(openai_messages)
    except (APIConnectionError, httpx.ConnectError):
        return None, "Connection to LLM failed. Check OPENAI_API_KEY and network."
    if assistant_content is None:
        return None, "Failed to generate assistant response"

    assistant_message = Message(session_id=session_id, role=OpenAIEnums.ROLE_ASSISTANT.value, content=assistant_content)
    await message_model.create_message(assistant_message)
    session.updated_at = datetime.now(timezone.utc)
    await session_model.update_session(session)

    voice = getattr(openai_provider, "tts_voice", "alloy") or "alloy"
    try:
        audio_out = openai_provider.text_to_speech(assistant_content, voice=voice)
    except (APIConnectionError, httpx.ConnectError):
        return None, "Connection to LLM failed. Check OPENAI_API_KEY and network."
    if audio_out is None:
        return None, "Text-to-speech failed"
    return audio_out, None
