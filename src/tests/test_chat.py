"""
Tests for Chat endpoints: list messages, send message (JSON), stream message (SSE), send voice.
"""
import pytest


async def _setup_session(client):
    agent = await client.post(
        "/api/v1/agents", json={"name": "ChatBot", "prompt": "You are helpful."}
    )
    agent_id = agent.json()["agent_id"]
    session = await client.post(f"/api/v1/agents/{agent_id}/sessions")
    return session.json()["session_id"]


@pytest.mark.asyncio
async def test_list_messages_empty(client):
    session_id = await _setup_session(client)
    resp = await client.get(f"/api/v1/sessions/session-messages?session_id={session_id}")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_send_message(client):
    session_id = await _setup_session(client)
    resp = await client.post(
        "/api/v1/sessions/send-message",
        json={"session_id": session_id, "content": "Hello!"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["role"] == "assistant"
    assert data["content"] == "Hello from the assistant!"
    assert data["session_id"] == session_id


@pytest.mark.asyncio
async def test_messages_stored_after_send(client):
    session_id = await _setup_session(client)
    await client.post(
        "/api/v1/sessions/send-message",
        json={"session_id": session_id, "content": "Hi there"},
    )
    resp = await client.get(f"/api/v1/sessions/session-messages?session_id={session_id}")
    messages = resp.json()
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "Hi there"
    assert messages[1]["role"] == "assistant"


@pytest.mark.asyncio
async def test_send_message_invalid_session(client):
    resp = await client.post(
        "/api/v1/sessions/send-message",
        json={"session_id": 99999, "content": "Hello"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_send_message_missing_content(client):
    session_id = await _setup_session(client)
    resp = await client.post(
        "/api/v1/sessions/send-message",
        json={"session_id": session_id},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_stream_message(client):
    session_id = await _setup_session(client)
    resp = await client.post(
        "/api/v1/sessions/stream-message",
        json={"session_id": session_id, "content": "Stream me"},
    )
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers["content-type"]
    body = resp.text
    assert "Hello " in body or "stream!" in body
    assert '"done": true' in body or '"done":true' in body


@pytest.mark.asyncio
async def test_send_voice_message(client):
    session_id = await _setup_session(client)
    audio_bytes = b"\x00\x01\x02\x03" * 100
    resp = await client.post(
        "/api/v1/sessions/send-voice-message",
        data={"session_id": str(session_id)},
        files={"audio": ("test.webm", audio_bytes, "audio/webm")},
    )
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers["content-type"]
    body = resp.text
    assert "user_text" in body
    assert "done" in body


@pytest.mark.asyncio
async def test_send_voice_message_no_audio(client):
    session_id = await _setup_session(client)
    resp = await client.post(
        "/api/v1/sessions/send-voice-message",
        data={"session_id": str(session_id)},
    )
    assert resp.status_code == 422
