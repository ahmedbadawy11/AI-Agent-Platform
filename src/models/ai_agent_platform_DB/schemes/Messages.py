from datetime import datetime

from .ai_agent_base import SQLAlchemyBase
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey,func
from sqlalchemy.orm import relationship
from sqlalchemy import Index

class Message(SQLAlchemyBase):
    __tablename__ = "messages"

    message_id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("sessions.session_id", ondelete="CASCADE"), nullable=False)
    role = Column(String(32), nullable=False)  # "user" | "assistant" | "system"
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    session = relationship("Session", back_populates="messages")

    __table_args__ = (
        Index("idx_message_session_id", "session_id"),
    )
