from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.sql import and_

from src.database_tasks import get_sync_db
from src.models.payments import Payment
from src.schemas.user import PaymentRead, PaymentCreate, PaymentIdRead
from src.services.payment_service import create_payment, get_payment
from src.utils.logging import setup_logging

logger = setup_logging()
router = APIRouter()


@router.post("/", response_model=PaymentIdRead)
def create_payment_endpoint(payment_data: PaymentCreate, db: Session = Depends(get_sync_db)):
    try:
        new_payment = create_payment(db, payment_data)
        logger.info(f"Payment created successfully with firebase_id={new_payment.firebase_id}")
        return new_payment

    except Exception as e:
        logger.error(f"Error creating payment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{payment_id}", response_model=PaymentRead)
def get_payment_endpoint(payment_id: int, db: Session = Depends(get_sync_db)):
    payment = get_payment(db, payment_id)
    if payment is None:
        logger.error(f"Payment with firebase_id={payment_id} not found")
        raise HTTPException(status_code=404, detail="Payment Not Found")
    return payment


@router.get("/", response_model=List[PaymentRead])
def get_all_payments(
        db: Session = Depends(get_sync_db),
        firebase_id: Optional[str] = "",
):
    logger.info("Fetching all payments")
    query = select(Payment)
    if firebase_id:
        query = query.where(and_(Payment.firebase_id == firebase_id))

    result = db.execute(query)
    return result.scalars().all()
