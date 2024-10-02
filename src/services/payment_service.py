from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.sql import and_

from src.models import Challenge
from src.models.payments import Payment
from src.schemas.user import PaymentCreate, PaymentUpdate


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
    # Create the Payment object
    new_payment = Payment(
        fid=payment_data.fid,
        amount=payment_data.amount,
        referral_code=payment_data.referral_code,
        challenge_id=payment_data.challenge_id  # This will be updated with the actual challenge created below
    )

    db.add(new_payment)
    db.commit()
    db.refresh(new_payment)

    # Check if challenge data exists in payment_data and create challenge if necessary
    if payment_data.challenge:
        challenge_data = payment_data.challenge  # Assume this is a dictionary containing challenge data
        new_challenge = Challenge(
            trader_id=challenge_data['trader_id'],
            hot_key=challenge_data['hot_key'],
            status=challenge_data['status'],
            active=challenge_data['active'],
            challenge=challenge_data['challenge']
        )
        db.add(new_challenge)

        # Associate the challenge with the payment
        new_payment.challenge = new_challenge
        new_payment.challenge_id = new_challenge.id  # Update payment with the actual challenge ID after it's created

    # Commit the transaction and refresh the payment object
    db.commit()
    db.refresh(new_payment)

    return new_payment


def update_payment(db: Session, payment_id: int, payment_data: PaymentUpdate):
    payment = get_payment(db, payment_id)
    if not payment:
        return None

    # Update the payment fields if provided
    if payment_data.fid is not None:
        payment.fid = payment_data.fid
    if payment_data.amount is not None:
        payment.amount = payment_data.amount
    if payment_data.referral_code is not None:
        payment.referral_code = payment_data.referral_code

    # Update or create the challenge if challenge data is provided
    if payment_data.challenge:
        challenge_data = payment_data.challenge
        existing_challenge = db.scalar(
            select(Challenge).where(
                and_(
                    Challenge.trader_id == challenge_data['trader_id'],
                    Challenge.user_id == payment.challenge.user_id
                )
            )
        )

        if existing_challenge:
            # Update the existing challenge
            existing_challenge.hot_key = challenge_data['hot_key']
            existing_challenge.status = challenge_data['status']
            existing_challenge.active = challenge_data['active']
            existing_challenge.challenge = challenge_data['challenge']
        else:
            # Create a new challenge if none exists
            new_challenge = Challenge(
                trader_id=challenge_data['trader_id'],
                hot_key=challenge_data['hot_key'],
                status=challenge_data['status'],
                active=challenge_data['active'],
                challenge=challenge_data['challenge'],
                user_id=payment.challenge.user_id
            )
            db.add(new_challenge)

            # Associate the new challenge with the payment
            payment.challenge = new_challenge
            payment.challenge_id = new_challenge.id

    # Commit the changes and refresh the payment object
    db.commit()
    db.refresh(payment)
    return payment


def delete_payment(db: Session, payment_id: int):
    payment = get_payment(db, payment_id)
    if not payment:
        return None

    db.delete(payment)
    db.commit()
    return payment
