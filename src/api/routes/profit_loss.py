from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.schemas.transaction import ProfitLossRequest
from src.services.fee_service import get_taoshi_values
from src.services.trade_service import get_open_position
from src.utils.logging import setup_logging
from src.validations.position import validate_trade_pair

logger = setup_logging()
router = APIRouter()


@router.post("/profit-loss/", response_model=dict)
async def get_profit_loss(profit_loss_request: ProfitLossRequest, db: AsyncSession = Depends(get_db)):
    trader_id = profit_loss_request.trader_id
    trade_pair = profit_loss_request.trade_pair

    logger.info(f"Calculating profit/loss for trader_id={trader_id} and trade_pair={trade_pair}")

    profit_loss_request.asset_type, trade_pair = validate_trade_pair(profit_loss_request.asset_type,
                                                                     profit_loss_request.trade_pair)

    latest_position = await get_open_position(db, trader_id, trade_pair)
    if not latest_position:
        logger.error("No open position found for this trade pair and trader")
        raise HTTPException(status_code=404, detail="No open position found for this trade pair and trader")

    try:
        # Calculate profit/loss based on the first price
        current_price, profit_loss, profit_loss_without_fee, *extras = get_taoshi_values(
            latest_position.trader_id,
            latest_position.trade_pair,
            position_uuid=latest_position.uuid,
            challenge=latest_position.source,
        )

        # Log the calculated profit/loss
        logger.info(f"Calculated profit/loss: {profit_loss}")

        # Return the details in the response
        return {
            "trader_id": trader_id,
            "trade_pair": trade_pair,
            "cumulative_leverage": latest_position.cumulative_leverage,
            "cumulative_order_type": latest_position.cumulative_order_type,
            "cumulative_stop_loss": latest_position.cumulative_stop_loss,
            "cumulative_take_profit": latest_position.cumulative_take_profit,
            "profit_loss": profit_loss,
            "profit_loss_without_fee": profit_loss_without_fee,
        }

    except Exception as e:
        logger.error(f"Error calculating profit/loss: {e}")
        raise HTTPException(status_code=500, detail=str(e))
