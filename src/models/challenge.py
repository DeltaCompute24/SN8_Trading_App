from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, JSON
from sqlalchemy.orm import relationship

from src.database import Base


class Challenge(Base):
    __tablename__ = "challenges"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trader_id = Column(Integer, nullable=False)
    hot_key = Column(String, nullable=False)
    active = Column(String, nullable=False)
    status = Column(String, nullable=True, default="")
    challenge = Column(String, nullable=False)
    challenge_name = Column(String, nullable=True, default="")
    step = Column(Integer, nullable=True)
    phase = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    register_on_test_net = Column(DateTime, default=datetime.utcnow, nullable=True)
    register_on_main_net = Column(DateTime, nullable=True)
    pass_the_challenge = Column(DateTime, nullable=True)
    pass_the_main_net_challenge = Column(DateTime, nullable=True)
    draw_down = Column(Float, nullable=True)
    profit_sum = Column(Float, nullable=True)
    score = Column(Float, nullable=True)
    response = Column(JSON, nullable=True)
    message = Column(String, nullable=False)
    hotkey_status = Column(String, nullable=False)

    # Foreign key to reference the FirebaseUser
    user_id = Column(Integer, ForeignKey("firebase_users.id"))

    # Many-to-one relationship: A challenge belongs to one user
    user = relationship("FirebaseUser", back_populates="challenges")

    # One-to-one relationship with Payment
    payment = relationship("Payment", back_populates="challenge", uselist=False)

    # Foreign key to reference the Tournament
    tournament_id = Column(Integer, ForeignKey("tournament.id"))

    # Many-to-one relationship with Tournament
    tournament = relationship("Tournament", back_populates="challenges")
