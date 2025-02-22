import json

import redis
from urllib.parse import urlparse
from src.schemas.redis_position import RedisQuotesData
from src.config import REDIS_URL
from src.utils.constants import REDIS_LIVE_QUOTES_TABLE, REDIS_LIVE_PRICES_TABLE, POSITIONS_TABLE, OPERATION_QUEUE_NAME

parsed_url = urlparse(REDIS_URL)
redis_client = redis.StrictRedis(
    host=parsed_url.hostname,
    port=parsed_url.port or 6379,
    decode_responses=True
)


def get_hash_values(hash_name=REDIS_LIVE_PRICES_TABLE):
    """
    get all the hash values against a key
    """
    return redis_client.hgetall(hash_name)


def get_bid_ask_price(trade_pair: str) -> RedisQuotesData:
    """
        get the bid and ask of the trade pair
    """
    quotes = { "bp" : 0.0 , "ap" : 0.0}
    price_object = redis_client.hget(REDIS_LIVE_QUOTES_TABLE, trade_pair)
    if price_object:
        quotes = json.loads(price_object)
    return RedisQuotesData(bp= quotes.get("bp") , ap=quotes.get("ap") )


def get_hash_value(key, hash_name=POSITIONS_TABLE):
    """
    get the value of the hash
    """
    return redis_client.hget(hash_name, key)

def get_all_hash_value(hash_name=POSITIONS_TABLE):
    """
    get the value of the hash
    """
    return redis_client.hgetall(hash_name)


def set_hash_value(key, value, hash_name=POSITIONS_TABLE):
    """
    set the key, value against a hash set
    """
    redis_client.hset(hash_name, key, json.dumps(value))


def set_live_price(key: str, value: dict):
    """
    set the key, value against a hash set, preserving the types in value object
    """
    redis_client.hset(REDIS_LIVE_PRICES_TABLE, key, json.dumps(value))

def set_quotes(key: str, value: dict , format = False):
    """
    set the key, value against a hash set, preserving the types in value object
    """
    if format:
        value['bp'] = value.get('b')
        value['ap'] = value.get('a')
    
    redis_client.hset(REDIS_LIVE_QUOTES_TABLE, key, json.dumps(value))


def push_to_redis_queue(data, queue_name=OPERATION_QUEUE_NAME):
    redis_client.lpush(queue_name, data)


def get_queue_data(queue_name=OPERATION_QUEUE_NAME):
    return redis_client.lrange(queue_name, 0, -1)


def get_queue_right_item(queue_name=OPERATION_QUEUE_NAME):
    return redis_client.lindex(queue_name, -1)


def pop_queue_right_item(queue_name=OPERATION_QUEUE_NAME, count=1):
    redis_client.rpop(queue_name, count=count)


def delete_hash_value(key, hash_name=POSITIONS_TABLE):
    redis_client.hdel(hash_name, key)
