from datetime import datetime, timedelta

import redis

from src.services.api_service import get_profit_and_current_price

redis_client = redis.StrictRedis(host='localhost', port=6379, db=0)


def get_assets_fee(asset_type):
    if asset_type == "crypto":
        return 0.001
    elif asset_type == "forex":
        return 0.00007
    else:  # for indices
        return 0.00009


def get_taoshi_values(trade_pair, trader_id):
    key = f"{trade_pair}-{trader_id}"
    position = redis_client.hget('positions', key)
    if not position:
        return 0.0, 0.0, 0.0, 0.0, 0.0

    position = list(position.decode('utf-8'))
    current_time = datetime.now()

    difference = abs(current_time - position[0])
    if difference < timedelta(seconds=5):
        return position[1:]

    price, profit_loss, profit_loss_without_fee, taoshi_profit_loss, taoshi_profit_loss_without_fee = get_profit_and_current_price(
        trader_id, trade_pair)
    value = [datetime.now(), price, profit_loss, profit_loss_without_fee, taoshi_profit_loss,
             taoshi_profit_loss_without_fee]
    redis_client.hset('positions', f"{trade_pair}-{trader_id}", str(value))
    return value[1:]
