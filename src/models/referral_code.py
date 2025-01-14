from datetime import date , datetime , timezone
from sqlalchemy import Column, ForeignKey, Integer, String,Boolean, Date, DateTime, Table,CheckConstraint
from sqlalchemy.orm import relationship, Mapped
from src.database import Base
from typing import List
from enum import Enum
from sqlalchemy import Enum as SQLAlchemyEnum


class ChallengeType(str, Enum):
    MAIN = 'main'
    TEST = 'test'
    TOURNAMENT = 'tournament'
    
    def _generate_next_value_(name, start, count, last_values):
        return name.lower()  

    def __str__(self):
        return self.value
    
    
    
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
    discount_fixed: Mapped[int] = Column(Integer(), default=0)
    challenge_type: Mapped[ChallengeType] = Column(  # Add type hint
        SQLAlchemyEnum(
            ChallengeType,
            name='challenge_type',
            create_constraint=True,
            validate_strings=True,
            native_enum=True,
            values_callable=lambda obj: [e.value for e in obj]  # Ensure values are used
        ),
        nullable=False,
        default=ChallengeType.TEST
    )
    __table_args__ = (
        CheckConstraint(
            'discount_percentage >= 0 AND discount_percentage <= 100',
            name='check_discount_percentage_range'
        ),
    )

