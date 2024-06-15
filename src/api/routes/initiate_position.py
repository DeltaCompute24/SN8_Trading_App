from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_db
from src.schemas.transaction import TransactionCreate, TradeResponse
from src.services.trade_service import create_transaction, get_open_position
from src.utils.logging import setup_logging
from src.utils.websocket_manager import websocket_manager
from datetime import datetime

logger = setup_logging()
router = APIRouter()

@router.post("/initiate-position/", response_model=TradeResponse)
async def initiate_position(position_data: TransactionCreate, db: AsyncSession = Depends(get_db)):
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

        # Create the transaction with the first received price
        await create_transaction(db, position_data, entry_price=first_price, operation_type="initiate")
        logger.info(f"Position initiated successfully with entry price {first_price}")
        return TradeResponse(message="Position initiated successfully")

    except Exception as e:
        logger.error(f"Error initiating position: {e}")
        raise HTTPException(status_code=500, detail=str(e))
