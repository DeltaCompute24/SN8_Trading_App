from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import text

from src.database import get_db
from src.models.transaction import Status
from src.schemas.monitored_position import MonitoredPositionCreate
from src.schemas.transaction import TransactionUpdate
from src.services.trade_service import create_transaction, get_open_position, update_monitored_positions, \
    close_transaction
from src.utils.logging import setup_logging
from src.utils.websocket_manager import websocket_manager
from src.validations.position import validate_position, validate_leverage, check_get_challenge

logger = setup_logging()
router = APIRouter()


@router.post("/adjust-position/", response_model=dict)
async def adjust_position_endpoint(position_data: TransactionUpdate, db: AsyncSession = Depends(get_db)):
    logger.info(f"Adjusting position for trader_id={position_data.trader_id} and trade_pair={position_data.trade_pair}")

    position_data = validate_position(position_data, adjust=True)

    # Get the latest transaction record for the given trader and trade pair
    position = await get_open_position(db, position_data.trader_id, position_data.trade_pair)
    if not position:
        logger.error("No open position found for this trade pair and trader")
        raise HTTPException(status_code=404, detail="No open position found for this trade pair and trader")
    await check_get_challenge(db, position_data)
    try:
        prev_leverage = position.leverage
        new_leverage = position_data.leverage

        cumulative_stop_loss = position_data.stop_loss
        cumulative_take_profit = position_data.take_profit
        realtime_price = position.entry_price or 0.0
        profit_loss = position.profit_loss or 0.0
        profit_loss_without_fee = position.profit_loss_without_fee or 0.0
        taoshi_profit_loss = position.taoshi_profit_loss or 0.0
        taoshi_profit_loss_without_fee = position.taoshi_profit_loss_without_fee or 0.0
        len_order = position.order_level
        position_data.leverage = position.leverage
        cumulative_leverage = position.cumulative_leverage
        average_entry_price = position.average_entry_price
        max_profit_loss = position.max_profit_loss
        status = Status.open

        if new_leverage != prev_leverage:
            status = Status.adjust_processing
            # Calculate new leverage based on the cumulative order type
            leverage = new_leverage - cumulative_leverage
            order_type = position.order_type
            if leverage < 0:
                order_type = "SHORT" if position.order_type == "LONG" else "LONG"
                leverage = abs(leverage)
            position_data.leverage = leverage
            cumulative_leverage = abs(new_leverage)
            validate_leverage(position_data.asset_type, leverage)

            # Submit the adjustment signal
            adjustment_submitted = await websocket_manager.submit_trade(position_data.trader_id,
                                                                        position_data.trade_pair,
                                                                        order_type,
                                                                        leverage, )
            if not adjustment_submitted:
                logger.error("Failed to submit adjustment")
                raise HTTPException(status_code=500, detail="Failed to submit adjustment")
            logger.info("Adjustment submitted successfully")

        # Create a new transaction record with updated values
        new_transaction = await create_transaction(
            db, position_data, entry_price=position.entry_price, operation_type="adjust",
            order_type=position.order_type, position_id=position.position_id, initial_price=position.initial_price,
            cumulative_leverage=cumulative_leverage,
            cumulative_stop_loss=cumulative_stop_loss,
            cumulative_take_profit=cumulative_take_profit,
            cumulative_order_type=position.cumulative_order_type,
            status=status,
            old_status=position.status,
            modified_by=str(position_data.trader_id),
            upward=position.upward,
            profit_loss=profit_loss,
            profit_loss_without_fee=profit_loss_without_fee,
            average_entry_price=average_entry_price,
            taoshi_profit_loss=taoshi_profit_loss,
            taoshi_profit_loss_without_fee=taoshi_profit_loss_without_fee,
            uuid=position.uuid,
            hot_key=position.hot_key,
            source=position.source,
            order_level=len_order,
            max_profit_loss=max_profit_loss,
            limit_order=position.limit_order,
            open_time=position.open_time,
            adjust_time=datetime.utcnow(),
        )

        await close_transaction(db, position.order_id, position.trader_id, realtime_price, profit_loss,
                                old_status=position.status, profit_loss_without_fee=profit_loss_without_fee,
                                order_level=position.order_level, average_entry_price=average_entry_price,
                                taoshi_profit_loss=taoshi_profit_loss, operation_type="adjust",
                                taoshi_profit_loss_without_fee=taoshi_profit_loss_without_fee,
                                )

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

        return {
            "message": "Position adjusted successfully",
            "data": {
                "position_id": new_transaction.position_id,
                "trader_id": new_transaction.trader_id,
                "trade_pair": new_transaction.trade_pair,
                "leverage": new_transaction.leverage,
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
