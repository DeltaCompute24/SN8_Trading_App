import json

import redis

from src.config import REDIS_HOST
from src.utils.constants import REDIS_LIVE_PRICES_TABLE

redis_client = redis.StrictRedis(host='redis', port=6379, decode_responses=True)
hosted_redis = redis.StrictRedis(host=REDIS_HOST, port=6379, decode_responses=True)


def get_hash_values(hash_name=REDIS_LIVE_PRICES_TABLE, hosted=False):
    """
    get all the hash values against a key
    """
    if hosted:
        return hosted_redis.hgetall(hash_name)
    return redis_client.hgetall(hash_name)


def set_live_price(key: str, value: dict):
    """
    set the key, value against a hash set, preserving the types in value object
    """
    redis_client.hset(REDIS_LIVE_PRICES_TABLE, key, json.dumps(value))
