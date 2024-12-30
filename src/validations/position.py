from datetime import datetime

import pytz
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.tournament_service import get_tournament
from src.services.user_service import get_challenge
from src.utils.constants import *
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

    if asset_type not in ["crypto", "forex", "indices", "stocks"]:
        raise HTTPException(status_code=400, detail="Invalid asset type, It should be crypto, forex or stocks!")
    if asset_type == "crypto" and trade_pair not in crypto_pairs:
        raise HTTPException(status_code=400, detail="Invalid trade pair for asset type crypto!")
    if asset_type == "forex" and trade_pair not in forex_pairs:
        raise HTTPException(status_code=400, detail="Invalid trade pair for asset type forex!")
    if asset_type == "indices" and trade_pair not in indices_pairs:
        raise HTTPException(status_code=400, detail="Invalid trade pair for asset type indices!")
    if asset_type == "stocks" and trade_pair not in stocks_pairs:
        raise HTTPException(status_code=400, detail="Invalid trade pair for asset type stocks!")

    return asset_type, trade_pair


def validate_order_type(order_type):
    order_type = order_type.upper()

    if order_type not in ["LONG", "SHORT"]:
        raise HTTPException(status_code=400, detail="Invalid order type, It should be long or short")

    return order_type


def validate_leverage(asset_type, leverage):
    if asset_type == "crypto" and (leverage < CRYPTO_MIN_LEVERAGE or leverage > CRYPTO_MAX_LEVERAGE):
        raise HTTPException(status_code=400,
                            detail=f"Invalid leverage for asset type {asset_type}! Valid Range: {CRYPTO_MIN_LEVERAGE} - {CRYPTO_MAX_LEVERAGE}")
    elif asset_type == "forex" and (leverage < FOREX_MIN_LEVERAGE or leverage > FOREX_MAX_LEVERAGE):
        raise HTTPException(status_code=400,
                            detail=f"Invalid leverage for asset type {asset_type}! Valid Range: {FOREX_MIN_LEVERAGE} - {FOREX_MAX_LEVERAGE}")
    elif asset_type == "indices" and (leverage < INDICES_MIN_LEVERAGE or leverage > INDICES_MAX_LEVERAGE):
        raise HTTPException(status_code=400,
                            detail=f"Invalid leverage for asset type {asset_type}! Valid Range: {INDICES_MIN_LEVERAGE} - {INDICES_MAX_LEVERAGE}")
    elif asset_type == "stocks" and (leverage < STOCKS_MIN_LEVERAGE or leverage > STOCKS_MAX_LEVERAGE):
        raise HTTPException(status_code=400,
                            detail=f"Invalid leverage for asset type {asset_type}! Valid Range: {STOCKS_MIN_LEVERAGE} - {STOCKS_MAX_LEVERAGE}")

    return leverage


async def check_get_challenge(db: AsyncSession, position_data):
    challenge = get_challenge(position_data.trader_id)

    if not challenge.tournament_id:
        return challenge

    tournament = await get_tournament(db, challenge.tournament_id)  # Await the async function
    if not tournament:
        raise HTTPException(
            status_code=404,
            detail="Tournament not found."
        )
    if not tournament.active:
        raise HTTPException(
            status_code=404,
            detail="Tournament is not active."
        )
    now = datetime.now(pytz.utc).replace(second=0, microsecond=0).replace(tzinfo=None)
    # if tournament.start_time > now:
    #     raise HTTPException(
    #         status_code=400,
    #         detail=f"Tournament has not started yet. It will start at {tournament.start_time} utc."
    #     )
    # if tournament.end_time <= now:
    #     raise HTTPException(
    #         status_code=400,
    #         detail=f"Tournament has already ended. It ended at {tournament.end_time} utc."
    #     )
    return challenge
