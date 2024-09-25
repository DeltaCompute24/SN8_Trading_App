from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import text

from src.database import get_db
from src.schemas.transaction import TradeResponse, ProfitLossRequest
from src.services.api_service import get_profit_and_current_price
from src.services.trade_service import close_transaction, get_latest_position
from src.utils.logging import setup_logging
from src.utils.websocket_manager import websocket_manager
from src.validations.position import validate_trade_pair

logger = setup_logging()
router = APIRouter()


@router.post("/close-position/", response_model=TradeResponse)
async def close_position(position_data: ProfitLossRequest, db: AsyncSession = Depends(get_db)):
    logger.info(
        f"Closing position for trader_id={position_data.trader_id} and trade_pair={position_data.trade_pair}")

    position_data.asset_type, position_data.trade_pair = validate_trade_pair(position_data.asset_type,
                                                                             position_data.trade_pair)

    position = await get_latest_position(db, position_data.trader_id, position_data.trade_pair)
    if not position:
        logger.error("No open position found for this trade pair and trader")
        raise HTTPException(status_code=404, detail="No open position found for this trade pair and trader")

    try:
        # Submit the FLAT signal to close the position
        if position.status != "PENDING":
            close_submitted = await websocket_manager.submit_trade(position_data.trader_id,
                                                                   position_data.trade_pair, "FLAT", 1)
            if not close_submitted:
                logger.error("Failed to submit close signal")
                raise HTTPException(status_code=500, detail="Failed to submit close signal")

        close_price, taoshi_profit_loss, taoshi_profit_loss_with_fee = get_profit_and_current_price(position.trader_id,
                                                                                                    position.trade_pair)
        if close_price == 0:
            logger.error("Failed to fetch current price for the trade pair")
            raise HTTPException(status_code=500, detail="Failed to fetch current price for the trade pair")

        logger.info(f"Close price for {position.trade_pair} is {close_price}")
        profit_loss = (taoshi_profit_loss * 100) - 100
        profit_loss_with_fee = (taoshi_profit_loss_with_fee * 100) - 100
        # Close Previous Open Position
        await close_transaction(db, position.order_id, position.trader_id, close_price, profit_loss=profit_loss,
                                old_status=position.status, profit_loss_with_fee=profit_loss_with_fee,
                                taoshi_profit_loss=taoshi_profit_loss,
                                taoshi_profit_loss_with_fee=taoshi_profit_loss_with_fee)

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
