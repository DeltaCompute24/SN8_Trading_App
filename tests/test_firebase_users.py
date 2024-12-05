from unittest.mock import patch

import pytest

url = "/users/"


class TestFirebaseUsers:
    def test_validations(self, client):
        response = client.post(url, json={})
        assert response.status_code == 422
        assert response.json() == {
            'detail': [
                {'type': 'missing', 'loc': ['body', 'firebase_id'], 'msg': 'Field required', 'input': {}},
                {'type': 'missing', 'loc': ['body', 'name'], 'msg': 'Field required', 'input': {}},
                {'type': 'missing', 'loc': ['body', 'email'], 'msg': 'Field required', 'input': {}}
            ]
        }

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

    # ---------------------------- GET USER ---------------------------------------------
    def test_get_user_not_found(self, client):
        response = client.get(f"{url}firebase")

        assert response.status_code == 404
        assert response.json() == {"detail": "User Not Found!"}

    def test_get_user(self, client):
        api_response = {
            "firebase_id": "firebase_id",
            "name": "name",
            "email": "email@gmail.com",
            "id": 1,
            "username": "email",
            "created_at": "2021-08-01T00:00:00",
            "updated_at": "2021-08-01T00:00:00",
            "challenges": []
        }
        with(
            patch(target="src.api.routes.users.get_firebase_user", return_value=api_response),
        ):
            response = client.get(f"{url}firebase")
            assert response.status_code == 200
            assert response.json() == api_response

    # ---------------------------- UPDATE USER ---------------------------------------------
    def test_update_user_validations(self, client):
        response = client.put(f"{url}firebase")
        assert response.status_code == 422
        assert response.json() == {
            'detail': [{'type': 'missing', 'loc': ['body'], 'msg': 'Field required', 'input': None}]}

    def test_update_user_not_found(self, client):
        response = client.put(f"{url}firebase", json={})
        assert response.status_code == 404
        assert response.json() == {'detail': 'User Not Found!'}

    # def test_update_user_successfully(self, client, user_object):
    #     api_response = {
    #         "firebase_id": "firebase",
    #         "name": "name",
    #         "email": "email@gmail.com",
    #         "id": 1,
    #         "username": "email",
    #         "created_at": "2021-08-01T00:00:00",
    #         "updated_at": "2021-08-01T00:00:00",
    #         "challenges": []
    #     }
    #     with(
    #         patch(target="src.api.routes.users.get_firebase_user", return_value=user_object),
    #     ):
    #         response = client.put(f"{url}firebase", json={})
    #         assert response.status_code == 200
    #         assert response.json() == api_response
