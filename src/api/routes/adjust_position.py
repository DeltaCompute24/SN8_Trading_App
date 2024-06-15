from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_db
from src.schemas.transaction import TransactionCreate, TradeResponse
from src.services.trade_service import create_transaction, get_latest_position
from src.utils.logging import setup_logging
from src.utils.websocket_manager import websocket_manager

logger = setup_logging()
router = APIRouter()

@router.post("/adjust-position/", response_model=TradeResponse)
async def adjust_position_endpoint(position_data: TransactionCreate, db: AsyncSession = Depends(get_db)):
    logger.info(f"Adjusting position for trader_id={position_data.trader_id} and trade_pair={position_data.trade_pair}")

    # Get the latest transaction record for the given trader and trade pair
    latest_position = await get_latest_position(db, position_data.trader_id, position_data.trade_pair)
    if not latest_position:
        logger.error("No open position found for this trade pair and trader")
        raise HTTPException(status_code=404, detail="No open position found for this trade pair and trader")

    try:
        logger.info(f"Latest position: {latest_position}")

        # Determine if the new trade is the same type (LONG/SHORT) as the existing trade
        if (latest_position.order_type == 'LONG' and position_data.order_type.upper() == 'LONG') or \
           (latest_position.order_type == 'SHORT' and position_data.order_type.upper() == 'SHORT'):
            new_leverage = latest_position.cumulative_leverage + position_data.leverage
        else:
            new_leverage = latest_position.cumulative_leverage - position_data.leverage

        # Update the order type based on the resulting leverage
        if new_leverage == 0:
            position_data.order_type = 'FLAT'
            new_leverage = 0
        elif new_leverage < 0:
            position_data.order_type = 'SHORT'
            new_leverage = abs(new_leverage)
        else:  # new_leverage > 0
            position_data.order_type = 'LONG'

        logger.info(f"New leverage: {new_leverage}, Updated order type: {position_data.order_type}")

        # Update cumulative values based on the latest position
        cumulative_leverage = abs(new_leverage)  # Ensure cumulative leverage is always positive
        cumulative_stop_loss = position_data.stop_loss
        cumulative_take_profit = position_data.take_profit
        cumulative_order_type = position_data.order_type

        logger.info(f"Cumulative leverage: {cumulative_leverage}, Cumulative stop loss: {cumulative_stop_loss}, Cumulative take profit: {cumulative_take_profit}, Cumulative order type: {cumulative_order_type}")

        # Submit the adjustment signal
        adjustment_submitted = await websocket_manager.submit_trade(position_data.trader_id, position_data.trade_pair, position_data.order_type, position_data.leverage)
        if not adjustment_submitted:
            logger.error("Failed to submit adjustment")
            raise HTTPException(status_code=500, detail="Failed to submit adjustment")

        logger.info("Adjustment submitted successfully")

        # Create a new transaction record with updated values
        await create_transaction(
            db, position_data, entry_price=latest_position.entry_price, operation_type="adjust",
            position_id=latest_position.position_id,
            trade_order=latest_position.trade_order + 1,
            cumulative_leverage=cumulative_leverage,
            cumulative_stop_loss=cumulative_stop_loss,
            cumulative_take_profit=cumulative_take_profit,
            cumulative_order_type=cumulative_order_type
        )
        logger.info("Position adjusted successfully")
        return TradeResponse(message="Position adjusted successfully")

    except Exception as e:
        logger.error(f"Error adjusting position: {e}")
        raise HTTPException(status_code=500, detail=str(e))
