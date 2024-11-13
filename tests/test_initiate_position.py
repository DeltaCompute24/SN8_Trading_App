from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from src.main import app
from src.schemas.transaction import TransactionCreate


@pytest.fixture
def position_data():
    return TransactionCreate(
        trader_id=4040,
        trade_pair="BTCUSD",
        asset_type="crypto",
        leverage=0.2,
        stop_loss=0.1,
        take_profit=0.2,
        order_type="LONG",
    )


@pytest.fixture
async def client():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_initiate_position_success(client, position_data):
    # Mock dependencies
    with patch("src.services.trade_service.get_latest_position", new=AsyncMock(return_value=None)), \
            patch("src.services.user_service.get_challenge", return_value="challenge_data"), \
            patch("src.utils.websocket_manager.websocket_manager.submit_trade", new=AsyncMock(return_value=True)), \
            patch("src.services.trade_service.create_transaction", new=AsyncMock()), \
            patch("src.services.fee_service.get_taoshi_values",
                  return_value=(1.0, 0.0, 0.0, 0.0, 0.0, "uuid", "hot_key", 1, 1.0)), \
            patch("src.services.trade_service.update_monitored_positions", new=AsyncMock()), \
            patch("src.utils.redis_manager.get_live_price", return_value=1.0):
        response = await client.post("/initiate-position/", json=position_data.dict())
        assert response.status_code == 200
        assert response.json()["message"] == "Position initiated successfully"


@pytest.mark.asyncio
async def test_initiate_position_existing_position(client, position_data):
    with patch("src.services.trade_service.get_latest_position", new=AsyncMock(return_value="existing_position")):
        response = await client.post("/initiate-position/", json=position_data.dict())
        assert response.status_code == 400
        assert response.json()["detail"] == "An open or pending position already exists for this trade pair and trader"


@pytest.mark.asyncio
async def test_initiate_position_failed_trade_submission(client, position_data):
    with patch("src.services.trade_service.get_latest_position", new=AsyncMock(return_value=None)), \
            patch("src.services.user_service.get_challenge", return_value="challenge_data"), \
            patch("src.utils.websocket_manager.websocket_manager.submit_trade", new=AsyncMock(return_value=False)):
        response = await client.post("/initiate-position/", json=position_data.dict())
        assert response.status_code == 500
        assert response.json()["detail"] == "Failed to submit trade"


@pytest.mark.asyncio
async def test_initiate_position_price_fetch_failure(client, position_data):
    with patch("src.services.trade_service.get_latest_position", new=AsyncMock(return_value=None)), \
            patch("src.services.user_service.get_challenge", return_value="challenge_data"), \
            patch("src.utils.websocket_manager.websocket_manager.submit_trade", new=AsyncMock(return_value=True)), \
            patch("src.services.fee_service.get_taoshi_values",
                  return_value=(0, 0.0, 0.0, 0.0, 0.0, "uuid", "hot_key", 1, 1.0)):
        response = await client.post("/initiate-position/", json=position_data.dict())
        assert response.status_code == 500
        assert response.json()["detail"] == "Failed to fetch current price for the trade pair"


@pytest.mark.asyncio
async def test_initiate_position_invalid_trader_id(client, position_data):
    with patch("src.services.trade_service.get_latest_position", new=AsyncMock(return_value=None)), \
            patch("src.services.user_service.get_challenge", return_value=None):
        response = await client.post("/initiate-position/", json=position_data.dict())
        assert response.status_code == 400
        assert response.json()["detail"] == "Given Trader ID 4040 does not exist in the system!"
