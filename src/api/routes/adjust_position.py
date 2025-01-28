from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import text

from src.database import get_db
from src.models.transaction import Status
from src.schemas.monitored_position import MonitoredPositionCreate
from src.schemas.transaction import TransactionUpdate
from src.services.trade_service import update_transaction_async, get_open_or_adjusted_position, update_monitored_positions, \
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
    validate_leverage(position_data.asset_type, position_data.leverage)
    # Get the latest transaction record for the given trader and trade pair
    position = await get_open_or_adjusted_position(db, position_data.trader_id, position_data.trade_pair)
    if not position:
        logger.error("No open position found for this trade pair and trader")
        raise HTTPException(status_code=404, detail="No open position found for this trade pair and trader")
    # await check_get_challenge(db, position_data)
    try:
        prev_leverage = position.leverage
        new_leverage = position_data.leverage

        cumulative_stop_loss = position_data.stop_loss
        cumulative_take_profit = position_data.take_profit
        cumulative_leverage = position.cumulative_leverage
  
        order_type = position.order_type
        leverage = position_data.leverage
        
        if new_leverage != prev_leverage:
            
            leverage = new_leverage - cumulative_leverage
           
            order_type = "SHORT"  if leverage < 0 else "LONG"
            
            leverage = abs(leverage)
            position_data.leverage = leverage
            
            #How should the cumulative leverage be caclculated in each case?
            cumulative_leverage = abs(new_leverage)

        #Should the trade be sent if only the order_type changes?
        adjustment_submitted = await websocket_manager.submit_trade(position_data.trader_id,
                                                                    position_data.trade_pair,
                                                                    order_type,
                                                                          leverage, )
        
        #How are cumulative stop loss and take profit calculated for each case?
        if not adjustment_submitted:
            logger.error("Failed to submit adjustment")
            raise HTTPException(status_code=500, detail="Failed to submit adjustment")
        logger.info("Adjustment submitted successfully")

      
        new_transaction = await update_transaction_async(
            db, 
            position,
            {
            "operation_type" : "adjust",
            order_type : position.order_type, 
            cumulative_leverag : cumulative_leverage,
            cumulative_stop_loss : cumulative_stop_loss,
            cumulative_take_profit : cumulative_take_profit,
            status : Status.adjust_processing if position.status" ==" Status.open else position.status,
            old_status : position.status
            }
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
