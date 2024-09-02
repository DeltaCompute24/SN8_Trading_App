from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.schemas.transaction import ProfitLossRequest
from src.services.trade_service import get_latest_position, calculate_profit_loss
from src.utils.logging import setup_logging
from src.utils.websocket_manager import websocket_manager
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

    latest_position = await get_latest_position(db, trader_id, trade_pair)
    if not latest_position:
        logger.error("No open position found for this trade pair and trader")
        raise HTTPException(status_code=404, detail="No open position found for this trade pair and trader")

    try:
        # Explicitly log the details of the latest position
        logger.info(f"Latest position details: {latest_position}")

        # Ensure latest_position is a dictionary for logging purposes
        if hasattr(latest_position, "__dict__"):
            logger.info(f"Latest position attributes: {latest_position.__dict__}")
        else:
            logger.warning(f"Latest position has no __dict__ attribute: {latest_position}")

        # Extract and log individual attributes for better visibility
        logger.info(f"Position ID: {latest_position.position_id}")
        logger.info(f"Trader ID: {latest_position.trader_id}")
        logger.info(f"Trade Pair: {latest_position.trade_pair}")
        logger.info(f"Entry Price: {latest_position.entry_price}")
        logger.info(f"Cumulative Leverage: {latest_position.cumulative_leverage}")
        logger.info(f"Cumulative Order Type: {latest_position.cumulative_order_type}")
        logger.info(f"Asset Type: {latest_position.asset_type}")

        # Connect and subscribe to the WebSocket
        websocket = await websocket_manager.connect(latest_position.asset_type)
        subscription_response = await websocket_manager.subscribe(trade_pair)
        logger.info(f"Subscription response: {subscription_response}")

        # Wait for the first price to be received
        first_price = await websocket_manager.listen_for_initial_price()
        if first_price is None:
            logger.error("Failed to fetch current price for the trade pair")
            raise HTTPException(status_code=500, detail="Failed to fetch current price for the trade pair")

        # Log the details used for profit/loss calculation
        logger.info(f"Calculating profit/loss with details: entry_price={latest_position.entry_price}, "
                    f"current_price={first_price}, leverage={latest_position.cumulative_leverage}, "
                    f"order_type={latest_position.cumulative_order_type}, asset_type={latest_position.asset_type}")

        # Calculate profit/loss based on the first price
        profit_loss = calculate_profit_loss(latest_position.entry_price, first_price,
                                            latest_position.cumulative_leverage, latest_position.cumulative_order_type,
                                            latest_position.asset_type)

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
            "profit_loss": profit_loss
        }

    except Exception as e:
        logger.error(f"Error calculating profit/loss: {e}")
        raise HTTPException(status_code=500, detail=str(e))
