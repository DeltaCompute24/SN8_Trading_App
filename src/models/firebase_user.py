from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship

from src.database import Base


class FirebaseUser(Base):
    __tablename__ = "firebase_users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    firebase_id = Column(String, nullable=False, unique=True)
    email = Column(String, nullable=True)
    name = Column(String, nullable=True)
    username = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # One-to-many relationship: A user can have multiple challenges
    challenges = relationship("Challenge", back_populates="user")
    payout = relationship("Payout", back_populates="user")
