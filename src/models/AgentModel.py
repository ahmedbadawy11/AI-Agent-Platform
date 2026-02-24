from .BaseDatamodel import BaseDatamodel
from .ai_agent_platform_DB.schemes import Agent
from sqlalchemy import select


class AgentModel(BaseDatamodel):
    def __init__(self, db_client: object):
        super().__init__(db_client=db_client)
        self.db_client = db_client

    async def get_by_id(self, agent_id: int) -> Agent | None:
        """Get one agent by id."""
        async with self.db_client() as session:
            result = await session.execute(select(Agent).where(Agent.agent_id == agent_id))
            return result.scalar_one_or_none()

    async def list_all(self) -> list[Agent]:
        """List all AI agents (Assessment: list of agents)."""
        async with self.db_client() as session:
            result = await session.execute(select(Agent).order_by(Agent.created_at))
            return list(result.scalars().all())

    async def create_agent(self, agent: Agent) -> Agent:
        """Create an AI agent (Assessment: add a new AI agent)."""
        async with self.db_client() as session:
            async with session.begin():
                session.add(agent)
            await session.commit()
            await session.refresh(agent)
        return agent

    async def update_agent(self, agent: Agent) -> Agent:
        """Update an existing agent (Assessment: edit agent)."""
        async with self.db_client() as session:
            merged = await session.merge(agent)
            await session.commit()
            await session.refresh(merged)
        return merged

    async def delete_agent(self, agent_id: int) -> bool:
        """Delete an agent by id. Returns True if deleted."""
        async with self.db_client() as session:
            async with session.begin():
                result = await session.execute(select(Agent).where(Agent.agent_id == agent_id))
                agent = result.scalar_one_or_none()
                if agent is None:
                    return False
                await session.delete(agent)
                await session.commit()
        return True
