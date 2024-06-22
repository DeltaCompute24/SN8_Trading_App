from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_, func, distinct
from typing import Optional, List
from src.database import get_db
from src.schemas.transaction import Transaction as TransactionSchema
from src.models.transaction import Transaction
from src.utils.logging import setup_logging

logger = setup_logging()
router = APIRouter()


@router.get("/positions/", response_model=List[TransactionSchema])
@router.get("/positions/{trader_id}", response_model=List[TransactionSchema])
async def get_positions(
    trader_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    trade_pair: Optional[str] = None,
    only_open: Optional[bool] = False
):
    logger.info(f"Fetching positions for trader_id={trader_id}, trade_pair={trade_pair}, only_open={only_open}")

    # Base query
    query = select(Transaction)
    if trader_id:
        query = query.where(Transaction.trader_id == trader_id)

    # Apply trade_pair filter if specified
    if trade_pair:
        query = query.where(Transaction.trade_pair == trade_pair)

    if only_open:
        # Subquery to get the latest trade order for each position
        latest_trade_subquery = (
            select(Transaction.position_id, func.max(Transaction.trade_order).label("max_trade_order"))
            .group_by(Transaction.position_id)
            .subquery()
        )

        # Join with the transactions table to get the latest status
        latest_status_subquery = (
            select(Transaction.position_id)
            .join(latest_trade_subquery, 
                  and_(
                      Transaction.position_id == latest_trade_subquery.c.position_id,
                      Transaction.trade_order == latest_trade_subquery.c.max_trade_order
                  ))
            .where(Transaction.status != "CLOSED")
            .distinct()
        )

        # Main query to fetch all orders for positions that are not closed
        query = (
            select(Transaction)
            .where(
                Transaction.position_id.in_(latest_status_subquery)
            )
            .order_by(Transaction.position_id, Transaction.trade_order)
        )
    else:
        # Main query to fetch all transactions
        query = query.order_by(Transaction.position_id, Transaction.trade_order)

    result = await db.execute(query)
    positions = result.scalars().all()

    return positions
