from fastapi import HTTPException

from src.utils.constants import crypto_pairs, forex_pairs, indices_pairs
from src.utils.logging import setup_logging

logger = setup_logging()


def validate_position(position, adjust=False):
    asset_type, trade_pair = validate_trade_pair(position.asset_type, position.trade_pair)
    if not adjust:
        order_type = validate_order_type(position.order_type)
        position.order_type = order_type
    position.asset_type = asset_type
    position.trade_pair = trade_pair

    if position.stop_loss is None:
        position.stop_loss = 0
    if position.take_profit is None:
        position.take_profit = 0

    return position


def validate_trade_pair(asset_type, trade_pair):
    asset_type = asset_type.lower()
    trade_pair = trade_pair.upper()

    if asset_type not in ["crypto", "forex", "indices"]:
        raise HTTPException(status_code=400, detail="Invalid asset type, It should be crypto or forex!")
    if asset_type == "crypto" and trade_pair not in crypto_pairs:
        raise HTTPException(status_code=400, detail="Invalid trade pair for asset type crypto!")
    if asset_type == "forex" and trade_pair not in forex_pairs:
        raise HTTPException(status_code=400, detail="Invalid trade pair for asset type forex!")
    if asset_type == "indices" and trade_pair not in indices_pairs:
        raise HTTPException(status_code=400, detail="Invalid trade pair for asset type indices!")

    return asset_type, trade_pair


def validate_order_type(order_type):
    order_type = order_type.upper()

    if order_type not in ["LONG", "SHORT"]:
        raise HTTPException(status_code=400, detail="Invalid order type, It should be long, short or flat")

    return order_type
