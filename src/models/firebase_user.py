from datetime import datetime
from src.models.referral_code import ReferralCode, user_referral_codes

from sqlalchemy import Column, Integer, String, DateTime, ARRAY
from sqlalchemy.orm import relationship, Mapped
from typing import List
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
    used_codes: Mapped[List["ReferralCode"]] = relationship(
        "ReferralCode",
        secondary=user_referral_codes,
        back_populates="users",
        cascade="all, delete"
    )
    generated_codes: Mapped[List["ReferralCode"]] = relationship(
        "ReferralCode",
        back_populates="generated_by",
        cascade="all, delete"
    )
    
    favorite_trade_pairs: Mapped[List[str]] = Column(ARRAY(String), default=list)
    