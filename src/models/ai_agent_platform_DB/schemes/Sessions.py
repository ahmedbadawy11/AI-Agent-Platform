from datetime import datetime

from .ai_agent_base import SQLAlchemyBase
from sqlalchemy import Column, Integer, DateTime, ForeignKey,func
from sqlalchemy.orm import relationship
from sqlalchemy import Index


class Session(SQLAlchemyBase):
    __tablename__ = "sessions"

    session_id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(Integer, ForeignKey("agents.agent_id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True),  onupdate=func.now(),nullable=True)

    agent = relationship("Agent", back_populates="sessions")
    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_session_agent_id", "agent_id"),
    )