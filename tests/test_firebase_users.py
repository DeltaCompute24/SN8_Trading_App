from unittest.mock import patch

import pytest

url = "/users/"


class TestFirebaseUsers:
    @pytest.mark.parametrize(
        "firebase_id, name, email, expected_status, expected_response",
        [
            ("", "name", "email", 400, {"detail": "Firebase id, Name or Email can't be Empty!"}),
            ("firebase_id", "", "email", 400, {"detail": "Firebase id, Name or Email can't be Empty!"}),
            ("firebase_id", "name", "", 400, {"detail": "Firebase id, Name or Email can't be Empty!"}),
        ]
    )
    def test_validations(self, firebase_id, name, email, expected_status, expected_response, client):
        payload = {
            "firebase_id": firebase_id,
            "name": name,
            "email": email,
        }
        response = client.post(url, json=payload)
        assert response.status_code == expected_status
        assert response.json() == expected_response

    def test_create_user(self, client):
        payload = {
            "firebase_id": "firebase_id",
            "name": "name",
            "email": "email@gmail.com",
        }
        api_response = {
            **payload,
            "id": 1,
            "username": "email",
            "created_at": "2021-08-01T00:00:00",
            "updated_at": "2021-08-01T00:00:00",
            "challenges": []
        }
        with(
            patch(target="src.api.routes.users.create_firebase_user", return_value=api_response),
        ):
            response = client.post(url, json=payload)
            assert response.status_code == 200
            assert response.json() == api_response
