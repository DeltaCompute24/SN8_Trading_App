from sqlalchemy import Column, Integer, String, Numeric, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class UsersBalance(Base):
    __tablename__ = "users_balance"

    trader_id = Column(Integer, primary_key=True)
    hot_key = Column(String, primary_key=True)
    balance = Column(Numeric(30, 4), nullable=False, default=0)
    balance_as_on = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)