from datetime import datetime

from sqlalchemy import Column, Integer, DateTime, String, Float, Boolean, JSON
from sqlalchemy.orm import relationship

from src.database import Base


class Tournament(Base):
    __tablename__ = "tournament"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    winners = Column(JSON, nullable=True)
    winning_score = Column(Float, nullable=True)
    cost = Column(Float, nullable=True)
    prize = Column(Float, nullable=True)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # One-to-many relationship: A tournament can have multiple challenges
    challenges = relationship("Challenge", back_populates="tournament", cascade="all, delete-orphan")
