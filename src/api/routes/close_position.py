from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import text
from src.database import get_db
from src.models.transaction import Status
from src.schemas.transaction import TradeResponse, ProfitLossRequest
from src.services.trade_service import close_transaction, get_latest_position
from src.utils.logging import setup_logging
from src.utils.websocket_manager import websocket_manager
from src.validations.position import validate_trade_pair, check_get_challenge
from src.utils.redis_manager import set_hash_value, get_hash_value, delete_hash_value
import json

logger = setup_logging()
router = APIRouter()


@router.post("/close-position/", response_model=TradeResponse)
async def close_position(position_data: ProfitLossRequest, db: AsyncSession = Depends(get_db)):
 
    position_data.asset_type, position_data.trade_pair = validate_trade_pair(position_data.asset_type,
                                                                             position_data.trade_pair)

    position = await get_latest_position(db, position_data.trader_id, position_data.trade_pair)
    if not position:
        logger.error("No open position found for this trade pair and trader")
        raise HTTPException(status_code=404, detail="No open or pending position found for this trade pair and trader")
    await check_get_challenge(db, position_data)
    try:
        # Submit the FLAT signal to close the position
        status = Status.close
        close_price = position.entry_price or 0.0
        profit_loss = position.profit_loss or 0.0
        profit_loss_without_fee = position.profit_loss_without_fee or 0.0
        taoshi_profit_loss = position.taoshi_profit_loss or 0.0
        taoshi_profit_loss_without_fee = position.taoshi_profit_loss_without_fee or 0.0
        len_order = position.order_level
        average_entry_price = position.average_entry_price

        if position.status != "PENDING":
            status = Status.close_processing
            close_submitted = await websocket_manager.submit_trade(position_data.trader_id,
                                                                   position_data.trade_pair, "FLAT", 1)
            if not close_submitted:
                logger.error("Failed to submit close signal")
                raise HTTPException(status_code=500, detail="Failed to submit close signal")
       

        #Getting the return value from redis for immediate return update and then updating it to actual value through monitoring
        redis_position : str | None = get_hash_value(f"{ position_data.trade_pair}-{position_data.trader_id}")
        if redis_position:
            redis_position : list = json.loads(redis_position)
            profit_loss =  redis_position[2]
            print(f"PROFTLOSS from REDIS {profit_loss}")
            
        
        # Close Previous Open Position
        await close_transaction(db, position.order_id, position.trader_id, close_price, profit_loss=profit_loss,
                                old_status=position.status, profit_loss_without_fee=profit_loss_without_fee,
                                taoshi_profit_loss=taoshi_profit_loss, status=status,
                                taoshi_profit_loss_without_fee=taoshi_profit_loss_without_fee, order_level=len_order,
                                average_entry_price=average_entry_price)

        delete_hash_value(f"{position.trade_pair}-{position.trader_id}")


        return TradeResponse(message="Position closed successfully")

    except Exception as e:
        logger.error(f"Error closing position: {e}")
        raise HTTPException(status_code=500, detail=str(e))
