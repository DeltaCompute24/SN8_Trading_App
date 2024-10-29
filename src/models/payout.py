from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship, Mapped
from src.database import Base
from src.models.firebase_user import FirebaseUser


class Payout(Base):
    __tablename__ = "payouts"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Foreign key to reference the FirebaseUser
    user_id: int = Column(Integer, ForeignKey("firebase_users.id"), nullable=False)
    user: Mapped["FirebaseUser"] = relationship("FirebaseUser")

    # Enum will not be used, because is harder to migrate changes in postgres
    # and also is not compatible with all databases
    type: str = Column(String, nullable=False)

    # Wire type
    first_name: str = Column(String, nullable=True)
    last_name: str = Column(String, nullable=True)
    address: str = Column(String, nullable=True)
    iban: str = Column(String, nullable=True)
    bank_name: str = Column(String, nullable=True)
    bank_address: str = Column(String, nullable=True)
    bank_country: str = Column(String, nullable=True)
    bic_swift_code: str = Column(String, nullable=True)

    # Crypto type
    usdt_address: str = Column(String, nullable=True)
    tao_address: str = Column(String, nullable=True)
