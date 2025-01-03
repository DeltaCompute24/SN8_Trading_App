import json

import redis

from src.utils.constants import REDIS_LIVE_PRICES_TABLE

redis_client = redis.StrictRedis(host='redis', port=6379, decode_responses=True)


def get_hash_values(hash_name=REDIS_LIVE_PRICES_TABLE):
    """
    get all the hash values against a key
    """
    return redis_client.hgetall(hash_name)


def get_live_price(trade_pair: str) -> float:
    """
        get the live_price of the trade pair
    """
    current_price = 0.0
    price_object = redis_client.hget(REDIS_LIVE_PRICES_TABLE, trade_pair)
    if price_object:
        price_object = json.loads(price_object)
        current_price = price_object.get("c") or 0.0
    return float(current_price)


def set_live_price(key: str, value: dict):
    """
    set the key, value against a hash set, preserving the types in value object
    """
    redis_client.hset(REDIS_LIVE_PRICES_TABLE, key, json.dumps(value))
