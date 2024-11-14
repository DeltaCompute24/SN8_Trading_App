import unittest
from unittest.mock import AsyncMock, patch

from httpx import AsyncClient

from src.main import app


class TestInitiatePosition(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.client = AsyncClient(app=app, base_url="http://test")
        self.payload = {
            "trader_id": 4060,
            "trade_pair": "BTCUSD",
            "leverage": 1,
            "asset_type": "crypto",
            "stop_loss": 2,
            "take_profit": 2,
            "order_type": "LONG"
        }

    async def asyncTearDown(self):
        await self.client.aclose()

    async def test_position_already_exist(self):
        with patch("src.api.routes.initiate_position.get_latest_position", new=AsyncMock(return_value=self.payload)):
            response = await self.client.post("/trades/initiate-position/", json=self.payload)
            # assert response
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json(),
                             {"detail": "An open or pending position already exists for this trade pair and trader"})

    async def test_challenge_not_exist(self):
        with (patch(target="src.api.routes.initiate_position.get_latest_position", new=AsyncMock(return_value=None)),
              patch(target="src.api.routes.initiate_position.get_challenge", return_value=None)):
            response = await self.client.post("/trades/initiate-position/", json=self.payload)
            # assert response
            self.assertEqual(response.status_code, 500)
            self.assertEqual(response.json(),
                             second={
                                 "detail": f"400: Given Trader ID {self.payload['trader_id']} does not exist in the system!"})

    async def test_submit_trade_failed(self):
        with (patch(target="src.api.routes.initiate_position.get_latest_position", new=AsyncMock(return_value=None)),
              patch(target="src.api.routes.initiate_position.get_challenge", return_value="test"),
              patch(target="src.api.routes.initiate_position.websocket_manager.submit_trade", return_value=False)):
            response = await self.client.post("/trades/initiate-position/", json=self.payload)
            # assert response
            self.assertEqual(response.status_code, 500)
            self.assertEqual(response.json(), second={"detail": "500: Failed to submit trade"})

    async def test_trade_submitted_successfully(self):
        with (patch(target="src.api.routes.initiate_position.get_latest_position", new=AsyncMock(return_value=None)),
              patch(target="src.api.routes.initiate_position.get_challenge", return_value="test"),
              patch(target="src.api.routes.initiate_position.websocket_manager.submit_trade", return_value=True),
              patch(target="src.api.routes.initiate_position.get_taoshi_values",
                    return_value=(0, 1, 1, 1, 1, 1, 1, 1, 1))):
            # call api
            response = await self.client.post("/trades/initiate-position/", json=self.payload)
            # assert response
            self.assertEqual(response.status_code, 500)
            self.assertEqual(response.json(),
                             second={"detail": "500: Failed to fetch current price for the trade pair"})

    async def test_open_position_successfully(self):
        with (
            patch(target="src.api.routes.initiate_position.get_latest_position", new=AsyncMock(return_value=None)),
            patch(target="src.api.routes.initiate_position.get_challenge", return_value="test"),
            patch(target="src.api.routes.initiate_position.websocket_manager.submit_trade", return_value=True),
            patch(target="src.api.routes.initiate_position.get_taoshi_values",
                  return_value=(1, 1, 1, 1, 1, 1, 1, 1, 1)),
            patch("src.api.routes.initiate_position.create_transaction", new=AsyncMock()),
            patch("src.api.routes.initiate_position.update_monitored_positions", new=AsyncMock()),
        ):
            # call api
            response = await self.client.post("/trades/initiate-position/", json=self.payload)
            # assert response
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), {"detail": "Position initiated successfully"})
