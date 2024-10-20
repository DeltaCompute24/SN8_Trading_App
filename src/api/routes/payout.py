from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.database_tasks import TaskSessionLocal_

from src.schemas.payout import PayoutSaveSchema, PayoutSchema
from src.services.payout_service import get_payout, save_payout
from src.utils.logging import setup_logging

logger = setup_logging()
router = APIRouter()


def get_db():
    db = TaskSessionLocal_()
    try:
        yield db
    finally:
        db.close()


@router.post("/", response_model=PayoutSchema)
def save_payout_information(
    payout_data: PayoutSaveSchema, db: Session = Depends(get_db)
):
    payout = save_payout(db, payout_data)
    return payout


@router.get("/{firebase_id}", response_model=PayoutSchema)
def get_payout_information(firebase_id: str, db: Session = Depends(get_db)):
    payout = get_payout(db, firebase_id)
    logger.info(f"Retrieved payout information for firebase_id={firebase_id}")

    if not payout:
        logger.info(f"No payout information found for firebase_id={firebase_id}")
        raise HTTPException(status_code=404, detail="Payout Not Found!")

    return payout
