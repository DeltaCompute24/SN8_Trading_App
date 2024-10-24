import ast
from datetime import datetime, timedelta

from src.services.api_service import get_profit_and_current_price
from src.utils.redis_manager import set_hash_value, get_hash_value


def get_assets_fee(asset_type):
    if asset_type == "crypto":
        return 0.001
    elif asset_type == "forex":
        return 0.00007
    else:  # for indices
        return 0.00009


def get_taoshi_values(trader_id, trade_pair, position_uuid=None, challenge="main"):
    key = f"{trade_pair}-{trader_id}"
    position = get_hash_value(key=key)
    # if position exist in redis
    if position and not position_uuid:
        position = ast.literal_eval(position)
        current_time = datetime.now()
        position_time = datetime.strptime(position[0], '%Y-%m-%d %H:%M:%S.%f')

        difference = abs(current_time - position_time)
        if difference < timedelta(seconds=5):
            return position[1:]

    # if position doesn't exist and belongs to main net
    main = (challenge.lower() == "main")
    price, profit_loss, profit_loss_without_fee, taoshi_profit_loss, taoshi_profit_loss_without_fee, uuid, hot_key, len_orders, avg_entry_price = get_profit_and_current_price(
        trader_id, trade_pair, main=main, position_uuid=position_uuid)
    value = [str(datetime.now()), price, profit_loss, profit_loss_without_fee, taoshi_profit_loss,
             taoshi_profit_loss_without_fee, uuid, hot_key, len_orders, avg_entry_price]
    if price != 0:
        set_hash_value(key=f"{trade_pair}-{trader_id}", value=str(value))
    return value[1:]
