import os
from typing import Iterator

import asyncio
import pytest_asyncio
from dotenv import load_dotenv
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel

from src.database import get_db
from src.main import app
from src.models.transaction import Transaction

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL_TEST")


# drop all database every time when test complete
@pytest_asyncio.fixture
async def async_db_engine():
    async_engine = create_async_engine(
        url=DATABASE_URL,
        echo=True,
    )

    async with async_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    yield async_engine

    async with async_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)


# truncate all table to isolate tests
@pytest_asyncio.fixture
async def async_db_session(async_db_engine):
    async_session = (
        sessionmaker(
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
            bind=async_db_engine,
            class_=AsyncSession,
        ))

    async with async_session() as session:
        await session.begin()

        yield session

        await session.rollback()

        for table in reversed(SQLModel.metadata.sorted_tables):
            await session.execute(f'TRUNCATE {table.name} CASCADE;')
            await session.commit()


@pytest_asyncio.fixture
async def async_client(async_db_session: AsyncSession) -> AsyncClient:
    def override_get_db() -> Iterator[AsyncSession]:
        yield async_db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

@pytest_asyncio.fixture
def event_loop():
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
def transaction_payload() -> dict:
    return {
        "trader_id": 4040,
        "trade_pair": "BTCUSD",
        "leverage": 1,
        "asset_type": "crypto",
        "stop_loss": 2,
        "take_profit": 2,
        "order_type": "LONG"
    }


# Doesn't work because it is not deleted after successful test
@pytest_asyncio.fixture
async def transaction_object(async_db_session: AsyncSession) -> Transaction:
    transaction = Transaction(
        trader_id=4040,
        trade_pair="BTCUSD",
        leverage=0.1,
        initial_price=58906.0,
        entry_price=58906.0,  # entry price and initial price will be different if status is pending
        asset_type="crypto",
        stop_loss=0.2,
        take_profit=0.2,
        order_type="LONG",
        operation_type="initiate",
        cumulative_leverage=0.1,
        cumulative_order_type="LONG",
        cumulative_stop_loss=0.2,
        cumulative_take_profit=0.2,
        average_entry_price=58906.0,
        status="OPEN",
        old_status="OPEN",
        trade_order=1,
        position_id=1,
        uuid="2CA263F1-5C94-11E0-84CC-002170FBAC5B",
        hot_key="5CRwSWfJWnMat1wtUvLTLUJ3fkTTgn1XDC8jVko2H8CmnYC2",
        limit_order=0.0,
        source="test",
        modified_by="4040",
    )
    async_db_session.add(transaction)
    await async_db_session.commit()
    await async_db_session.refresh(transaction)
    return transaction
