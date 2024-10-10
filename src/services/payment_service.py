from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.sql import and_

from src.models import Challenge
from src.models.payments import Payment
from src.schemas.user import PaymentCreate
from src.services.email_service import send_mail_in_thread
from src.services.user_service import create_firebase_user


def get_payment(db: Session, payment_id: int):
    payment = db.scalar(
        select(Payment).where(
            and_(
                Payment.id == payment_id
            )
        )
    )
    return payment


def create_payment(db: Session, payment_data: PaymentCreate):
    # Check if a payment with the same fid already exists
    existing_payment = db.query(Payment).filter(Payment.fid == payment_data.fid).first()

    if existing_payment:
        raise ValueError(f"Payment with fid {payment_data.fid} already exists.")

    firebase_user = create_firebase_user(db, payment_data.fid)

    new_challenge = Challenge(
        trader_id=0,
        hot_key="",
        user_id=firebase_user.id,
        active="0",
        challenge="test"
    )
    db.add(new_challenge)
    db.commit()
    db.refresh(new_challenge)

    # Create the Payment object
    new_payment = Payment(
        fid=payment_data.fid,
        amount=payment_data.amount,
        referral_code=payment_data.referral_code,
        challenge=new_challenge,
        challenge_id=new_challenge.id,
    )
    db.add(new_payment)
    db.commit()
    db.refresh(new_payment)

    if firebase_user.email:
        send_mail_in_thread(firebase_user.email, "Payment Confirmed", "Your payment is confirmed!")
    return new_payment
