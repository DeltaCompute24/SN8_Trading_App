import json

from redis import asyncio as aioredis

from src.config import REDIS_URL
from src.utils.constants import REDIS_LIVE_PRICES_TABLE, POSITIONS_TABLE, OPERATION_QUEUE_NAME

redis_client = aioredis.from_url(REDIS_URL, decode_responses=True)


def get_hash_values(hash_name=REDIS_LIVE_PRICES_TABLE):
    """
    get all the hash values against a key
    """
    return redis_client.hgetall(hash_name)


def get_live_price(trade_pair: str) -> float:
    """
        get the live_price of the trade pair
    """
    current_price = redis_client.hget(REDIS_LIVE_PRICES_TABLE, trade_pair)
    return float(current_price) if current_price else 0.0


def get_hash_value(key, hash_name=POSITIONS_TABLE):
    """
    get the value of the hash
    """
    return redis_client.hget(hash_name, key)


def set_hash_value(key, value, hash_name=POSITIONS_TABLE):
    """
    set the key, value against a hash set
    """
    redis_client.hset(hash_name, key, str(value))


def push_to_redis_queue(data, queue_name=OPERATION_QUEUE_NAME):
    redis_client.lpush(queue_name, json.dumps(data))


def get_queue_data(queue_name=OPERATION_QUEUE_NAME):
    return redis_client.lrange(queue_name, 0, -1)


def get_queue_left_item(queue_name=OPERATION_QUEUE_NAME):
    return redis_client.lindex(queue_name, -1)


def pop_queue_right_item(queue_name=OPERATION_QUEUE_NAME):
    redis_client.rpop(queue_name)
