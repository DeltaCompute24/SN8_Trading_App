from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_db
from src.schemas.transaction import ProfitLossRequest
from src.services.trade_service import get_latest_position, calculate_profit_loss
from src.utils.logging import setup_logging
from src.utils.websocket_manager import websocket_manager

logger = setup_logging()
router = APIRouter()

@router.post("/profit-loss/", response_model=dict)
async def get_profit_loss(profit_loss_request: ProfitLossRequest, db: AsyncSession = Depends(get_db)):
    trader_id = profit_loss_request.trader_id
    trade_pair = profit_loss_request.trade_pair

    logger.info(f"Calculating profit/loss for trader_id={trader_id} and trade_pair={trade_pair}")

    latest_position = await get_latest_position(db, trader_id, trade_pair)
    if not latest_position:
        logger.error("No open position found for this trade pair and trader")
        raise HTTPException(status_code=404, detail="No open position found for this trade pair and trader")

    try:
        # Connect and subscribe to the WebSocket
        websocket = await websocket_manager.connect(latest_position.asset_type)
        subscription_response = await websocket_manager.subscribe(trade_pair)
        logger.info(f"Subscription response: {subscription_response}")

        # Wait for the first price to be received
        first_price = await websocket_manager.listen_for_price()
        if first_price is None:
            logger.error("Failed to fetch current price for the trade pair")
            raise HTTPException(status_code=500, detail="Failed to fetch current price for the trade pair")
        
        # Calculate profit/loss based on the first price
        logger.info(f"Entry price: {latest_position.entry_price}, Current price: {first_price}, Leverage: {latest_position.cumulative_leverage}, Order type: {latest_position.cumulative_order_type}")
        profit_loss = calculate_profit_loss(latest_position.entry_price, first_price, latest_position.cumulative_leverage, latest_position.cumulative_order_type, latest_position.asset_type)

        return {"profit_loss": profit_loss}

    except Exception as e:
        logger.error(f"Error calculating profit/loss: {e}")
        raise HTTPException(status_code=500, detail=str(e))
