from .BaseDatamodel import BaseDatamodel
from .ai_agent_platform_DB.schemes import Message
from sqlalchemy import select


class MessageModel(BaseDatamodel):
    def __init__(self, db_client: object):
        super().__init__(db_client=db_client)
        self.db_client = db_client

    async def get_by_id(self, message_id: int) -> Message | None:
        """Get one message by id."""
        async with self.db_client() as db_session:
            result = await db_session.execute(
                select(Message).where(Message.message_id == message_id)
            )
            return result.scalar_one_or_none()

    async def list_by_session(self, session_id: int) -> list[Message]:
        """List messages in a session in chronological order (Assessment: chronological history)."""
        async with self.db_client() as db_session:
            result = await db_session.execute(
                select(Message)
                .where(Message.session_id == session_id)
                .order_by(Message.created_at.asc())
            )
            return list(result.scalars().all())

    async def create_message(self, message: Message) -> Message:
        """Store a user or agent message (Assessment: all messages stored in DB)."""
        async with self.db_client() as db_session:
            async with db_session.begin():
                db_session.add(message)
            await db_session.commit()
            await db_session.refresh(message)
        return message

    async def delete_message(self, message_id: int) -> bool:
        """Delete a message by id. Returns True if deleted."""
        async with self.db_client() as db_session:
            async with db_session.begin():
                result = await db_session.execute(
                    select(Message).where(Message.message_id == message_id)
                )
                message = result.scalar_one_or_none()
                if message is None:
                    return False
                await db_session.delete(message)
                await db_session.commit()
        return True
