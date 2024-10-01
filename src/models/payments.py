from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey
from sqlalchemy.orm import relationship

from src.database import Base


class Payment(Base):
    __tablename__ = "payments"

    fid = Column(Integer, primary_key=True, autoincrement=True)
    amount = Column(Float, nullable=False)
    referral_code = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Back-reference to Challenge
    challenge_id = Column(Integer, ForeignKey("challenges.id"), unique=True)
    challenge = relationship("Challenge", back_populates="payment")
