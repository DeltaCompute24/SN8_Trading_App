from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_db
from src.models.transaction import Status
from src.schemas.transaction import Transaction, TradeResponse, ProfitLossRequest
from src.services.trade_service import (
    close_transaction_with_commit,
    close_transaction_without_commit,
    get_latest_position,
    get_transaction_by_order_id,
)
from src.utils.logging import setup_logging
from src.utils.websocket_manager import websocket_manager
from src.validations.position import validate_trade_pair, check_get_challenge
from src.utils.redis_manager import (
    get_live_quote_from_redis,
    get_profit_loss_from_redis,
    delete_hash_value,
)


logger = setup_logging()
router = APIRouter()


@router.post("/close-position/", response_model=Transaction)
async def close_position(
    position_data: ProfitLossRequest, db: AsyncSession = Depends(get_db)
):

    position_data.asset_type, position_data.trade_pair = validate_trade_pair(
        position_data.asset_type, position_data.trade_pair
    )

    position = await get_latest_position(
        db, position_data.trader_id, position_data.trade_pair
    )
    if not position:
        logger.error("No open position found for this trade pair and trader")
        raise HTTPException(
            status_code=404,
            detail="No open or pending position found for this trade pair and trader",
        )
    await check_get_challenge(db, position_data)

    # Submit the FLAT signal to close the position
    status = Status.close
    close_price = 0
    profit_loss = 0.0

    if position.status == Status.pending:
        await close_transaction_with_commit(
            db,
            position.order_id,
            position.trader_id,
            close_price,
            profit_loss=profit_loss,
            old_status=position.status,
            status=status,
        )

    else:
        status = Status.close_processing
        profit_loss = get_profit_loss_from_redis(
            position.trade_pair, position.trader_id
        )
        close_price = get_live_quote_from_redis(
            position.trade_pair, position.order_type
        )

        try:

            await close_transaction_without_commit(
                db,
                position.order_id,
                position.trader_id,
                close_price,
                profit_loss=profit_loss,
                old_status=position.status,
                status=status,
            )

            close_submitted = await websocket_manager.submit_trade(
                position_data.trader_id, position_data.trade_pair, "FLAT", 1
            )
            if not close_submitted:
                logger.error("Failed to submit close signal")
                raise HTTPException(
                    status_code=500, detail="Failed to submit close signal"
                )

            delete_hash_value(f"{position.trade_pair}-{position.trader_id}")
            await db.commit()

        except Exception as e:

            await db.rollback()
            logger.error(f"Error in close position operation: {e}")
            raise HTTPException(
                status_code=500, detail=f"Failed to close position: {str(e)}"
            )
    result = await get_transaction_by_order_id(db, position.order_id)
    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"Transaction with order_id {position.order_id} not found",
        )

    return result
