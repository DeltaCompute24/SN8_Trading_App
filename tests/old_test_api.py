import logging
import unittest

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.future import select
from sqlalchemy.orm import sessionmaker

from src.database import Base
from src.main import app
from src.models.transaction import Transaction
from src.services.trade_service import calculate_profit_loss

logging.basicConfig(level=logging.INFO)

DATABASE_URL = "postgresql+asyncpg://user:password@localhost/test_db"
engine = create_async_engine(DATABASE_URL, future=True)
SessionTesting = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class TestTradingApp(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        self.session = SessionTesting()
        self.client = AsyncClient(app=app, base_url="http://test")

    async def asyncTearDown(self):
        await self.client.aclose()
        await self.session.close()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    async def test_initiate_position(self):
        payload = {
            "trader_id": 4060,
            "trade_pair": "BTCUSD",
            "leverage": 1,
            "asset_type": "crypto",
            "stop_loss": 2,
            "take_profit": 2,
            "order_type": "LONG"
        }
        logging.info("Initiating position with payload: %s", payload)
        response = await self.client.post("/trades/initiate-position/", json=payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"message": "Position initiated successfully"})

        # Verify the initiated position
        result = await self.session.execute(
            select(Transaction).where(Transaction.trader_id == 4060, Transaction.trade_pair == "BTCUSD"))
        position = result.scalars().first()

        self.assertIsNotNone(position)
        self.assertEqual(position.leverage, 1)
        self.assertEqual(position.stop_loss, 2)
        self.assertEqual(position.take_profit, 2)
        self.assertEqual(position.order_type, "LONG")
        self.assertEqual(position.operation_type, "initiate")

    async def test_close_position(self):
        # First initiate a position
        init_payload = {
            "trader_id": 4060,
            "trade_pair": "BTCUSD",
            "leverage": 1,
            "asset_type": "crypto",
            "stop_loss": 2,
            "take_profit": 2,
            "order_type": "LONG"
        }
        logging.info("Initiating position with payload: %s", init_payload)
        await self.client.post("/trades/initiate-position/", json=init_payload)

        # Now close the position
        close_payload = {
            "trader_id": 4060,
            "trade_pair": "BTCUSD",
            "asset_type": "crypto"
        }
        logging.info("Closing position with payload: %s", close_payload)
        response = await self.client.post("/trades/close-position/", json=close_payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"message": "Position closed successfully"})

        # Verify the closed position
        result = await self.session.execute(
            select(Transaction).where(Transaction.trader_id == 4060, Transaction.trade_pair == "BTCUSD").order_by(
                Transaction.open_time.desc()))
        position = result.scalars().first()

        self.assertIsNotNone(position)
        self.assertEqual(position.order_type, "FLAT")
        self.assertEqual(position.cumulative_leverage, 1)
        self.assertIsNotNone(position.close_price)
        self.assertIsNotNone(position.profit_loss)

    async def test_get_profit_loss(self):
        # First initiate a position
        init_payload = {
            "trader_id": 4060,
            "trade_pair": "BTCUSD",
            "leverage": 1,
            "asset_type": "crypto",
            "stop_loss": 2,
            "take_profit": 2,
            "order_type": "LONG"
        }
        logging.info("Initiating position with payload: %s", init_payload)
        await self.client.post("/trades/initiate-position/", json=init_payload)

        # Now calculate profit/loss
        profit_loss_payload = {
            "trader_id": 4060,
            "trade_pair": "BTCUSD"
        }
        logging.info("Calculating profit/loss with payload: %s", profit_loss_payload)
        response = await self.client.post("/trades/profit-loss/", json=profit_loss_payload)
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertIn("profit_loss", response_data)

        # Verify the profit/loss calculation
        result = await self.session.execute(
            select(Transaction).where(Transaction.trader_id == 4060, Transaction.trade_pair == "BTCUSD").order_by(
                Transaction.open_time.desc()))
        position = result.scalars().first()

        self.assertIsNotNone(position)
        entry_price = position.entry_price
        current_price = response_data["current_price"]
        leverage = position.cumulative_leverage
        order_type = position.cumulative_order_type

        # Assuming you have a calculate_profit_loss function to verify the value
        expected_profit_loss = calculate_profit_loss(position, current_price)
        self.assertEqual(response_data["profit_loss"], expected_profit_loss)

    async def test_get_positions(self):
        # Initiate a position
        init_payload = {
            "trader_id": 4060,
            "trade_pair": "BTCUSD",
            "leverage": 1,
            "asset_type": "crypto",
            "stop_loss": 2,
            "take_profit": 2,
            "order_type": "LONG"
        }
        logging.info("Initiating position with payload: %s", init_payload)
        await self.client.post("/trades/initiate-position/", json=init_payload)

        # Fetch positions
        logging.info("Fetching positions for trader_id: %d", 4060)
        response = await self.client.get("/trades/positions/4060")
        self.assertEqual(response.status_code, 200)
        positions = response.json()
        self.assertGreater(len(positions), 0)

        # Verify the fetched positions
        self.assertEqual(positions[0]["trader_id"], 4060)
        self.assertEqual(positions[0]["trade_pair"], "BTCUSD")


if __name__ == "__main__":
    unittest.main()
