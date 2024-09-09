from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.schemas.monitored_position import MonitoredPositionCreate
from src.schemas.transaction import TransactionCreate, TradeResponse
from src.services.trade_service import create_transaction, get_open_position, update_monitored_positions
from src.services.user_service import get_user_challenge_level
from src.utils.logging import setup_logging
from src.utils.websocket_manager import websocket_manager
from src.validations.position import validate_position

logger = setup_logging()
router = APIRouter()


@router.post("/initiate-position/", response_model=TradeResponse)
async def initiate_position(position_data: TransactionCreate, db: AsyncSession = Depends(get_db)):
    logger.info(
        f"Initiating position for trader_id={position_data.trader_id} and trade_pair={position_data.trade_pair}")

    position_data = validate_position(position_data)

    existing_position = await get_open_position(db, position_data.trader_id, position_data.trade_pair)
    if existing_position:
        logger.error("An open position already exists for this trade pair and trader")
        raise HTTPException(status_code=400, detail="An open position already exists for this trade pair and trader")

    try:
        # Connect and subscribe to the WebSocket
        websocket = await websocket_manager.connect(position_data.asset_type)
        subscription_response = await websocket_manager.subscribe(position_data.trade_pair)
        logger.info(f"Subscription response: {subscription_response}")

        # Wait for the first price to be received
        first_price = await websocket_manager.listen_for_initial_price()
        upward = -1
        if first_price is None:
            logger.error("Failed to fetch current price for the trade pair")
            raise HTTPException(status_code=500, detail="Failed to fetch current price for the trade pair")

        # Submit the trade and wait for confirmation
        trade_submitted = await websocket_manager.submit_trade(position_data.trader_id, position_data.trade_pair,
                                                               position_data.order_type, position_data.leverage)
        if not trade_submitted:
            logger.error("Failed to submit trade")
            raise HTTPException(status_code=500, detail="Failed to submit trade")

        logger.info("Trade submitted successfully")
        entry_price = position_data.entry_price
        initial_price = first_price
        status = "OPEN"
        if entry_price and entry_price != 0 and entry_price != first_price:
            # upward: 1, downward: 0
            upward = 1 if entry_price > first_price else 0
            first_price = entry_price
            status = "PENDING"

        challenge_level = await get_user_challenge_level(db, position_data.trader_id)

        # Create the transaction with the first received price
        new_transaction = await create_transaction(db, position_data, entry_price=first_price,
                                                   initial_price=initial_price, operation_type="initiate",
                                                   status=status, upward=upward, old_status=status,
                                                   challenge_level=challenge_level,
                                                   modified_by=str(position_data.trader_id))

        # Create MonitoredPositionCreate data
        monitored_position_data = MonitoredPositionCreate(
            position_id=new_transaction.position_id,
            order_id=new_transaction.trade_order,
            trader_id=new_transaction.trader_id,
            trade_pair=new_transaction.trade_pair,
            cumulative_leverage=new_transaction.cumulative_leverage,
            cumulative_order_type=new_transaction.cumulative_order_type,
            cumulative_stop_loss=new_transaction.cumulative_stop_loss,
            cumulative_take_profit=new_transaction.cumulative_take_profit,
            asset_type=new_transaction.asset_type,
            entry_price=new_transaction.entry_price,
        )

        # Update the monitored_positions table
        await update_monitored_positions(db, monitored_position_data)

        logger.info(f"Position initiated successfully with entry price {first_price}")
        return TradeResponse(message="Position initiated successfully")

    except Exception as e:
        logger.error(f"Error initiating position: {e}")
        raise HTTPException(status_code=500, detail=str(e))
