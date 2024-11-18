from unittest.mock import patch

import pytest

from src.models import FirebaseUser, Challenge
from src.schemas.user import PaymentIdRead

pytestmark = pytest.mark.asyncio
url = "/payments/"

payment_payload = {
    "firebase_id": "firebase_id",
    "amount": 100,
    "referral_code": "referral_code",
    "step": 3,
    "phase": 3,
}

payment = PaymentIdRead(
    id=1,
    firebase_id="firebase_id",
    amount=100,
    referral_code="referral_code",
    challenge_id=None,
    challenge=None,
)

payment_response = {
    "id": 1,
    "firebase_id": "firebase_id",
    "amount": 100,
    "referral_code": "referral_code",
    "challenge_id": None,
    "challenge": None,
}

firebase_user = FirebaseUser(
    id=1,
    firebase_id="firebase_id",
    email="email@gmail.com",
    name="name",
    username="email",
)

challenge = Challenge(
        id=1,
        trader_id=0,
        hot_key="",
        user_id=1,
        active="0",
        status="In Challenge",
        challenge="main",
        hotkey_status="Failed",
        message="User's Email and Name is Empty!",
        step=1,
        phase=1,
    )


class TestPayment:
    def test_validations(self, client):
        response = client.post(url, json=payment_payload)

        assert response.status_code == 422
        assert response.json() == {"detail": [
            {'type': 'literal_error', 'loc': ['body', 'step'], 'msg': 'Input should be 1 or 2', 'input': 3,
             'ctx': {'expected': '1 or 2'}},
            {'type': 'literal_error', 'loc': ['body', 'phase'], 'msg': 'Input should be 1 or 2', 'input': 3,
             'ctx': {'expected': '1 or 2'}}]}

    def test_payment_with_no_challenge(self, client):
        payment_payload["step"] = 1
        payment_payload["phase"] = 1
        with(
            patch(target="src.services.payment_service.get_firebase_user", return_value=None),
            patch(target="src.services.payment_service.create_payment_entry", return_value=payment),
        ):
            response = client.post(url, json=payment_payload)

            assert response.status_code == 200
            assert response.json() == payment_response

    def test_payment_without_username(self, client):
        firebase_user.email = None
        firebase_user.username = None
        payment.challenge_id = payment_response["challenge_id"] = 1
        payment.challenge = payment_response["challenge"] = {
            "id": 1,
            "trader_id": 0,
            "hot_key": "",
            "user_id": 1,
            "active": "0",
            "status": "In Challenge",
            "challenge": "main",
            "hotkey_status": "Failed",
            "message": "User's Email and Name is Empty!",
            "step": 1,
            "phase": 1,
        }
        with(
            patch(target="src.services.payment_service.get_firebase_user", return_value=firebase_user),
            patch(target="src.services.payment_service.create_challenge", return_value=challenge),
            patch(target="src.services.payment_service.create_payment_entry", return_value=payment),
        ):
            response = client.post(url, json=payment_payload)

            assert response.status_code == 200
            assert response.json() == payment_response

    def test_payment_with_username(self, client):
        challenge.challenge_name = "email_1"
        challenge.trader_id = 4040
        challenge.hot_key = "5CRwSWfJ"
        challenge.active = "1"
        challenge.hotkey_status = "Success"
        challenge.message = "Challenge Updated Successfully!"

        payment.challenge = payment_response["challenge"] = {
            "id": 1,
            "trader_id": 4040,
            "hot_key": "5CRwSWfJ",
            "user_id": 1,
            "active": "1",
            "status": "In Challenge",
            "challenge": "main",
            "hotkey_status": "Success",
            "message": "Challenge Updated Successfully!",
            "step": 1,
            "phase": 1,
        }

        with(
            patch(target="src.services.payment_service.get_firebase_user", return_value=firebase_user),
            patch(target="src.services.payment_service.create_challenge", return_value=challenge),
            patch(target="src.services.payment_service.create_payment_entry", return_value=payment),
            patch(target="src.services.payment_service.send_mail_in_thread"),
        ):
            response = client.post(url, json=payment_payload)

            assert response.status_code == 200
            assert response.json() == payment_response
