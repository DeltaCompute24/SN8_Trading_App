from sqlalchemy import Column, ForeignKey,DateTime, Integer, String
from sqlalchemy.orm import relationship, Mapped
from src.database import Base
from src.models.firebase_user import FirebaseUser
from datetime import datetime

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Foreign key to reference the FirebaseUser
    user_id: str = Column(String, ForeignKey("firebase_users.firebase_id", ondelete="CASCADE"), nullable=False)
    user: Mapped["FirebaseUser"] = relationship("FirebaseUser", back_populates = "notifications" , uselist=False)

    # Enum will not be used, because is harder to migrate changes in postgres
    # and also is not compatible with all databases
    type: Mapped[str] = Column(String, nullable=False)

    trader_id: Mapped[str] = Column(Integer, nullable=True)
    trader_pair: Mapped[str] = Column(String, nullable=True)
    message: Mapped[str] = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


