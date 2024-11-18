import json

import redis

from src.utils.constants import REDIS_LIVE_PRICES_TABLE, POSITIONS_TABLE, OPERATION_QUEUE_NAME

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


def set_live_price(key: str, value: dict):
    """
    set the key, value against a hash set, preserving the types in value object
    """
    redis_client.hset(REDIS_LIVE_PRICES_TABLE, key, json.dumps(value))


def push_to_redis_queue(data, queue_name=OPERATION_QUEUE_NAME):
    redis_client.lpush(queue_name, json.dumps(data))


def get_queue_data(queue_name=OPERATION_QUEUE_NAME):
    return redis_client.lrange(queue_name, 0, -1)


def get_queue_left_item(queue_name=OPERATION_QUEUE_NAME):
    return redis_client.lindex(queue_name, -1)


def pop_queue_right_item(queue_name=OPERATION_QUEUE_NAME):
    redis_client.rpop(queue_name)


def delete_hash_value(key, hash_name=REDIS_LIVE_PRICES_TABLE):
    redis_client.hdel(hash_name, key)
