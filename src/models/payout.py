from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship, Mapped
from src.database import Base
from src.models.firebase_user import FirebaseUser


class Payout(Base):
    __tablename__ = "payouts"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Foreign key to reference the FirebaseUser
    user_id: str = Column(String, ForeignKey("firebase_users.firebase_id", ondelete="SET NULL"), nullable=False)
    user: Mapped["FirebaseUser"] = relationship("FirebaseUser", back_populates = "payout" , uselist=False)

    # Enum will not be used, because is harder to migrate changes in postgres
    # and also is not compatible with all databases
    type: Mapped[str] = Column(String, nullable=False)

    # Wire type
    first_name: Mapped[str] = Column(String, nullable=True)
    last_name: Mapped[str] = Column(String, nullable=True)
    address: Mapped[str] = Column(String, nullable=True)
    iban: Mapped[str] = Column(String, nullable=True)
    bank_name: Mapped[str] = Column(String, nullable=True)
    bank_address: Mapped[str] = Column(String, nullable=True)
    bank_country: Mapped[str] = Column(String, nullable=True)
    bic_swift_code: Mapped[str] = Column(String, nullable=True)

    # Crypto type
    usdt_address: Mapped[str] = Column(String, nullable=True)
    tao_address: Mapped[str] = Column(String, nullable=True)
