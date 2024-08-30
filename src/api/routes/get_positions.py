from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.database import get_db
from src.models.transaction import Transaction
from src.schemas.transaction import Transaction as TransactionSchema
from src.services.trade_service import calculate_profit_loss
from src.utils.logging import setup_logging
from src.utils.websocket_manager import websocket_manager

logger = setup_logging()
router = APIRouter()


@router.get("/positions/", response_model=List[TransactionSchema])
@router.get("/positions/{trader_id}", response_model=List[TransactionSchema])
async def get_positions(
        trader_id: Optional[int] = None,
        db: AsyncSession = Depends(get_db),
        trade_pair: Optional[str] = None,
        only_open: Optional[bool] = False,
        status: Optional[str] = None
):
    logger.info(f"Fetching positions for trader_id={trader_id}, trade_pair={trade_pair}, status={status}")

    if status and status.strip().upper() not in ["OPEN", "PENDING", "CLOSED"]:
        logger.error("A status can only be open, pending and closed")
        raise HTTPException(status_code=400, detail="A status can only be open, pending and closed!")


    # Base query
    query = select(Transaction)
    if trader_id:
        query = query.where(Transaction.trader_id == trader_id)

    # Apply trade_pair filter if specified
    if trade_pair:
        query = query.where(Transaction.trade_pair == trade_pair)

    if status:
        status = status.strip().upper()
        query = query.where(Transaction.status == status)
    elif only_open:
        query = query.where(Transaction.status == "OPEN")
    # Main query to fetch all transactions
    query = query.order_by(Transaction.position_id, Transaction.trade_order)
    result = await db.execute(query)
    positions = result.scalars().all()
    for position in positions:
        if position.status != "OPEN":
            logger.info("Position is Closed => Continue")
            continue

        logger.info("Position is Open!")
        # Connect and subscribe to the WebSocket
        websocket = await websocket_manager.connect(position.asset_type)
        subscription_response = await websocket_manager.subscribe(position.trade_pair)
        logger.info(f"Subscription response: {subscription_response}")

        # Wait for the first price to be received
        first_price = await websocket_manager.listen_for_initial_price()
        if first_price is None:
            logger.error("Failed to fetch current price for the trade pair")
            raise HTTPException(status_code=500, detail="Failed to fetch current price for the trade pair")
        profit_loss = calculate_profit_loss(position.entry_price, first_price,
                                            position.cumulative_leverage, position.cumulative_order_type,
                                            position.asset_type)
        position.profit_loss = profit_loss

    return positions
