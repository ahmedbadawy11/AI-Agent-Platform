"""
Tests for Agent management endpoints: create, list, update.
"""
import pytest


@pytest.mark.asyncio
async def test_list_agents_empty(client):
    resp = await client.get("/api/v1/agents")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_create_agent(client):
    payload = {"name": "Test Agent", "prompt": "You are a helpful assistant."}
    resp = await client.post("/api/v1/agents", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Test Agent"
    assert data["prompt"] == "You are a helpful assistant."
    assert "agent_id" in data
    assert data["created_at"] is not None


@pytest.mark.asyncio
async def test_create_agent_missing_fields(client):
    resp = await client.post("/api/v1/agents", json={"name": "No prompt"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_list_agents_after_create(client):
    await client.post("/api/v1/agents", json={"name": "A1", "prompt": "p1"})
    await client.post("/api/v1/agents", json={"name": "A2", "prompt": "p2"})
    resp = await client.get("/api/v1/agents")
    assert resp.status_code == 200
    agents = resp.json()
    assert len(agents) >= 2
    names = {a["name"] for a in agents}
    assert "A1" in names
    assert "A2" in names


@pytest.mark.asyncio
async def test_update_agent(client):
    create_resp = await client.post(
        "/api/v1/agents", json={"name": "Original", "prompt": "p"}
    )
    agent_id = create_resp.json()["agent_id"]

    update_resp = await client.put(
        f"/api/v1/agents/{agent_id}", json={"name": "Updated"}
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["name"] == "Updated"
    assert update_resp.json()["prompt"] == "p"


@pytest.mark.asyncio
async def test_update_agent_prompt_only(client):
    create_resp = await client.post(
        "/api/v1/agents", json={"name": "Keep", "prompt": "old"}
    )
    agent_id = create_resp.json()["agent_id"]

    update_resp = await client.put(
        f"/api/v1/agents/{agent_id}", json={"prompt": "new prompt"}
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["name"] == "Keep"
    assert update_resp.json()["prompt"] == "new prompt"


@pytest.mark.asyncio
async def test_update_nonexistent_agent(client):
    resp = await client.put("/api/v1/agents/99999", json={"name": "x"})
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()
