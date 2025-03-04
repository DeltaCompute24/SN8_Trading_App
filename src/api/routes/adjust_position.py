from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_db
from src.models.transaction import Status
from src.schemas.transaction import TransactionUpdate, TransactionUpdateDatabase
from src.services.trade_service import (
    update_transaction_async,
    get_open_or_adjusted_position,
)
from src.utils.logging import setup_logging
from src.utils.websocket_manager import websocket_manager
from src.validations.position import validate_position, validate_leverage
from datetime import datetime, timezone


logger = setup_logging()
router = APIRouter()


@router.post("/adjust-position/", response_model=dict)
async def adjust_position_endpoint(
    position_data: TransactionUpdate, db: AsyncSession = Depends(get_db)
):
    """
    Only leverage and SL/TP  is allowed. Submits to Taoshi only when leverage changes

    """

    position_data = validate_position(position_data, adjust=True)
    validate_leverage(position_data.asset_type, position_data.leverage)
    # Get the latest transaction record for the given trader and trade pair
    position = await get_open_or_adjusted_position(
        db, position_data.trader_id, position_data.trade_pair
    )
    if not position:
        logger.error("No open position found for this trade pair and trader")
        raise HTTPException(
            status_code=404,
            detail="No open position found for this trade pair and trader",
        )
    # await check_get_challenge(db, position_data)
    try:
        prev_leverage = position.leverage
        new_leverage = position_data.leverage

        # Prevent Monitoring if only Sl/TP changed. As in this case no new trade is submited
        status = Status.open
        cumulative_stop_loss = position_data.stop_loss
        cumulative_take_profit = position_data.take_profit
        cumulative_leverage = position.cumulative_leverage

        order_type = position.order_type
        leverage = position_data.leverage

        if new_leverage != prev_leverage:
            leverage = new_leverage - cumulative_leverage
            order_type = "SHORT" if leverage < 0 else "LONG"
            leverage = abs(leverage)
            adjustment_submitted = await websocket_manager.submit_trade(
                position_data.trader_id,
                position_data.trade_pair,
                order_type,
                leverage,
            )

            if not adjustment_submitted:
                logger.error("Failed to submit adjustment")
                raise HTTPException(
                    status_code=500, detail="Failed to submit adjustment"
                )

            # Monitoring is done through Trade Status, hence here the trade should be monitored for updated data
            status = Status.adjust_processing

        updated_transaction = await update_transaction_async(
            db,
            position,
            TransactionUpdateDatabase(
                operation_type="adjust",
                order_type=position.order_type,
                leverage=new_leverage,
                cumulative_leverage=leverage,
                stop_loss=cumulative_stop_loss,
                take_profit=cumulative_take_profit,
                cumulative_stop_loss=cumulative_stop_loss,
                cumulative_take_profit=cumulative_take_profit,
                status=status if position.status == Status.open else position.status,
                old_status=position.status,
                adjust_time=datetime.now(),
            ),
        )

        return {
            "message": "Position adjusted successfully",
            "data": {
                "position_id": updated_transaction.position_id,
                "trader_id": updated_transaction.trader_id,
                "trade_pair": updated_transaction.trade_pair,
                "leverage": updated_transaction.leverage,
                "cumulative_leverage": updated_transaction.cumulative_leverage,
                "cumulative_order_type": updated_transaction.cumulative_order_type,
                "cumulative_stop_loss": updated_transaction.cumulative_stop_loss,
                "cumulative_take_profit": updated_transaction.cumulative_take_profit,
                "asset_type": updated_transaction.asset_type,
                "entry_price": updated_transaction.entry_price,
            },
        }
    except Exception as e:
        logger.error(f"Error adjusting position: {e}")
        raise HTTPException(status_code=500, detail=str(e))
