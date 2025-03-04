import json
import redis
from src.models.transaction import OrderType
from src.schemas.redis_position import RedisQuotesData
from src.utils.constants import (
    REDIS_LIVE_QUOTES_TABLE,
    REDIS_LIVE_PRICES_TABLE,
    POSITIONS_TABLE,
    OPERATION_QUEUE_NAME,
)

redis_client = redis.StrictRedis(host="redis", port=6379, decode_responses=True)


def get_hash_values(hash_name=REDIS_LIVE_PRICES_TABLE):
    """
    get all the hash values against a key
    """
    return redis_client.hgetall(hash_name)


def get_bid_ask_price(trade_pair: str) -> RedisQuotesData:
    """
    get the bid and ask of the trade pair
    """
    quotes = {"bp": 0.0, "ap": 0.0}
    price_object = redis_client.hget(REDIS_LIVE_QUOTES_TABLE, trade_pair)
    if price_object:
        quotes = json.loads(price_object)
    return RedisQuotesData(bp=quotes.get("bp"), ap=quotes.get("ap"))


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


def set_hash_data(hash_name, data):
    """
    Set a whole dict inside a table
    """
    redis_client.hmset(hash_name, data)


def set_live_price(key: str, value: dict):
    """
    set the key, value against a hash set, preserving the types in value object
    """
    redis_client.hset(REDIS_LIVE_PRICES_TABLE, key, json.dumps(value))


def set_quotes(key: str, value: dict, format=False):
    """
    set the key, value against a hash set, preserving the types in value object
    """
    if format:
        value["bp"] = value.get("b")
        value["ap"] = value.get("a")

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


def get_profit_loss_from_redis(trade_pair: str, trader_id: int) -> int:
    profit_loss = None
    key = f"{trade_pair}-{trader_id}"
    redis_position: str | None = get_hash_value(key)
    if redis_position:
        redis_position: list = json.loads(redis_position)
        profit_loss = redis_position[2]
    print(f"PROFITLOSS from REDIS {key} {profit_loss}")

    return profit_loss


def get_live_quote_from_redis(trade_pair: str, order_type) -> int:
    close_price = None
    key = trade_pair
    live_quotes: str | None = get_hash_value(
        key,
        REDIS_LIVE_QUOTES_TABLE,
    )
    if live_quotes:
        quotes: dict = json.loads(live_quotes)
        close_price = (
            quotes.get("bp") if order_type == OrderType.buy else quotes.get("ap")
        )
    print(f"CLOSE Price from REDIS {key} {close_price}")
    return close_price
