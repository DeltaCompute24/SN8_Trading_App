import asyncio
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import Session
from sqlalchemy.sql import and_

from src.core.celery_app import celery_app
from src.database_tasks import TaskSessionLocal_
from src.models.transaction import Transaction
from src.services.trade_service import calculate_profit_loss, close_transaction
from src.utils.websocket_manager import websocket_manager

logger = logging.getLogger(__name__)


def get_open_position(db: AsyncSession, trader_id: int, trade_pair: str):
    open_transaction = db.scalar(
        select(Transaction).where(
            and_(
                Transaction.trader_id == trader_id,
                Transaction.trade_pair == trade_pair,
                Transaction.status != "CLOSED"
            )
        ).order_by(Transaction.trade_order.desc())
    )
    return open_transaction


@celery_app.task(name='src.tasks.position_monitor_sync.monitor_positions')
def monitor_positions():
    logger.info("Starting monitor_positions task")
    monitor_positions_sync()


def get_monitored_positions():
    try:
        logger.info("Fetching monitored positions from database")
        db: Session = TaskSessionLocal_()
        result = db.execute(select(Transaction))
        positions = result.scalars().all()
        db.close()
        logger.info(f"Retrieved {len(positions)} monitored positions")
        return positions
    except Exception as e:
        logger.error(f"An error occurred while fetching monitored positions: {e}")
        return []


def monitor_positions_sync():
    try:
        logger.info("Starting monitor_positions_sync")
        positions = get_monitored_positions()
        for position in positions:
            logger.info(f"Processing position {position.position_id}")
            monitor_position(position)
        logger.info("Finished monitor_positions_sync")
    except Exception as e:
        logger.error(f"An error occurred in monitor_positions_sync: {e}")


def monitor_position(position):
    try:
        current_price = websocket_manager.current_prices.get(position.trade_pair)
        if current_price:
            logger.error(f"Current Price Found: {current_price}")
            profit_loss = calculate_profit_loss(
                position.entry_price,
                current_price,
                position.cumulative_leverage,
                position.cumulative_order_type,
                position.asset_type
            )
            if should_close_position(profit_loss, position):
                db: Session = TaskSessionLocal_()
                close_position(position, current_price)
                db.close()
        return True
    except Exception as e:
        logger.error(f"An error occurred while monitoring position {position.position_id}: {e}")


def close_position(position, close_price):
    try:
        db: AsyncSession = TaskSessionLocal_()
        open_position = get_open_position(db, position.trader_id, position.trade_pair)

        if open_position:
            close_submitted = websocket_manager.submit_trade(position.trader_id, position.trade_pair, "FLAT", 1)
            if close_submitted:
                asyncio.run(close_transaction(db, position.order_id, close_price))
        db.close()
    except Exception as e:
        logger.error(f"An error occurred while closing position {position.position_id}: {e}")


def should_close_position(profit_loss, position):
    try:
        result = (
                (position.cumulative_order_type == "LONG" and profit_loss >= position.cumulative_take_profit) or
                (position.cumulative_order_type == "LONG" and profit_loss <= position.cumulative_stop_loss) or
                (position.cumulative_order_type == "SHORT" and profit_loss <= position.cumulative_take_profit) or
                (position.cumulative_order_type == "SHORT" and profit_loss >= position.cumulative_stop_loss)
        )
        logger.info(f"Determining whether to close position: {result}")
        return result
    except Exception as e:
        logger.error(f"An error occurred while determining if position should be closed: {e}")
        return False
