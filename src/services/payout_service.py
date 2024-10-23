from typing import Optional
from sqlalchemy.orm import Session

from src.models.payout import Payout
from src.schemas.payout import PayoutSaveSchema, PayoutSchema

from src.services.user_service import create_firebase_user
from src.utils.logging import setup_logging

logger = setup_logging()


def get_payout(db: Session, firebase_id: str) -> Optional[Payout]:
    payout_information = (
        db.query(Payout).filter(Payout.user.has(firebase_id=firebase_id)).first()
    )

    return payout_information


def save_payout(db: Session, payout_data: PayoutSaveSchema) -> Payout:
    firebase_user = create_firebase_user(db, payout_data.firebase_id)
    payout = db.query(Payout).filter(Payout.user == firebase_user).first()
    is_new = payout is None

    if is_new:
        payout = Payout(user=firebase_user)

    payout.type = payout_data.type.value

    payout_data_dict = payout_data.model_dump(
        exclude_unset=True, exclude={"type", "firebase_id"}
    )

    for key, value in payout_data_dict.items():
        # Check if the Payout model has the attribute before setting it
        if hasattr(payout, key):
            setattr(payout, key, value)
        else:
            logger.warning(f"Attribute {key} not found on Payout model")

    if is_new:
        db.add(payout)

    db.commit()
    db.refresh(payout)

    return payout
