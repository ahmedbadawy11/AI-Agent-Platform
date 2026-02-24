"""
Conversation: message history and sending messages (text + voice).
Single goal — support UI: type/send message, record audio and send, show user message and AI response.
"""
import json
import re
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


_SENTENCE_END = re.compile(r'(?<=[.!?。？！])\s+')


def _split_sentences(text: str) -> list[str]:
    """Split text on sentence-ending punctuation followed by whitespace."""
    parts = _SENTENCE_END.split(text)
    return [p for p in parts if p.strip()]


def run_voice_stt(openai_provider, audio_bytes: bytes, audio_filename: str = "audio.webm") -> tuple[str | None, str | None]:
    """
    Run STT separately so the router can return a proper error HTTP response
    before committing to a streaming response.
    Returns (transcribed_text, error_message).
    """
    try:
        text = openai_provider.speech_to_text(audio_bytes, filename=audio_filename)
    except (APIConnectionError, httpx.ConnectError):
        return None, "Connection to LLM failed. Check OPENAI_API_KEY and network."
    except Exception as e:
        return None, f"Speech-to-text error: {str(e)}"
    if not text or not text.strip():
        return None, "Speech-to-text produced no text"
    return text.strip(), None


async def stream_voice_after_stt(db_client, openai_provider, session_id: int, user_text: str):
    """
    Streaming voice flow (called after STT succeeds):
    Store user message -> stream LLM by sentences -> TTS each sentence -> yield events.
    Yields (event_type, data) tuples:
      ("user_text", str)       — the transcribed user message (show in UI immediately)
      ("assistant_text", str)  — LLM text chunk (show in UI as it streams)
      ("audio", bytes)         — raw mp3 bytes for playback
      ("error", str)           — error (stream will end)
      ("done", "")             — signals end of stream
    """
    session_model = SessionModel(db_client)
    message_model = MessageModel(db_client)
    agent_model = AgentModel(db_client)

    session = await session_model.get_by_id(session_id)
    if not session:
        yield ("error", "Session not found")
        return
    agent = await agent_model.get_by_id(session.agent_id)
    if not agent:
        yield ("error", "Agent not found")
        return

    user_message = Message(session_id=session_id, role=OpenAIEnums.ROLE_USER.value, content=user_text)
    await message_model.create_message(user_message)

    yield ("user_text", user_text)

    history = await message_model.list_by_session(session_id)
    openai_messages = _build_openai_messages(agent.prompt, history)

    voice = getattr(openai_provider, "tts_voice", "alloy") or "alloy"
    accumulated_llm = []
    sentence_buffer = ""

    try:
        for chunk in openai_provider.generate_chat_stream(openai_messages):
            accumulated_llm.append(chunk)
            sentence_buffer += chunk
            yield ("assistant_text", chunk)

            sentences = _split_sentences(sentence_buffer)
            if len(sentences) > 1:
                for sentence in sentences[:-1]:
                    for audio_chunk in openai_provider.text_to_speech_stream(sentence, voice=voice):
                        yield ("audio", audio_chunk)
                sentence_buffer = sentences[-1]
    except (APIConnectionError, httpx.ConnectError):
        yield ("error", "Connection to LLM failed. Check OPENAI_API_KEY and network.")
        return

    if sentence_buffer.strip():
        try:
            for audio_chunk in openai_provider.text_to_speech_stream(sentence_buffer, voice=voice):
                yield ("audio", audio_chunk)
        except (APIConnectionError, httpx.ConnectError):
            yield ("error", "Connection to LLM failed during final TTS.")
            return

    full_content = "".join(accumulated_llm)
    if full_content:
        assistant_message = Message(
            session_id=session_id,
            role=OpenAIEnums.ROLE_ASSISTANT.value,
            content=full_content,
        )
        await message_model.create_message(assistant_message)
        session.updated_at = datetime.now(timezone.utc)
        await session_model.update_session(session)

    yield ("done", "")
