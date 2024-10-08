import ast
from datetime import datetime, timedelta

import redis

from src.services.api_service import get_profit_and_current_price
from src.services.user_service import get_challenge

redis_client = redis.StrictRedis(host='localhost', port=6379, db=0)


def get_assets_fee(asset_type):
    if asset_type == "crypto":
        return 0.001
    elif asset_type == "forex":
        return 0.00007
    else:  # for indices
        return 0.00009


def get_taoshi_values(trader_id, trade_pair, initiate=False, position_uuid=None):
    challenge = get_challenge(trader_id, source=True) or "main"

    key = f"{trade_pair}-{trader_id}"
    position = redis_client.hget('positions', key)
    # if position exist in redis
    if position and not position_uuid:
        position = ast.literal_eval(position.decode('utf-8'))
        current_time = datetime.now()
        position_time = datetime.strptime(position[0], '%Y-%m-%d %H:%M:%S.%f')

        difference = abs(current_time - position_time)
        if difference < timedelta(seconds=5):
            if initiate:
                return [challenge, *position[1:]]
            return position[1:]

    # if position doesn't exist and belongs to main net
    main = (challenge.lower() == "main")
    price, profit_loss, profit_loss_without_fee, taoshi_profit_loss, taoshi_profit_loss_without_fee, uuid, hot_key = get_profit_and_current_price(
        trader_id, trade_pair, main=main, position_uuid=position_uuid)
    value = [str(datetime.now()), price, profit_loss, profit_loss_without_fee, taoshi_profit_loss,
             taoshi_profit_loss_without_fee, uuid, hot_key]
    redis_client.hset('positions', f"{trade_pair}-{trader_id}", str(value))

    if initiate:
        return [challenge, *value[1:]]
    return value[1:]
