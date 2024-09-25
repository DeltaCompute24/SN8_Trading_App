from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.database import get_db
from src.models.transaction import Transaction
from src.schemas.transaction import Transaction as TransactionSchema
from src.services.api_service import get_profit_and_current_price
from src.utils.logging import setup_logging

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

    if trade_pair:
        query = query.where(Transaction.trade_pair == trade_pair)
    if status:
        status = status.strip().upper()
        query = query.where(Transaction.status == status)
    elif only_open:
        query = query.where(Transaction.status == "OPEN")

    # Main query to fetch all transactions
    query.order_by(desc(Transaction.open_time), desc(Transaction.close_time))
    # query = query.order_by(Transaction.position_id, Transaction.trade_order)
    result = await db.execute(query)
    positions = result.scalars().all()

    for position in positions:
        position.fee = abs((position.profit_loss_with_fee or 0.0) - (position.profit_loss or 0.0))
        if position.status != "OPEN":
            logger.info("Position is Closed => Continue")
            continue

        logger.info("Position is Open!")
        current_price, taoshi_profit_loss, taoshi_profit_loss_with_fee = get_profit_and_current_price(
            position.trader_id, position.trade_pair)
        if taoshi_profit_loss == 0:
            continue
        profit_loss = (taoshi_profit_loss * 100) - 100
        profit_loss_with_fee = (taoshi_profit_loss_with_fee * 100) - 100
        position.profit_loss = profit_loss or position.profit_loss
        position.profit_loss_with_fee = profit_loss_with_fee or position.profit_loss_with_fee
        position.fee = abs(profit_loss_with_fee - profit_loss)

    return positions
