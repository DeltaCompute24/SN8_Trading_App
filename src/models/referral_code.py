from datetime import date , datetime
from sqlalchemy import Column, ForeignKey, Integer, String,Boolean, Date, DateTime, Table
from sqlalchemy.orm import relationship, Mapped
from src.database import Base
from src.models.firebase_user import FirebaseUser
from sqlalchemy.sql import func
from typing import List

# Create association table
user_referral_codes = Table(
    'user_referral_codes',
    Base.metadata,
    Column('user_id', String, ForeignKey('firebase_users.firebase_id', ondelete="CASCADE")),
    Column('referral_code_id', Integer, ForeignKey('referral_codes.id', ondelete="CASCADE")),
)

class ReferralCode(Base):
    __tablename__ = "referral_codes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Replace the direct foreign key with many-to-many relationship
    users: Mapped[List["FirebaseUser"]] = relationship(
        "FirebaseUser",
        secondary=user_referral_codes,
        back_populates="referral_codes"
    )
    
    code: Mapped[str] = Column(String(length=7), nullable=False)
    created_at = Column(DateTime, default=datetime.now(datetime.UTC))
    updated_at = Column(DateTime, default=datetime.now(datetime.UTC), onupdate=datetime.now(datetime.UTC))
    is_valid: Mapped[bool] = Column(Boolean, default=False)
    discount_percentage: Mapped[int] = Column(Integer, default=0 , max_length=100)
    valid_from: Mapped[date] = Column(Date, default=date.today())
    valid_to: Mapped[date] = Column(Date, default=None, nullable=True)
    multiple_use :Mapped[bool] = Column(Boolean, default=False)

