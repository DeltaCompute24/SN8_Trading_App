import json

import redis
from src.schemas.redis_position import RedisQuotesData
from src.utils.constants import REDIS_LIVE_QUOTES_TABLE, REDIS_LIVE_PRICES_TABLE, POSITIONS_TABLE, OPERATION_QUEUE_NAME

redis_client = redis.StrictRedis(host='redis', port=6379, decode_responses=True)


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


def set_hash_value_generic(hash_name, key, value):
    """
    Set the key, value against a hash set in Redis
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


def get_all_trader_returns():
    """
    Retrieve all trader returns from Redis
    """
    trader_returns = redis_client.hgetall("trader_returns")
    return {hot_key: int(float(rank)) for hot_key, rank in trader_returns.items() if float(rank).is_integer()}

def get_trader_data(hot_key):
    """
    Retrieve the most frequently used currency for a trader from Redis
    """
    trader_data = redis_client.hget("trader_data", hot_key)
    return json.loads(trader_data) if trader_data else None


def get_trader_scores_and_weight(hot_key):
    """
    Retrieve the scores and weight for a trader from Redis
    """
    trader_scores_weight = redis_client.hget("trader_rank_data", hot_key)
    return json.loads(trader_scores_weight) if trader_scores_weight else None


def get_top_traders_by_rank_and_metrics(top_n=3):
    """
    Get the top N traders sorted by rank and include their most frequently used currency,
    Sortino, Omega, and Sharpe ratios, and annualized all_time_returns
    """
    trader_returns = get_all_trader_returns()

    
    sorted_traders = sorted(trader_returns.items(), key=lambda x: x[1])
    top_traders = sorted_traders[:top_n]
    
    result = []
    for hot_key, rank in top_traders:
        trader_data = get_trader_data(hot_key)
        trader_scores_weight = get_trader_scores_and_weight(hot_key)
        if not trader_data or not trader_scores_weight:
            continue
        
        result.append({
            "hot_key": hot_key,
            "rank": str(int(float(rank))),
            "trader_pairs": trader_data["trader_pairs"],
            "username": trader_data["username"],
            "email": trader_data["email"],
            "thirty_days_return": trader_data["all_time_returns"],
            "all_time_returns": trader_scores_weight["scores"]["return"]["value"],
            "sortino": trader_scores_weight["scores"]["sortino"]["value"],
            "omega": trader_scores_weight["scores"]["omega"]["value"],
            "sharpe": trader_scores_weight["scores"]["sharpe"]["value"]
        })
    
    return result