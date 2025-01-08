from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.schemas.monitored_position import MonitoredPositionCreate
from src.schemas.transaction import TransactionCreate, TradeResponse
from src.services.trade_service import create_transaction, update_monitored_positions, get_non_closed_position
from src.utils.logging import setup_logging
from src.utils.redis_manager import get_live_price
from src.utils.websocket_manager import websocket_manager
from src.validations.position import validate_position, validate_leverage, check_get_challenge

logger = setup_logging()
router = APIRouter()


@router.post("/initiate-position/", response_model=TradeResponse)
async def initiate_position(position_data: TransactionCreate, db: AsyncSession = Depends(get_db)):
    logger.info(
        f"Initiating position for trader_id={position_data.trader_id} and trade_pair={position_data.trade_pair}")

    challenge = await check_get_challenge(db, position_data)
    position_data = validate_position(position_data)
    validate_leverage(position_data.asset_type, position_data.leverage)

    existing_position = await get_non_closed_position(db, position_data.trader_id, position_data.trade_pair)
    if existing_position:
        logger.error("A position already exists for this trade pair and trader")
        raise HTTPException(status_code=400,
                            detail="An open or pending position already exists for this trade pair and trader")

    try:
        upward = -1
        status = "PROCESSING"
        entry_price = position_data.entry_price
        limit_order = position_data.limit_order

        if not challenge:
            raise HTTPException(status_code=400,
                                detail=f"Given Trader ID {position_data.trader_id} does not exist in the system!")
        challenge = challenge.challenge
        profit_loss = 0.0
        profit_loss_without_fee = 0.0
        taoshi_profit_loss = 0.0
        taoshi_profit_loss_without_fee = 0.0
        len_order = 0
        uuid = ""
        hot_key = ""
        average_entry_price = 0.0

        # If entry_price == 0, it is empty then status will be "OPEN" so we can submit trade
        if (not entry_price or entry_price == 0) and (not limit_order or limit_order == 0):
            # Submit the trade and wait for confirmation
            trade_submitted = await websocket_manager.submit_trade(position_data.trader_id, position_data.trade_pair,
                                                                   position_data.order_type, position_data.leverage)
            if not trade_submitted:
                logger.error("Failed to submit trade")
                raise HTTPException(status_code=500, detail="Failed to submit trade")
            logger.info("Trade submitted successfully")
            first_price = 0
        else:
            status = "PENDING"
            first_price = get_live_price(position_data.trade_pair)

            if first_price == 0:
                logger.error("Failed to fetch current price for the trade pair")
                raise HTTPException(status_code=500, detail="Failed to fetch current price for the trade pair")

        initial_price = first_price
        if entry_price and entry_price != 0 and entry_price != first_price:
            # upward: 1, downward: 0
            upward = 1 if entry_price > first_price else 0
            first_price = entry_price
            status = "PENDING"

        # Create the transaction with the first received price
        new_transaction = await create_transaction(db, position_data, entry_price=first_price,
                                                   order_type=position_data.order_type,
                                                   initial_price=initial_price, operation_type="initiate",
                                                   status=status, upward=upward, old_status=status,
                                                   modified_by=str(position_data.trader_id),
                                                   average_entry_price=average_entry_price,
                                                   profit_loss=profit_loss,
                                                   profit_loss_without_fee=profit_loss_without_fee,
                                                   taoshi_profit_loss_without_fee=taoshi_profit_loss_without_fee,
                                                   taoshi_profit_loss=taoshi_profit_loss,
                                                   uuid=uuid,
                                                   hot_key=hot_key,
                                                   source=challenge,
                                                   order_level=len_order,
                                                   max_profit_loss=profit_loss,
                                                   limit_order=limit_order,
                                                   )

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
