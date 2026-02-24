"""
Tests for Session management endpoints: create, list by agent, get by id.
"""
import pytest


async def _create_agent(client, name="Bot", prompt="System prompt"):
    resp = await client.post("/api/v1/agents", json={"name": name, "prompt": prompt})
    assert resp.status_code == 200
    return resp.json()["agent_id"]


@pytest.mark.asyncio
async def test_create_session(client):
    agent_id = await _create_agent(client)
    resp = await client.post(f"/api/v1/agents/{agent_id}/sessions")
    assert resp.status_code == 200
    data = resp.json()
    assert data["agent_id"] == agent_id
    assert "session_id" in data


@pytest.mark.asyncio
async def test_list_sessions_for_agent(client):
    agent_id = await _create_agent(client)
    await client.post(f"/api/v1/agents/{agent_id}/sessions")
    await client.post(f"/api/v1/agents/{agent_id}/sessions")

    resp = await client.get(f"/api/v1/agents/{agent_id}/sessions")
    assert resp.status_code == 200
    sessions = resp.json()
    assert len(sessions) >= 2
    assert all(s["agent_id"] == agent_id for s in sessions)


@pytest.mark.asyncio
async def test_list_sessions_empty_agent(client):
    agent_id = await _create_agent(client, name="Empty")
    resp = await client.get(f"/api/v1/agents/{agent_id}/sessions")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_get_session_by_id(client):
    agent_id = await _create_agent(client)
    create_resp = await client.post(f"/api/v1/agents/{agent_id}/sessions")
    session_id = create_resp.json()["session_id"]

    resp = await client.get(f"/api/v1/agents/sessions/{session_id}")
    assert resp.status_code == 200
    assert resp.json()["session_id"] == session_id


@pytest.mark.asyncio
async def test_get_nonexistent_session(client):
    resp = await client.get("/api/v1/agents/sessions/99999")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()
