from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database_tasks import TaskSessionLocal_
from src.models.payments import Payment
from src.schemas.user import PaymentRead, PaymentCreate, PaymentUpdate
from src.services.payment_service import create_payment, get_payment, update_payment, delete_payment
from src.utils.logging import setup_logging

logger = setup_logging()
router = APIRouter()


# Dependency
async def get_db():
    async with TaskSessionLocal_() as db:
        yield db


# Create Payment
@router.post("/", response_model=PaymentRead)
async def create_payment_endpoint(payment_data: PaymentCreate, db: AsyncSession = Depends(get_db)):
    logger.info("Creating a new payment")

    try:
        new_payment = await create_payment(db, payment_data)
        logger.info(f"Payment created successfully with fid={new_payment.fid}")
        return new_payment

    except Exception as e:
        logger.error(f"Error creating payment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Read Payment
@router.get("/{payment_id}", response_model=PaymentRead)
async def get_payment_endpoint(payment_id: int, db: AsyncSession = Depends(get_db)):
    payment = await get_payment(db, payment_id)
    if payment is None:
        logger.error(f"Payment with fid={payment_id} not found")
        raise HTTPException(status_code=404, detail="Payment Not Found")
    return payment


# Read All Payments
@router.get("/", response_model=List[PaymentRead])
async def get_all_payments(db: AsyncSession = Depends(get_db)):
    logger.info("Fetching all payments")
    payments = await db.execute(select(Payment))
    return payments.scalars().all()


# Update Payment
@router.put("/{payment_id}", response_model=PaymentRead)
async def update_payment_endpoint(payment_id: int, payment_data: PaymentUpdate, db: AsyncSession = Depends(get_db)):
    logger.info(f"Updating payment with fid={payment_id}")

    payment = await update_payment(db, payment_id, payment_data)
    if payment is None:
        logger.error(f"Payment with fid={payment_id} not found")
        raise HTTPException(status_code=404, detail="Payment Not Found")

    logger.info(f"Payment updated successfully with fid={payment.fid}")
    return payment


# Delete Payment
@router.delete("/{payment_id}", response_model=dict)
async def delete_payment_endpoint(payment_id: int, db: AsyncSession = Depends(get_db)):
    logger.info(f"Deleting payment with fid={payment_id}")

    payment = await delete_payment(db, payment_id)
    if payment is None:
        logger.error(f"Payment with fid={payment_id} not found")
        raise HTTPException(status_code=404, detail="Payment Not Found")

    logger.info(f"Payment with fid={payment_id} deleted successfully")
    return {"detail": "Payment deleted successfully"}
