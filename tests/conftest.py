import asyncio
import os
from typing import Iterator

import pytest
import pytest_asyncio
from dotenv import load_dotenv
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from starlette.testclient import TestClient

from src.database import get_db, Base
from src.main import app
from src.models import FirebaseUser, Challenge
from src.models.transaction import Transaction
from src.schemas.user import PaymentIdRead, PaymentRead

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL_TEST")
DATABASE_URL_SYNC = DATABASE_URL.replace("asyncpg", "psycopg2")


# drop all database every time when test complete
@pytest_asyncio.fixture
async def async_db_engine():
    async_engine = create_async_engine(
        url=DATABASE_URL,
        echo=True,
    )

    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield async_engine

    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# truncate all table to isolate tests
@pytest_asyncio.fixture
async def async_db_session(async_db_engine):
    async_session = sessionmaker(
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
        bind=async_db_engine,
        class_=AsyncSession,
    )

    async with async_session() as session:
        await session.begin()

        yield session

        await session.rollback()


@pytest_asyncio.fixture
async def async_client(async_db_session: AsyncSession) -> AsyncClient:
    def override_get_db() -> Iterator[AsyncSession]:
        yield async_db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
def client() -> TestClient:
    return TestClient(app=app, base_url="http://test")


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
        "leverage": 0.1,
        "asset_type": "crypto",
        "stop_loss": 2,
        "take_profit": 2,
        "order_type": "LONG"
    }


@pytest_asyncio.fixture
def transaction_object() -> Transaction:
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
        order_level=2,
        max_profit_loss=0.2,
        profit_loss=0.2,
    )
    return transaction


# --------------------------------------------------- Payment Fixtures ----------------------------------------------

@pytest.fixture
def payment_payload():
    return {
        "firebase_id": "firebase_id",
        "amount": 100,
        "referral_code": "referral_code",
        "step": 1,
        "phase": 1,
    }


@pytest.fixture
def payment_object():
    return PaymentIdRead(
        id=1,
        firebase_id="firebase_id",
        amount=100,
        referral_code="referral_code",
        challenge_id=None,
        challenge=None,
    )


@pytest.fixture
def payment_response():
    return {
        "id": 1,
        "firebase_id": "firebase_id",
        "amount": 100,
        "referral_code": "referral_code",
        "challenge_id": None,
        "challenge": None,
    }


@pytest.fixture
def firebase_user():
    return FirebaseUser(
        id=1,
        firebase_id="firebase_id",
        email="email@gmail.com",
        name="name",
        username="email",
    )


@pytest.fixture
def challenge_object():
    return Challenge(
        id=1,
        trader_id=0,
        hot_key="",
        user_id=1,
        active="0",
        status="In Challenge",
        challenge="main",
        hotkey_status="Failed",
        message="User's Email and Name is Empty!",
        step=1,
        phase=1,
        response={},
        draw_down=0,
        profit_sum=0,
        register_on_test_net=None,
        register_on_main_net=None,
        pass_the_challenge=None,
        pass_the_main_net_challenge=None,
        challenge_name="",
        created_at="2021-08-01 00:00:00",
        updated_at="2021-08-01 00:00:00",
    )


@pytest.fixture
def payment_read(payment_object):
    payment_object.challenge = {
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
        "response": {},
        "draw_down": 0.0,
        "profit_sum": 0.0,
        "register_on_test_net": None,
        "register_on_main_net": None,
        "pass_the_challenge": None,
        "pass_the_main_net_challenge": None,
        "challenge_name": "",
        "created_at": "2021-08-01T00:00:00",
        "updated_at": "2021-08-01T00:00:00",
    }
    return payment_object, PaymentRead(
        **payment_object.dict(),
    )


@pytest.fixture
def user_object():
    return FirebaseUser(
        id=1,
        firebase_id="firebase",
        email="email@gmail.com",
        name="name",
        username="email",
        created_at="2021-08-01 00:00:00",
        updated_at="2021-08-01 00:00:00",
    )
