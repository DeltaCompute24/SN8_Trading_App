from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from src.database import get_db
from src.schemas.position import PositionCreate, TradeResponse, ProfitLossRequest, Position as PositionSchema
from src.models.position import Position
from src.services.trade_service import create_position, get_open_position, get_latest_position, calculate_profit_loss
from src.utils.logging import setup_logging
from src.utils.websocket_manager import websocket_manager
from datetime import datetime

logger = setup_logging()
router = APIRouter()

@router.post("/initiate-position/", response_model=TradeResponse)
async def initiate_position(position_data: PositionCreate, db: AsyncSession = Depends(get_db)):
    logger.info(f"Initiating position for trader_id={position_data.trader_id} and trade_pair={position_data.trade_pair}")

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
        first_price = await websocket_manager.listen_for_price()
        if first_price is None:
            logger.error("Failed to fetch current price for the trade pair")
            raise HTTPException(status_code=500, detail="Failed to fetch current price for the trade pair")
        
        # Submit the trade and wait for confirmation
        trade_submitted = await websocket_manager.submit_trade(position_data.trader_id, position_data.trade_pair, position_data.order_type, position_data.leverage)
        if not trade_submitted:
            logger.error("Failed to submit trade")
            raise HTTPException(status_code=500, detail="Failed to submit trade")

        logger.info("Trade submitted successfully")

        # Create the position with the first received price
        await create_position(db, position_data, entry_price=first_price, operation_type="initiate")
        logger.info(f"Position initiated successfully with entry price {first_price}")
        return TradeResponse(message="Position initiated successfully")

    except Exception as e:
        logger.error(f"Error initiating position: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/adjust-position/", response_model=TradeResponse)
async def adjust_position_endpoint(position_data: PositionCreate, db: AsyncSession = Depends(get_db)):
    logger.info(f"Adjusting position for trader_id={position_data.trader_id} and trade_pair={position_data.trade_pair}")

    # Get the latest position record for the given trader and trade pair
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

        # Create a new position record with updated values
        await create_position(
            db, position_data, entry_price=latest_position.entry_price, operation_type="adjust",
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

@router.post("/close-position/", response_model=TradeResponse)
async def close_position(profit_loss_request: ProfitLossRequest, db: AsyncSession = Depends(get_db)):
    logger.info(f"Closing position for trader_id={profit_loss_request.trader_id} and trade_pair={profit_loss_request.trade_pair}")

    position = await get_open_position(db, profit_loss_request.trader_id, profit_loss_request.trade_pair)
    if not position:
        logger.error("No open position found for this trade pair and trader")
        raise HTTPException(status_code=404, detail="No open position found for this trade pair and trader")

    try:
        # Submit the FLAT signal to close the position
        close_submitted = await websocket_manager.submit_trade(profit_loss_request.trader_id, profit_loss_request.trade_pair, "FLAT", 1)
        if not close_submitted:
            logger.error("Failed to submit close signal")
            raise HTTPException(status_code=500, detail="Failed to submit close signal")

        logger.info("Close signal submitted successfully")

        # Set close_time and close_price
        close_time = datetime.utcnow()

        # Connect and subscribe to the WebSocket
        logger.info(f"Connecting to WebSocket for asset type {position.asset_type}")
        websocket = await websocket_manager.connect(position.asset_type)
        subscription_response = await websocket_manager.subscribe(position.trade_pair)
        logger.info(f"Subscription response: {subscription_response}")

        # Wait for the first price to be received
        close_price = await websocket_manager.listen_for_price()
        if close_price is None:
            logger.error("Failed to fetch current price for the trade pair")
            raise HTTPException(status_code=500, detail="Failed to fetch current price for the trade pair")
        
        logger.info(f"Close price for {position.trade_pair} is {close_price}")

        # Calculate profit/loss
        profit_loss = calculate_profit_loss(position.entry_price, close_price, position.cumulative_leverage, position.order_type, position.asset_type)

        # Create a new position record to mark the position as closed
        close_position_data = PositionCreate(
            trader_id=profit_loss_request.trader_id,
            trade_pair=profit_loss_request.trade_pair,
            leverage=1,
            asset_type=profit_loss_request.asset_type,
            stop_loss=0,  # Set stop_loss to a default value
            take_profit=0,  # Set take_profit to a default value
            order_type="FLAT"
        )

        # Create the close position with the calculated profit/loss
        await create_position(db, close_position_data, entry_price=position.entry_price, operation_type="close",
                              cumulative_leverage=position.cumulative_leverage,
                              cumulative_stop_loss=0,  # Set to 0 when closing
                              cumulative_take_profit=0,  # Set to 0 when closing
                              cumulative_order_type=position.cumulative_order_type,
                              close_time=close_time, close_price=close_price, profit_loss=profit_loss)
        
        logger.info(f"Position closed successfully with close price {close_price} and profit/loss {profit_loss}")
        return TradeResponse(message="Position closed successfully")

    except Exception as e:
        logger.error(f"Error closing position: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/profit-loss/", response_model=dict)
async def get_profit_loss(profit_loss_request: ProfitLossRequest, db: AsyncSession = Depends(get_db)):
    trader_id = profit_loss_request.trader_id
    trade_pair = profit_loss_request.trade_pair

    logger.info(f"Calculating profit/loss for trader_id={trader_id} and trade_pair={trade_pair}")

    latest_position = await get_latest_position(db, trader_id, trade_pair)
    if not latest_position:
        logger.error("No open position found for this trade pair and trader")
        raise HTTPException(status_code=404, detail="No open position found for this trade pair and trader")

    try:
        # Connect and subscribe to the WebSocket
        websocket = await websocket_manager.connect(latest_position.asset_type)
        subscription_response = await websocket_manager.subscribe(trade_pair)
        logger.info(f"Subscription response: {subscription_response}")

        # Wait for the first price to be received
        first_price = await websocket_manager.listen_for_price()
        if first_price is None:
            logger.error("Failed to fetch current price for the trade pair")
            raise HTTPException(status_code=500, detail="Failed to fetch current price for the trade pair")
        
        # Calculate profit/loss based on the first price
        logger.info(f"Entry price: {latest_position.entry_price}, Current price: {first_price}, Leverage: {latest_position.cumulative_leverage}, Order type: {latest_position.cumulative_order_type}")
        profit_loss = calculate_profit_loss(latest_position.entry_price, first_price, latest_position.cumulative_leverage, latest_position.cumulative_order_type, latest_position.asset_type)

        return {"profit_loss": profit_loss}

    except Exception as e:
        logger.error(f"Error calculating profit/loss: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/positions/{trader_id}", response_model=list[PositionSchema])
async def get_positions(trader_id: int, db: AsyncSession = Depends(get_db)):
    logger.info(f"Fetching all positions for trader_id={trader_id}")

    result = await db.execute(select(Position).where(Position.trader_id == trader_id))
    positions = result.scalars().all()
    return positions
