from unittest.mock import patch, AsyncMock

import pytest

import src

pytestmark = pytest.mark.asyncio
url = "/trades/adjust-position/"


class TestAdjustPosition:

    async def test_position_not_exist(self, async_client, transaction_payload):
        with (
            patch(target="src.api.routes.adjust_position.get_open_position",
                  new=AsyncMock(return_value=None)),
        ):
            response = await async_client.post(url, json=transaction_payload)
            # assert response
            assert response.status_code == 404
            assert response.json() == {
                "detail": "No open position found for this trade pair and trader"}

    async def test_different_leverages(self, async_client, transaction_payload, transaction_object):
        transaction_payload["leverage"] = 0.01
        with (
            patch(target="src.api.routes.adjust_position.get_open_position", new=AsyncMock(return_value=transaction_object)),
            patch(target="src.api.routes.adjust_position.websocket_manager.submit_trade", return_value=False)
        ):
            response = await async_client.post(url, json=transaction_payload)
            # assert response
            assert response.status_code == 500
            assert response.json() == {"detail": "500: Failed to submit adjustment"}

    async def test_first_price_is_zero(self, async_client, transaction_payload, transaction_object):
        transaction_payload["leverage"] = 0.01
        with (
            patch(target="src.api.routes.adjust_position.get_open_position",
                  new=AsyncMock(return_value=transaction_object)),
            patch(target="src.api.routes.adjust_position.websocket_manager.submit_trade", return_value=True),
            patch(target="src.api.routes.adjust_position.get_taoshi_values", return_value=(0, 1, 1, 1, 1, 1, 1, 1, 1)),
        ):
            # call api
            response = await async_client.post(url=url, json=transaction_payload)
            # assert response
            assert response.status_code == 500
            assert response.json() == {"detail": "500: Failed to fetch current price for the trade pair"}
            # get_taoshi_values should be called 12 times because first_price is 0
            assert src.api.routes.adjust_position.get_taoshi_values.call_count == 12

    async def test_successful(self, async_client, transaction_payload, transaction_object):
        transaction_payload["leverage"] = 0.01
        adjust_response = {
            "message": "Position adjusted successfully",
            "data": {
                "position_id": transaction_object.position_id,
                "trader_id": transaction_object.trader_id,
                "trade_pair": transaction_object.trade_pair,
                "leverage": transaction_object.leverage,
                "cumulative_leverage": transaction_object.cumulative_leverage,
                "cumulative_order_type": transaction_object.cumulative_order_type,
                "cumulative_stop_loss": transaction_object.cumulative_stop_loss,
                "cumulative_take_profit": transaction_object.cumulative_take_profit,
                "asset_type": transaction_object.asset_type,
                "entry_price": transaction_object.entry_price,
            }
        }

        with (
            patch(target="src.api.routes.adjust_position.get_open_position",
                  new=AsyncMock(return_value=transaction_object)),
            patch(target="src.api.routes.adjust_position.websocket_manager.submit_trade", return_value=True),
            patch(target="src.api.routes.adjust_position.get_taoshi_values", return_value=(1, 1, 1, 1, 1, 1, 1, 3, 1)),
            patch("src.api.routes.adjust_position.create_transaction", new=AsyncMock(return_value=transaction_object)),
            patch("src.api.routes.adjust_position.close_transaction", new=AsyncMock()),
            patch("src.api.routes.adjust_position.MonitoredPositionCreate", new=AsyncMock()),
            patch("src.api.routes.adjust_position.update_monitored_positions", new=AsyncMock()),
        ):
            response = await async_client.post(url, json=transaction_payload)
            # assert response
            assert response.status_code == 200
            assert response.json() == adjust_response
            # get_taoshi_values should be called one time because first_price is 0
            assert src.api.routes.adjust_position.get_taoshi_values.call_count == 1

    async def test_same_leverages(self, async_client, transaction_payload, transaction_object):
        adjust_response = {
            "message": "Position adjusted successfully",
            "data": {
                "position_id": transaction_object.position_id,
                "trader_id": transaction_object.trader_id,
                "trade_pair": transaction_object.trade_pair,
                "leverage": transaction_object.leverage,
                "cumulative_leverage": transaction_object.cumulative_leverage,
                "cumulative_order_type": transaction_object.cumulative_order_type,
                "cumulative_stop_loss": transaction_object.cumulative_stop_loss,
                "cumulative_take_profit": transaction_object.cumulative_take_profit,
                "asset_type": transaction_object.asset_type,
                "entry_price": transaction_object.entry_price,
            }
        }

        with (
            patch(target="src.api.routes.adjust_position.get_open_position",
                  new=AsyncMock(return_value=transaction_object)),
            patch("src.api.routes.adjust_position.create_transaction", new=AsyncMock(return_value=transaction_object)),
            patch("src.api.routes.adjust_position.close_transaction", new=AsyncMock()),
            patch("src.api.routes.adjust_position.MonitoredPositionCreate", new=AsyncMock()),
            patch("src.api.routes.adjust_position.update_monitored_positions", new=AsyncMock()),
        ):
            response = await async_client.post(url, json=transaction_payload)
            # assert response
            assert response.status_code == 200
            assert response.json() == adjust_response
