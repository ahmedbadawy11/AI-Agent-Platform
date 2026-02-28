from datetime import datetime

from .ai_agent_base import SQLAlchemyBase
from sqlalchemy import Column, Integer, String, Text, DateTime,func
from sqlalchemy.orm import relationship


class Agent(SQLAlchemyBase):
    __tablename__ = "agents"

    agent_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    prompt = Column(Text, nullable=False)
    voice_id = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True),  onupdate=func.now(),nullable=True)

    sessions = relationship("Session", back_populates="agent", cascade="all, delete-orphan")
