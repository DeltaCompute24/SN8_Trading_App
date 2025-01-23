import json
import logging
from datetime import datetime, timedelta

from src.services.api_service import get_profit_and_current_price
from src.utils.redis_manager import set_hash_value, get_hash_value

logger = logging.getLogger(__name__)


def get_taoshi_values(trader_id, trade_pair, position_uuid=None, challenge="main", closed=False) -> list:
    key = f"{trade_pair}-{trader_id}"
    last_index = 11 if closed else -1

    # if position only exists in redis by mainnet because of the celery task for mainnet
    position = get_hash_value(key)
    if position:
        position = json.loads(position)
        
        logger.info(f"********Realtime Price Taken from Redis*********** Position Length : {len(position)} last_index:{last_index}")
        return position[1:last_index]

    # if position doesn't exist we check in test net and set the celery task
    main = (challenge.lower() == "main")
    price, profit_loss, profit_loss_without_fee, taoshi_profit_loss, taoshi_profit_loss_without_fee, uuid, hot_key, len_orders, avg_entry_price, closed = get_profit_and_current_price(
        trader_id,
        trade_pair,
        main=main,
        position_uuid=position_uuid
    )
    value = [str(datetime.now()), price, profit_loss, profit_loss_without_fee, taoshi_profit_loss,
             taoshi_profit_loss_without_fee, uuid, hot_key, len_orders, avg_entry_price, closed]
    if price != 0:
        set_hash_value(key=key, value=value)
    return value[1:last_index]
