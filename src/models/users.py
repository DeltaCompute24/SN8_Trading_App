from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy import UniqueConstraint

from src.database import Base


class Users(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trader_id = Column(Integer, nullable=True)
    hot_key = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (UniqueConstraint('hot_key', name='user_hot_key'),)
