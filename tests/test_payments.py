from unittest.mock import patch

import src
from tests.conftest import payment_object

url = "/payments/"


class TestPayment:
    def test_validations(self, client, payment_payload):
        payment_payload["step"] = 3
        payment_payload["phase"] = 3
        response = client.post(url, json=payment_payload)

        assert response.status_code == 422
        assert response.json() == {"detail": [
            {'type': 'literal_error', 'loc': ['body', 'step'], 'msg': 'Input should be 1 or 2', 'input': 3,
             'ctx': {'expected': '1 or 2'}},
            {'type': 'literal_error', 'loc': ['body', 'phase'], 'msg': 'Input should be 1 or 2', 'input': 3,
             'ctx': {'expected': '1 or 2'}}]}

    def test_payment_with_no_challenge(self, client, payment_payload, payment_object, payment_response):
        with(
            patch(target="src.services.payment_service.get_firebase_user", return_value=None),
            patch(target="src.services.payment_service.create_payment_entry", return_value=payment_object),
        ):
            response = client.post(url, json=payment_payload)

            assert response.status_code == 200
            assert response.json() == payment_response

    def test_payment_without_username(self, client, payment_object, payment_response, firebase_user, challenge_object,
                                      payment_payload):
        firebase_user.email = None
        firebase_user.username = None
        payment_object.challenge_id = payment_response["challenge_id"] = 1
        payment_object.challenge = payment_response["challenge"] = {
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
            patch(target="src.services.payment_service.create_challenge", return_value=challenge_object),
            patch(target="src.services.payment_service.create_payment_entry", return_value=payment_object),
        ):
            response = client.post(url, json=payment_payload)

            assert response.status_code == 200
            assert response.json() == payment_response

    def test_payment_with_username(self, client, challenge_object, payment_object, payment_payload, payment_response,
                                   firebase_user):
        challenge_object.challenge_name = "email_1"
        challenge_object.trader_id = 4040
        challenge_object.hot_key = "5CRwSWfJ"
        challenge_object.active = "1"
        challenge_object.hotkey_status = "Success"
        challenge_object.message = "Challenge Updated Successfully!"

        payment_object.challenge = payment_response["challenge"] = {
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
            patch(target="src.services.payment_service.create_challenge", return_value=challenge_object),
            patch(target="src.services.payment_service.register_and_update_challenge"),
            patch(target="src.services.payment_service.create_payment_entry", return_value=payment_object),
            patch(target="src.services.payment_service.send_mail_in_thread"),
        ):
            response = client.post(url, json=payment_payload)

            assert response.status_code == 200
            assert response.json() == payment_response
            src.services.payment_service.register_and_update_challenge.assert_called_once_with(1)

    # -------------------------------- Test Get Payment -----------------------------------
    def test_get_payment_not_found(self, client):
        response = client.get(url + "1")

        assert response.status_code == 404
        assert response.json() == {'detail': 'Payment Not Found'}

    def test_get_payment(self, client, payment_read, challenge_object):
        payment_response, payment_object = payment_read
        with (
            patch(target="src.api.routes.payments.get_payment", return_value=payment_object),
        ):
            response = client.get(url + "1")

            assert response.status_code == 200
            assert response.json() == payment_response.dict()
