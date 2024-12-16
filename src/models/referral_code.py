from datetime import date , datetime , timezone
from sqlalchemy import Column, ForeignKey, Integer, String,Boolean, Date, DateTime, Table
from sqlalchemy.orm import relationship, Mapped
from src.database import Base
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
    
    
    generated_by_id = Column(String, ForeignKey('firebase_users.email', ondelete="SET NULL"), nullable=True)
    generated_by = relationship(
        "FirebaseUser",
        foreign_keys=[generated_by_id],
        back_populates="generated_codes"
    )
    
    # Fix: Specify the type in List[]
    users = relationship(
        "FirebaseUser",
        secondary=user_referral_codes,
        back_populates="used_codes"
    )
    
    code: Mapped[str] = Column(String(length=30), nullable=False, unique=True)
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    is_valid: Mapped[bool] = Column(Boolean, default=True)
    discount_percentage: Mapped[int] = Column(Integer, default=0)
    valid_from: Mapped[date] = Column(Date, default=date.today())
    valid_to: Mapped[date] = Column(Date, default=None, nullable=True)
    multiple_use :Mapped[bool] = Column(Boolean, default=False)

