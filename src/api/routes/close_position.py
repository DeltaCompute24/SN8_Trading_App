from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_db
from src.schemas.transaction import TradeResponse, ProfitLossRequest, TransactionCreate
from src.services.trade_service import create_transaction, get_open_position, get_latest_position, calculate_profit_loss
from src.utils.logging import setup_logging
from src.utils.websocket_manager import websocket_manager
from datetime import datetime

logger = setup_logging()
router = APIRouter()

@router.post("/close-position/", response_model=TradeResponse)
async def close_position(profit_loss_request: ProfitLossRequest, db: AsyncSession = Depends(get_db)):
    logger.info(f"Closing position for trader_id={profit_loss_request.trader_id} and trade_pair={profit_loss_request.trade_pair}")

    position = await get_open_position(db, profit_loss_request.trader_id, profit_loss_request.trade_pair)
    if not position:
        logger.error("No open position found for this trade pair and trader")
        raise HTTPException(status_code=404, detail="No open position found for this trade pair and trader")

    try:
        # Submit the FLAT signal to close the position
        close_submitted = await websocket_manager.submit_trade(profit_loss_request.trader_id, profit_loss_request.trade_pair, "FLAT", 1)
        if not close_submitted:
            logger.error("Failed to submit close signal")
            raise HTTPException(status_code=500, detail="Failed to submit close signal")

        logger.info("Close signal submitted successfully")

        # Set close_time and close_price
        close_time = datetime.utcnow()

        # Connect and subscribe to the WebSocket
        logger.info(f"Connecting to WebSocket for asset type {position.asset_type}")
        websocket = await websocket_manager.connect(position.asset_type)
        subscription_response = await websocket_manager.subscribe(position.trade_pair)
        logger.info(f"Subscription response: {subscription_response}")

        # Wait for the first price to be received
        close_price = await websocket_manager.listen_for_price()
        if close_price is None:
            logger.error("Failed to fetch current price for the trade pair")
            raise HTTPException(status_code=500, detail="Failed to fetch current price for the trade pair")
        
        logger.info(f"Close price for {position.trade_pair} is {close_price}")

        # Calculate profit/loss
        profit_loss = calculate_profit_loss(position.entry_price, close_price, position.cumulative_leverage, position.order_type, position.asset_type)

        # Fetch the latest transaction for cumulative metrics
        latest_position = await get_latest_position(db, profit_loss_request.trader_id, profit_loss_request.trade_pair)
        if not latest_position:
            logger.error("Failed to fetch the latest position for cumulative metrics")
            raise HTTPException(status_code=500, detail="Failed to fetch the latest position for cumulative metrics")

        # Create a new transaction record to mark the position as closed
        close_transaction_data = TransactionCreate(
            trader_id=profit_loss_request.trader_id,
            trade_pair=profit_loss_request.trade_pair,
            leverage=1,
            asset_type=profit_loss_request.asset_type,
            stop_loss=None,  # Set stop_loss to None
            take_profit=None,  # Set take_profit to None
            order_type="FLAT"
        )

        # Create the close transaction with the calculated profit/loss
        await create_transaction(db, close_transaction_data, entry_price=position.entry_price, operation_type="close", status="CLOSED",
                                 position_id=position.position_id,
                                 trade_order=position.trade_order + 1,
                                 cumulative_leverage=latest_position.cumulative_leverage,
                                 cumulative_stop_loss=latest_position.cumulative_stop_loss,
                                 cumulative_take_profit=latest_position.cumulative_take_profit,
                                 cumulative_order_type=latest_position.cumulative_order_type,
                                 close_time=close_time, close_price=close_price, profit_loss=profit_loss)
        
        logger.info(f"Position closed successfully with close price {close_price} and profit/loss {profit_loss}")
        return TradeResponse(message="Position closed successfully")

    except Exception as e:
        logger.error(f"Error closing position: {e}")
        raise HTTPException(status_code=500, detail=str(e))
