import threading

import requests
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.sql import and_

from src.config import REGISTRATION_API_URL
from src.database_tasks import TaskSessionLocal_
from src.models import Challenge
from src.models.payments import Payment
from src.schemas.user import PaymentCreate
from src.services.email_service import send_mail_in_thread, send_mail
from src.services.user_service import get_firebase_user, get_challenge_by_id
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


def create_challenge(db, payment_data, user_id, status="In Progress", message="Trader_id and hot_key will be created"):
    _challenge = Challenge(
        trader_id=0,
        hot_key="",
        user_id=user_id,
        active="0",
        challenge=payment_data.network,
        hotkey_status=status,
        message=message,
    )
    db.add(_challenge)
    db.commit()
    db.refresh(_challenge)
    return _challenge


def create_payment_entry(db, payment_data, challenge=None):
    _payment = Payment(
        firebase_id=payment_data.firebase_id,
        amount=payment_data.amount,
        referral_code=payment_data.referral_code,
        challenge=challenge,
        challenge_id=challenge.id if challenge else None,
    )
    db.add(_payment)
    db.commit()
    db.refresh(_payment)
    return _payment


def create_payment(db: Session, payment_data: PaymentCreate):
    firebase_user = get_firebase_user(db, payment_data.firebase_id)

    if not firebase_user:
        new_challenge = None
    elif firebase_user.username:
        new_challenge = create_challenge(db, payment_data, firebase_user.id)
        thread = threading.Thread(
            target=register_and_update_challenge,
            args=(
                new_challenge.id, new_challenge.challenge,
                firebase_user.username,
            ))
        thread.start()
    # If Firebase user exists but lacks necessary fields
    else:
        new_challenge = create_challenge(db, payment_data, firebase_user.id, status="Failed",
                                         message="User's Email and Name is Empty!")

    new_payment = create_payment_entry(db, payment_data, new_challenge)
    if firebase_user and firebase_user.email:
        send_mail_in_thread(firebase_user.email, "Payment Confirmed", "Your payment is confirmed!")
    return new_payment


def register_and_update_challenge(challenge_id: int, network: str, user_name: str):
    with TaskSessionLocal_() as db:
        try:
            print("In THREAD!................")
            challenge = get_challenge_by_id(db, challenge_id)
            payload = {
                "name": f"{user_name}_{challenge_id}",
                "network": network,
            }
            response = requests.post(REGISTRATION_API_URL, json=payload)
            data = response.json()
            challenge.response = data
            if response.status_code == 200:
                print("200 RESPONSE")
                challenge.trader_id = data.get("trader_id")
                challenge.hot_key = data.get("hot_key")
                challenge.active = "1"
                challenge.status = "In Challenge"
                challenge.message = "Challenge Updated Successfully!"
                challenge.hotkey_status = "Success"
                send_mail(challenge.user.email, "Issuance of trader_id and hot_key",
                          "Congratulations! Your trader_id and hot_key is ready. Now, you can use your system.")
            else:
                print("400 RESPONSE")
                challenge.hotkey_status = "Failed"
                challenge.message = f"Registration API call failed with status code: {response.status_code}. Challenge didn't Updated!"

            db.commit()
            db.refresh(challenge)

        except Exception as e:
            challenge.hotkey_status = "Failed"
            challenge.message = str(e)
            db.commit()
