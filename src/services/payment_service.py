import threading
from datetime import datetime

import requests
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.sql import and_

from src.config import REGISTRATION_API_URL
from src.database_tasks import TaskSessionLocal_
from src.models import Challenge
from src.models.payments import Payment
from src.schemas.user import PaymentCreate
from src.services.email_service import send_mail, send_support_email
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


def create_challenge(db, payment_data, network, phase, user, challenge_status="In Challenge", status="In Progress",
                     message="Trader_id and hot_key will be created"):
    _challenge = Challenge(
        trader_id=0,
        hot_key="",
        user_id=user.id,
        active="0",
        status=challenge_status,
        challenge=network,
        hotkey_status=status,
        message=message,
        step=payment_data.step,
        phase=phase,
    )
    db.add(_challenge)
    db.commit()
    db.refresh(_challenge)

    if user.username:
        _challenge.challenge_name = f"{user.username}_{_challenge.id}"
        db.add(_challenge)
        db.commit()
        db.refresh(_challenge)

    return _challenge


def create_payment_entry(db, payment_data, phase, challenge=None):
    _payment = Payment(
        firebase_id=payment_data.firebase_id,
        amount=payment_data.amount,
        referral_code=payment_data.referral_code,
        challenge=challenge,
        challenge_id=challenge.id if challenge else None,
        step=payment_data.step,
        phase=phase,
    )
    db.add(_payment)
    db.commit()
    db.refresh(_payment)
    return _payment


def create_payment(db: Session, payment_data: PaymentCreate):
    if payment_data.step not in [1, 2]:
        raise HTTPException(status_code=400, detail="Step or Phase can either be 1 or 2")

    if payment_data.step == 2:
        phase = 1
        network = "test"
    else:
        phase = 2
        network = "main"

    firebase_user = get_firebase_user(db, payment_data.firebase_id)
    if firebase_user and firebase_user.email == "dev@delta-mining.com" and payment_data.step == 1:
        raise HTTPException(status_code=400, detail=f"You '{firebase_user.email}' can't register minor as mainnet!")

    first_name = ""
    context = {}
    if not firebase_user:
        new_challenge = None
    elif firebase_user.username:
        first_name = firebase_user.name or "User"
        context = {"name": first_name}
        new_challenge = create_challenge(db, payment_data, network, phase, firebase_user)
        thread = threading.Thread(
            target=register_and_update_challenge,
            kwargs={
                "challenge_id": new_challenge.id,
                "context": context,
            }
        )
        thread.start()
    # If Firebase user exists but lacks necessary fields
    else:
        new_challenge = create_challenge(db, payment_data, network, phase, firebase_user, status="Failed",
                                         message="User's Email and Name is Empty!")

    new_payment = create_payment_entry(db, payment_data, phase, new_challenge)
    if firebase_user and firebase_user.email:
        send_mail(
            receiver=firebase_user.email,
            subject=f"{first_name}, Payment Confirmed",
            context=context,
        )
    return new_payment


def register_and_update_challenge(
        challenge_id: int,
        challenge_status="In Challenge",
        subject="Step 2 Challenge Details",
        test_template="ChallengeDetailStep2.html",
        context=None,
):
    with TaskSessionLocal_() as db:
        try:
            print("In THREAD!................")
            challenge = get_challenge_by_id(db, challenge_id)
            email = challenge.user.email
            network = challenge.challenge
            payload = {
                "name": challenge.challenge_name,
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
                challenge.status = challenge_status
                challenge.message = "Challenge Updated Successfully!"
                challenge.hotkey_status = "Success"
                context.update({
                    "trader_id": challenge.trader_id,
                })
                if network == "main":
                    challenge.register_on_main_net = datetime.utcnow()
                    send_mail(
                        email,
                        subject="Step 1 Challenge Details",
                        template_name="ChallengeDetailStep1.html",
                        context=context,
                    )
                else:
                    challenge.register_on_test_net = datetime.utcnow()
                    send_mail(
                        email,
                        subject=subject,
                        template_name=test_template,
                        context=context,
                    )
            else:
                print("400 RESPONSE")
                challenge.hotkey_status = "Failed"
                challenge.message = f"Registration API call failed with status code: {response.status_code}. Challenge didn't Updated!"
                send_support_email(
                    subject=f"Registration API call failed with status code: {response.status_code}",
                    content=f"User {email} tried to create payment with step {challenge.step} and phase {challenge.phase} "
                            f"but Failed. Response from registration api => {data}",
                )

            db.commit()
            db.refresh(challenge)

        except Exception as e:
            challenge.hotkey_status = "Failed"
            challenge.message = str(e)
            db.commit()
            send_support_email(
                subject="Exception in Registration Process",
                content=f"User {email} tried to create payment with step {challenge.step} and phase {challenge.phase} "
                        f"but Failed. Exception => {e}",
            )
