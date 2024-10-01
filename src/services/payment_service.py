from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from src.models.payments import Payment
from src.schemas.user import PaymentCreate, PaymentUpdate
from sqlalchemy.sql import and_


async def get_payment(db: AsyncSession, payment_id: int):
    payment = await db.scalar(
        select(Payment).where(
            and_(
                Payment.fid == payment_id
            )
        )
    )
    return payment


async def create_payment(db: AsyncSession, payment_data: PaymentCreate):
    new_payment = Payment(
        amount=payment_data.amount,
        referral_code=payment_data.referral_code,
        challenge_id=payment_data.challenge_id
    )
    db.add(new_payment)
    await db.commit()
    await db.refresh(new_payment)
    return new_payment


async def update_payment(db: AsyncSession, payment_id: int, payment_data: PaymentUpdate):
    payment = await get_payment(db, payment_id)
    if not payment:
        return None

    if payment_data.amount is not None:
        payment.amount = payment_data.amount
    if payment_data.referral_code is not None:
        payment.referral_code = payment_data.referral_code

    await db.commit()
    await db.refresh(payment)
    return payment


async def delete_payment(db: AsyncSession, payment_id: int):
    payment = await get_payment(db, payment_id)
    if not payment:
        return None

    await db.delete(payment)
    await db.commit()
    return payment
