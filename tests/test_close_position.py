from unittest.mock import patch, AsyncMock

import pytest

import src

pytestmark = pytest.mark.asyncio
url = "/trades/close-position/"


class TestClosePosition:

    async def test_position_not_exist(self, async_client, transaction_payload):
        with (
            patch(target="src.api.routes.close_position.get_latest_position",
                  new=AsyncMock(return_value=None)),
        ):
            response = await async_client.post(url, json=transaction_payload)
            # assert response
            assert response.status_code == 404
            assert response.json() == {"detail": "No open or pending position found for this trade pair and trader"}

    async def test_different_leverages(self, async_client, transaction_payload, transaction_object):
        with (
            patch(target="src.api.routes.close_position.get_latest_position",
                  new=AsyncMock(return_value=transaction_object)),
            patch(target="src.api.routes.close_position.websocket_manager.submit_trade", return_value=False)
        ):
            response = await async_client.post(url, json=transaction_payload)
            # assert response
            assert response.status_code == 500
            assert response.json() == {"detail": "500: Failed to submit close signal"}

    async def test_first_price_is_zero(self, async_client, transaction_payload, transaction_object):
        with (
            patch(target="src.api.routes.close_position.get_latest_position",
                  new=AsyncMock(return_value=transaction_object)),
            patch(target="src.api.routes.close_position.websocket_manager.submit_trade", return_value=True),
            patch(target="src.api.routes.close_position.get_taoshi_values", return_value=(0, 1, 1, 1, 1, 1, 1, 1, 1)),
        ):
            # call api
            response = await async_client.post(url=url, json=transaction_payload)
            # assert response
            assert response.status_code == 500
            assert response.json() == {"detail": "500: Failed to fetch current price for the trade pair"}
            # get_taoshi_values should be called 12 times because first_price is 0
            assert src.api.routes.close_position.get_taoshi_values.call_count == 12

    async def test_successful(self, async_client, transaction_payload, transaction_object):
        with (
            patch(target="src.api.routes.close_position.get_latest_position",
                  new=AsyncMock(return_value=transaction_object)),
            patch(target="src.api.routes.close_position.websocket_manager.submit_trade", return_value=True),
            patch(target="src.api.routes.close_position.get_taoshi_values", return_value=(1, 1, 1, 1, 1, 1, 1, 3, 1)),
            patch("src.api.routes.close_position.close_transaction", new=AsyncMock()),
        ):
            response = await async_client.post(url, json=transaction_payload)
            # assert response
            assert response.status_code == 200
            assert response.json() == {"message": "Position closed successfully"}
            # get_taoshi_values should be called one time because first_price is 0
            assert src.api.routes.close_position.get_taoshi_values.call_count == 1

    async def test_pending_successful(self, async_client, transaction_payload, transaction_object):
        transaction_object.status = "PENDING"

        with (
            patch(target="src.api.routes.close_position.get_latest_position",
                  new=AsyncMock(return_value=transaction_object)),
            patch("src.api.routes.close_position.close_transaction", new=AsyncMock()),
        ):
            response = await async_client.post(url, json=transaction_payload)
            # assert response
            assert response.status_code == 200
            assert response.json() == {"message": "Position closed successfully"}
