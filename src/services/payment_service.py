import threading

import requests
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.sql import and_

from src.config import REGISTRATION_API_URL
from src.models import Challenge
from src.models.payments import Payment
from src.schemas.user import PaymentCreate
from src.services.email_service import send_mail_in_thread
from src.services.user_service import get_firebase_user
from src.utils.logging import setup_logging

logger = setup_logging()


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
    firebase_user = get_firebase_user(db, payment_data.firebase_id)

    def create_challenge(user_id):
        new_challenge = Challenge(
            trader_id=0,
            hot_key="",
            user_id=user_id,
            active="0",
            challenge=payment_data.network,
            hotkey_status="In Progress"
        )
        db.add(new_challenge)
        db.commit()
        db.refresh(new_challenge)
        return new_challenge

    def create_payment_entry(challenge=None):
        new_payment = Payment(
            firebase_id=payment_data.firebase_id,
            amount=payment_data.amount,
            referral_code=payment_data.referral_code,
            challenge=challenge,
            challenge_id=challenge.id if challenge else None,
        )
        db.add(new_payment)
        db.commit()
        db.refresh(new_payment)
        return new_payment

    # If no Firebase user exists, create a payment without a challenge
    if not firebase_user:
        return create_payment_entry()

    # If Firebase user exists but lacks necessary fields
    if not firebase_user.name or not firebase_user.username or not firebase_user.email:
        new_challenge = create_challenge(firebase_user.id)
        return create_payment_entry(new_challenge)

    # If Firebase user has all necessary fields, create a challenge and start a thread
    new_challenge = create_challenge(firebase_user.id)
    if new_challenge:
        thread = threading.Thread(target=register_and_update_challenge,
                                  args=(new_challenge, new_challenge.challenge, firebase_user.name, db))
        thread.start()
        new_payment = create_payment_entry(new_challenge)
        send_mail_in_thread(firebase_user.email, "Payment Confirmed", "Your payment is confirmed!")
        return new_payment
    else:
        logger.error(f"Challenge didn't Created !")


def register_and_update_challenge(challenge: Challenge, network: str, user_name: str, db: Session):
    try:
        payload = {
            "name": user_name,
            "network": network,
        }
        response = requests.post(REGISTRATION_API_URL, json=payload)
        if response.status_code == 200:
            data = response.json()
            challenge.trader_id = data.get("trader_id")
            challenge.hot_key = data.get("hot_key")
            challenge.message = "Challenge Updated Successfully !"
            challenge.hotkey_status = "success"
            challenge.response = data
            db.commit()
            db.refresh(challenge)
            logger.info(f"Challenge {challenge.id} updated successfully.")
        else:
            challenge.hotkey_status = "Failed"
            challenge.message = "Challenge didn't Updated !"
            db.commit()
            db.refresh(challenge)
            logger.error(
                f"Registration API call failed with status code: {response.status_code}, response: {response.text}")

    except requests.RequestException as e:
        logger.error(f"Error in registration API call: {e}")
    except Exception as e:
        logger.error(f"Error updating challenge: {e}")
