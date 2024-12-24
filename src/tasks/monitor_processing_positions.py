import asyncio
import logging
from datetime import datetime
from datetime import timedelta

from sqlalchemy.future import select
from sqlalchemy.orm import Session
from sqlalchemy.sql import and_

from src.core.celery_app import celery_app
from src.database_tasks import TaskSessionLocal_
from src.models.transaction import Transaction, Status
from src.services.fee_service import get_taoshi_values
from src.utils.constants import ERROR_QUEUE_NAME
from src.utils.redis_manager import push_to_redis_queue
from src.utils.websocket_manager import websocket_manager

logger = logging.getLogger(__name__)


def update_position(db: Session, position, data):
    logger.info(f"Updating processing position: {position.trader_id} - {position.hot_key}")

    for key, value in data.items():
        setattr(position, key, value)

    db.commit()
    db.refresh(position)


def get_processing_positions(db):
    """
    fetch PROCESSING positions from database
    """
    try:
        logger.info("Fetching processing positions from database")
        result = db.execute(
            select(Transaction).where(
                and_(
                    Transaction.status == Status.processing,
                )
            )
        )
        positions = result.scalars().all()
        logger.info(f"Retrieved {len(positions)} processing positions")
        return positions
    except Exception as e:
        push_to_redis_queue(data=f"**Monitor Positions** Database Error - {e}", queue_name=ERROR_QUEUE_NAME)
        logger.error(f"An error occurred while fetching processing positions: {e}")
        return []


@celery_app.task(name='src.tasks.monitor_processing_positions.processing_positions')
def processing_positions():
    """
    PROCESS the submitted positions to initiate them
    """
    with TaskSessionLocal_() as db:
        for position in get_processing_positions(db):
            # get the price
            price, profit_loss, profit_loss_without_fee, taoshi_profit_loss, taoshi_profit_loss_without_fee, uuid, hot_key, len_order, average_entry_price = get_taoshi_values(
                position.trader_id,
                position.trade_pair,
                challenge=position.source,
            )
            data = {
                "entry_price": price,
                "initial_price": price,
                "old_status": position.status,
                "average_entry_price": average_entry_price,
                "profit_loss": profit_loss,
                "profit_loss_without_fee": profit_loss_without_fee,
                "taoshi_profit_loss_without_fee": taoshi_profit_loss_without_fee,
                "taoshi_profit_loss": taoshi_profit_loss,
                "uuid": uuid,
                "hot_key": hot_key,
                "order_level": len_order,
                "max_profit_loss": profit_loss,
            }
            # check if its price empty then check its time
            now = datetime.utcnow() - timedelta(minutes=5)
            if price == 0 and position.open_time < now:
                asyncio.run(websocket_manager.submit_trade(position.trader_id, position.trade_pair, "FLAT", 1))
                data.update({
                    "operation_type": "close",
                    "status": "CLOSED",
                })
                update_position(db, position, data)
                continue
            data.update({
                "operation_type": "open",
                "status": "OPEN",
            })
            update_position(db, position, data)
