from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import text

from src.database import get_db
from src.schemas.transaction import TradeResponse, ProfitLossRequest
from src.services.trade_service import get_open_position, calculate_profit_loss, close_transaction
from src.utils.logging import setup_logging
from src.utils.websocket_manager import websocket_manager

logger = setup_logging()
router = APIRouter()


@router.post("/close-position/", response_model=TradeResponse)
async def close_position(profit_loss_request: ProfitLossRequest, db: AsyncSession = Depends(get_db)):
    logger.info(
        f"Closing position for trader_id={profit_loss_request.trader_id} and trade_pair={profit_loss_request.trade_pair}")

    position = await get_open_position(db, profit_loss_request.trader_id, profit_loss_request.trade_pair)
    if not position:
        logger.error("No open position found for this trade pair and trader")
        raise HTTPException(status_code=404, detail="No open position found for this trade pair and trader")

    try:
        # Submit the FLAT signal to close the position
        close_submitted = await websocket_manager.submit_trade(profit_loss_request.trader_id,
                                                               profit_loss_request.trade_pair, "FLAT", 1)
        if not close_submitted:
            logger.error("Failed to submit close signal")
            raise HTTPException(status_code=500, detail="Failed to submit close signal")

        logger.info("Close signal submitted successfully")

        # Connect and subscribe to the WebSocket
        logger.info(f"Connecting to WebSocket for asset type {position.asset_type}")
        websocket = await websocket_manager.connect(position.asset_type)
        subscription_response = await websocket_manager.subscribe(position.trade_pair)
        logger.info(f"Subscription response: {subscription_response}")

        # Wait for the first price to be received
        close_price = await websocket_manager.listen_for_initial_price()
        if close_price is None:
            logger.error("Failed to fetch current price for the trade pair")
            raise HTTPException(status_code=500, detail="Failed to fetch current price for the trade pair")

        logger.info(f"Close price for {position.trade_pair} is {close_price}")

        # Calculate profit/loss
        profit_loss = calculate_profit_loss(position.entry_price, close_price, position.cumulative_leverage,
                                            position.order_type, position.asset_type)

        # Close Previous Open Position
        await close_transaction(db, position.order_id, position.trader_id, close_price, profit_loss)

        # Remove closed position from the monitored_positions table
        await db.execute(
            text("DELETE FROM monitored_positions WHERE position_id = :position_id"),
            {"position_id": position.position_id}
        )
        await db.commit()

        logger.info(f"Position closed successfully with close price {close_price} and profit/loss {profit_loss}")
        return TradeResponse(message="Position closed successfully")

    except Exception as e:
        logger.error(f"Error closing position: {e}")
        raise HTTPException(status_code=500, detail=str(e))
