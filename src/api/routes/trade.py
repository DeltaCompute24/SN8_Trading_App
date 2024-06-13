from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_db
from src.schemas.position import PositionCreate, TradeResponse
from src.services.trade_service import create_position, get_open_position, calculate_profit_loss, adjust_position
from src.utils.logging import setup_logging
from src.utils.websocket_manager import websocket_manager

logger = setup_logging()
router = APIRouter()

@router.post("/initiate-trade/", response_model=TradeResponse)
async def initiate_trade(position_data: PositionCreate, db: AsyncSession = Depends(get_db)):
    logger.info(f"Initiating trade for trader_id={position_data.trader_id} and trade_pair={position_data.trade_pair}")

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
        
        logger.info(f"First price for {position_data.trade_pair} is {first_price}")

        # Submit the trade and wait for confirmation
        trade_submitted = await websocket_manager.submit_trade(position_data.trader_id, position_data.trade_pair, position_data.order_type, position_data.leverage)
        if not trade_submitted:
            logger.error("Failed to submit trade")
            raise HTTPException(status_code=500, detail="Failed to submit trade")

        logger.info("Trade submitted successfully")

        # Create the position with the first received price
        await create_position(db, position_data, entry_price=first_price, operation_type="initiate")
        logger.info("Trade initiated successfully")
        return TradeResponse(message="Trade initiated successfully")

    except Exception as e:
        logger.error(f"Error initiating trade: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/adjust-trade/{trader_id}/{trade_pair}", response_model=TradeResponse)
async def adjust_trade(trader_id: int, trade_pair: str, trade_input: PositionCreate, db: AsyncSession = Depends(get_db)):
    logger.info(f"Adjusting trade for trader_id={trader_id} and trade_pair={trade_pair}")

    position = await adjust_position(
        db,
        trader_id,
        trade_pair,
        trade_input.leverage,
        trade_input.stop_loss,
        trade_input.take_profit,
        trade_input.order_type
    )
    if not position:
        logger.error("No open position found for this trade pair and trader")
        raise HTTPException(status_code=404, detail="No open position found for this trade pair and trader")

    logger.info("Trade adjusted successfully")
    return TradeResponse(message="Trade adjusted successfully")

@router.get("/profit-loss/{trader_id}/{trade_pair}")
async def get_profit_loss(trader_id: int, trade_pair: str, db: AsyncSession = Depends(get_db)):
    logger.info(f"Calculating profit/loss for trader_id={trader_id} and trade_pair={trade_pair}")

    profit_loss = await calculate_profit_loss(db, trader_id, trade_pair)
    if profit_loss is None:
        logger.error("No open position found for this trade pair and trader")
        raise HTTPException(status_code=404, detail="No open position found for this trade pair and trader")

    return {"profit_loss": profit_loss}