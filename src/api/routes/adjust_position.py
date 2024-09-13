from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import text

from src.database import get_db
from src.schemas.monitored_position import MonitoredPositionCreate
from src.schemas.transaction import TransactionCreate
from src.services.trade_service import create_transaction, get_open_position, update_monitored_positions, \
    close_transaction, calculate_profit_loss
from src.services.user_service import get_user_challenge_level
from src.utils.logging import setup_logging
from src.utils.websocket_manager import websocket_manager
from src.validations.position import validate_position

logger = setup_logging()
router = APIRouter()


@router.post("/adjust-position/", response_model=dict)
async def adjust_position_endpoint(position_data: TransactionCreate, db: AsyncSession = Depends(get_db)):
    logger.info(f"Adjusting position for trader_id={position_data.trader_id} and trade_pair={position_data.trade_pair}")

    position_data = validate_position(position_data)

    # Get the latest transaction record for the given trader and trade pair
    position = await get_open_position(db, position_data.trader_id, position_data.trade_pair)
    if not position:
        logger.error("No open position found for this trade pair and trader")
        raise HTTPException(status_code=404, detail="No open position found for this trade pair and trader")

    try:
        logger.info(f"Latest position: {position}")

        # Calculate new leverage based on the cumulative order type
        if (position.cumulative_order_type == 'LONG' and position_data.order_type.upper() == 'LONG') or \
                (position.cumulative_order_type == 'SHORT' and position_data.order_type.upper() == 'SHORT'):
            new_leverage = position.cumulative_leverage + position_data.leverage
        else:
            new_leverage = position.cumulative_leverage - position_data.leverage

        # Determine the new cumulative order type
        if new_leverage == 0:
            cumulative_order_type = 'FLAT'
            new_leverage = 0
        elif new_leverage < 0:
            cumulative_order_type = 'SHORT'
            new_leverage = abs(new_leverage)
        else:  # new_leverage > 0
            cumulative_order_type = 'LONG'

        logger.info(f"New leverage: {new_leverage}, Updated cumulative order type: {cumulative_order_type}")

        # Update cumulative values based on the latest position
        cumulative_leverage = abs(new_leverage)  # Ensure cumulative leverage is always positive
        cumulative_stop_loss = position_data.stop_loss
        cumulative_take_profit = position_data.take_profit

        # Connect and subscribe to the WebSocket
        logger.info(f"Connecting to WebSocket for asset type {position.asset_type}")
        websocket = await websocket_manager.connect(position.asset_type)
        subscription_response = await websocket_manager.subscribe(position.trade_pair)
        logger.info(f"Subscription response: {subscription_response}")

        realtime_price = await websocket_manager.listen_for_initial_price()
        prev_avg_entry_price = position.average_entry_price if position.average_entry_price else 0.0
        if cumulative_leverage != 0:
            average_entry_price = (prev_avg_entry_price * position.cumulative_leverage
                                   + realtime_price * position_data.leverage) / cumulative_leverage
        else:
            average_entry_price = prev_avg_entry_price

        logger.info(
            f"Cumulative leverage: {cumulative_leverage}, Cumulative stop loss: {cumulative_stop_loss}, Cumulative take profit: {cumulative_take_profit}, Cumulative order type: {cumulative_order_type}")

        # Submit the adjustment signal
        adjustment_submitted = await websocket_manager.submit_trade(position_data.trader_id, position_data.trade_pair,
                                                                    position_data.order_type, position_data.leverage)
        if not adjustment_submitted:
            logger.error("Failed to submit adjustment")
            raise HTTPException(status_code=500, detail="Failed to submit adjustment")

        logger.info("Adjustment submitted successfully")

        # Calculate profit/loss
        profit_loss = calculate_profit_loss(position, realtime_price)

        challenge_level = await get_user_challenge_level(db, position_data.trader_id)
        entry_price_list = position.entry_price_list if position.entry_price_list else []
        leverage_list = position.leverage_list if position.leverage_list else []
        order_type_list = position.order_type_list if position.order_type_list else []

        # Create a new transaction record with updated values
        new_transaction = await create_transaction(
            db, position_data, entry_price=position.entry_price, operation_type="adjust",
            position_id=position.position_id, initial_price=position.initial_price,
            cumulative_leverage=cumulative_leverage,
            cumulative_stop_loss=cumulative_stop_loss,
            cumulative_take_profit=cumulative_take_profit,
            cumulative_order_type=cumulative_order_type,
            status=position.status,
            old_status=position.old_status,
            challenge_level=challenge_level,
            modified_by=str(position_data.trader_id),
            upward=position.upward,
            average_entry_price=average_entry_price,
            entry_price_list=entry_price_list + [realtime_price],
            leverage_list=leverage_list + [position_data.leverage],
            order_type_list=order_type_list + [position_data.order_type],
        )

        await close_transaction(db, position.order_id, position.trader_id, realtime_price, profit_loss,
                                old_status=position.status, challenge_level=challenge_level)

        # Remove old monitored position
        await db.execute(
            text("DELETE FROM monitored_positions WHERE position_id = :position_id"),
            {"position_id": position.position_id}
        )
        await db.commit()

        # Update the monitored_positions table with the new transaction
        await update_monitored_positions(
            db,
            MonitoredPositionCreate(
                position_id=new_transaction.position_id,
                order_id=new_transaction.trade_order,
                trader_id=new_transaction.trader_id,
                trade_pair=new_transaction.trade_pair,
                cumulative_leverage=new_transaction.cumulative_leverage,
                cumulative_order_type=new_transaction.cumulative_order_type,
                cumulative_stop_loss=new_transaction.cumulative_stop_loss,
                cumulative_take_profit=new_transaction.cumulative_take_profit,
                asset_type=new_transaction.asset_type,
                entry_price=new_transaction.entry_price
            )
        )

        logger.info("Position adjusted successfully")
        return {
            "message": "Position adjusted successfully",
            "data": {
                "position_id": new_transaction.position_id,
                "trader_id": new_transaction.trader_id,
                "trade_pair": new_transaction.trade_pair,
                "cumulative_leverage": new_transaction.cumulative_leverage,
                "cumulative_order_type": new_transaction.cumulative_order_type,
                "cumulative_stop_loss": new_transaction.cumulative_stop_loss,
                "cumulative_take_profit": new_transaction.cumulative_take_profit,
                "asset_type": new_transaction.asset_type,
                "entry_price": new_transaction.entry_price,
            }
        }
    except Exception as e:
        logger.error(f"Error adjusting position: {e}")
        raise HTTPException(status_code=500, detail=str(e))
