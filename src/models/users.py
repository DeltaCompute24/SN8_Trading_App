from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy import JSON, UniqueConstraint

from src.database import Base


class Users(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trader_id = Column(Integer, nullable=False)
    hot_key = Column(JSON, nullable=False)
    current_challenge_level = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (UniqueConstraint('trader_id', name='user_trade'),)
