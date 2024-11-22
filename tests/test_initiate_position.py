from unittest.mock import patch, AsyncMock

import pytest

import src

pytestmark = pytest.mark.asyncio
url = "/trades/initiate-position/"


class TestInitiatePosition:

    async def test_position_already_exist(self, async_client, transaction_payload):
        with (
            patch(target="src.api.routes.initiate_position.get_latest_position",
                  new=AsyncMock(return_value=transaction_payload)),
        ):
            response = await async_client.post(url=url, json=transaction_payload)
            # assert response
            assert response.status_code == 400
            assert response.json() == {
                "detail": "An open or pending position already exists for this trade pair and trader"}

    async def test_challenge_not_exist(self, async_client, transaction_payload):
        with (
            patch(target="src.api.routes.initiate_position.get_latest_position",
                  new=AsyncMock(return_value=None)),
            patch('src.api.routes.initiate_position.get_challenge', return_value=None)
        ):
            response = await async_client.post(url=url, json=transaction_payload)
            # assert response
            assert response.status_code == 500
            assert response.json() == {
                "detail": f"400: Given Trader ID {transaction_payload['trader_id']} does not exist in the system!"}

    async def test_submit_trade_failed(self, async_client, transaction_payload):
        with (
            patch(target="src.api.routes.initiate_position.get_latest_position", new=AsyncMock(return_value=None)),
            patch(target="src.api.routes.initiate_position.get_challenge", return_value="test"),
            patch(target="src.api.routes.initiate_position.websocket_manager.submit_trade", return_value=False)
        ):
            response = await async_client.post(url=url, json=transaction_payload)
            # assert response
            assert response.status_code == 500
            assert response.json() == {"detail": "500: Failed to submit trade"}

    async def test_first_price_is_zero(self, async_client, transaction_payload):
        with (
            patch(target="src.api.routes.initiate_position.get_latest_position", new=AsyncMock(return_value=None)),
            patch(target="src.api.routes.initiate_position.get_challenge", return_value="test"),
            patch(target="src.api.routes.initiate_position.websocket_manager.submit_trade", return_value=True),
            patch(target="src.api.routes.initiate_position.get_taoshi_values",
                  return_value=(0, 1, 1, 1, 1, 1, 1, 1, 1))
        ):
            # call api
            response = await async_client.post(url=url, json=transaction_payload)
            # assert response
            assert response.status_code == 500
            assert response.json() == {"detail": "500: Failed to fetch current price for the trade pair"}
            # get_taoshi_values should be called 12 times because first_price is 0
            assert src.api.routes.initiate_position.get_taoshi_values.call_count == 12

    async def test_open_position_successfully(self, async_client, transaction_payload):
        with (
            patch(target="src.api.routes.initiate_position.get_latest_position", new=AsyncMock(return_value=None)),
            patch(target="src.api.routes.initiate_position.get_challenge", return_value="test"),
            patch(target="src.api.routes.initiate_position.websocket_manager.submit_trade", return_value=True),
            patch(target="src.api.routes.initiate_position.get_taoshi_values",
                  return_value=(1, 1, 1, 1, 1, 1, 1, 1, 1)),
            patch("src.api.routes.initiate_position.create_transaction", new=AsyncMock()),
            patch("src.api.routes.initiate_position.MonitoredPositionCreate", new=AsyncMock()),
            patch("src.api.routes.initiate_position.update_monitored_positions", new=AsyncMock()),
        ):
            # call api
            response = await async_client.post(url=url, json=transaction_payload)
            # assert response
            assert response.status_code == 200
            assert response.json() == {"message": "Position initiated successfully"}
