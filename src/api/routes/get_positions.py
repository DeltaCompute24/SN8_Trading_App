from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.sql import and_ , or_

from src.database import get_db
from src.models.transaction import Transaction, Status
from src.schemas.transaction import Transaction as TransactionSchema
from src.services.api_service import call_main_net, testnet_websocket
from src.services.user_service import get_challenge, get_hot_key
from src.utils.logging import setup_logging

logger = setup_logging()
router = APIRouter()


@router.get("/positions/", response_model=List[TransactionSchema])
@router.get("/positions/{trader_id}", response_model=List[TransactionSchema])
async def get_positions(
        trader_id: Optional[int] = None,
        db: AsyncSession = Depends(get_db),
        trade_pair: Optional[str] = "",
        only_open: Optional[bool] = False,
        status: Optional[str] = "",
):
    logger.info(f"Fetching positions for trader_id={trader_id}, trade_pair={trade_pair}, status={status}")

    status = status.strip().upper()
    if status and status not in [Status.open, Status.pending, Status.close, Status.processing, Status.adjust_processing,
                                 Status.close_processing]:
        logger.error("A status can only be open, pending and closed, processing , adjust_processing")
        raise HTTPException(status_code=400, detail="A status can only be open, pending, closed, processing , adjust_processing")

    source = get_challenge(trader_id, source=True)

    # Base query
    query = select(Transaction)
    if trader_id:
        query = query.where(and_(Transaction.trader_id == trader_id, Transaction.source == source))
    if trade_pair:
        query = query.where(and_(Transaction.trade_pair == trade_pair))
    if status:
        if status == Status.open:
            query = query.where(or_(
                Transaction.status == Status.open,
                Transaction.status == Status.processing,
                Transaction.status == Status.adjust_processing
            ))
        else:
            query = query.where(and_(Transaction.status == status))
    elif only_open:
        query = query.where(and_(Transaction.status == "OPEN"))

    # Main query to fetch all transactions
    query.order_by(desc(Transaction.open_time), desc(Transaction.close_time))
    # query = query.order_by(Transaction.position_id, Transaction.trade_order)
    result = await db.execute(query)
    positions = result.scalars().all()

    if status in ["PENDING", "CLOSED"]:
        for position in positions:
            position.fee = abs((position.profit_loss_without_fee or 0.0) - (position.profit_loss or 0.0))
        return positions

    if source == "main":
        data = call_main_net()
    elif source == "test":
        data = testnet_websocket()
    else:
        test_net = testnet_websocket()
        data = call_main_net() | test_net

    for position in positions:
        position.fee = abs((position.profit_loss_without_fee or 0.0) - (position.profit_loss or 0.0))
        if position.status != "OPEN":
            continue

        hot_key = get_hot_key(position.trader_id)
        content = data.get(hot_key)
        if not content:
            continue

        for pos in content["positions"]:
            if pos["position_uuid"] != position.uuid:
                continue

            price, taoshi_profit_loss, taoshi_profit_loss_without_fee = pos["orders"][-1]["price"], pos[
                "return_at_close"], pos["current_return"]
            position.profit_loss = (taoshi_profit_loss * 100) - 100
            position.profit_loss_without_fee = (taoshi_profit_loss_without_fee * 100) - 100
            position.fee = abs(position.profit_loss_without_fee - position.profit_loss)
            break

    return positions
