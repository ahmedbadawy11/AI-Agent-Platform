from .BaseDatamodel import BaseDatamodel
from .ai_agent_platform_DB.schemes import Session
from sqlalchemy import select


class SessionModel(BaseDatamodel):
    def __init__(self, db_client: object):
        super().__init__(db_client=db_client)
        self.db_client = db_client

    async def get_by_id(self, session_id: int) -> Session | None:
        """Get one session by id."""
        async with self.db_client() as db_session:
            result = await db_session.execute(
                select(Session).where(Session.session_id == session_id)
            )
            return result.scalar_one_or_none()

    async def list_by_agent(self, agent_id: int) -> list[Session]:
        """List all chat sessions for an agent (Assessment: multiple chat sessions per agent)."""
        async with self.db_client() as db_session:
            result = await db_session.execute(
                select(Session)
                .where(Session.agent_id == agent_id)
                .order_by(Session.updated_at.desc())
            )
            return list(result.scalars().all())

    async def create_session(self, session: Session) -> Session:
        """Start a new chat session for an agent (Assessment: create a new chat)."""
        async with self.db_client() as db_session:
            async with db_session.begin():
                db_session.add(session)
            await db_session.commit()
            await db_session.refresh(session)
        return session

    async def update_session(self, session: Session) -> Session:
        """Update session (e.g. updated_at on new message)."""
        async with self.db_client() as db_session:
            merged = await db_session.merge(session)
            await db_session.commit()
            await db_session.refresh(merged)
        return merged

    async def delete_session(self, session_id: int) -> bool:
        """Delete a session by id. Returns True if deleted."""
        async with self.db_client() as db_session:
            async with db_session.begin():
                result = await db_session.execute(
                    select(Session).where(Session.session_id == session_id)
                )
                session = result.scalar_one_or_none()
                if session is None:
                    return False
                await db_session.delete(session)
                await db_session.commit()
        return True
