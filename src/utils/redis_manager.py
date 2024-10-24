from redis import asyncio as aioredis

from src.config import REDIS_URL

REDIS_LIVE_PRICES_TABLE = 'live_prices'
redis_client = aioredis.from_url(REDIS_URL, decode_responses=True)


def get_live_price(trade_pair: str) -> float:
    current_price = redis_client.hget(REDIS_LIVE_PRICES_TABLE, trade_pair)
    return float(current_price) if current_price else 0.0
