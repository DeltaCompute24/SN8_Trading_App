from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from src.database import Base


class Challenge(Base):
    __tablename__ = "challenges"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trader_id = Column(Integer, nullable=False)
    hot_key = Column(String, nullable=False)
    status = Column(String, nullable=False)
    challenge = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Foreign key to reference the FirebaseUser
    user_id = Column(Integer, ForeignKey("firebase_users.id"))

    # Many-to-one relationship: A challenge belongs to one user
    user = relationship("FirebaseUser", back_populates="challenges")
