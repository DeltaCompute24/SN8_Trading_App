from datetime import datetime

from sqlalchemy import Column, Integer, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship

from src.database import Base


class Tournament(Base):
    __tablename__ = "tournament"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Back-reference to Challenge
    challenge_id = Column(Integer, ForeignKey("challenges.id"), unique=True)
    challenge = relationship("Challenge", back_populates="tournament")
