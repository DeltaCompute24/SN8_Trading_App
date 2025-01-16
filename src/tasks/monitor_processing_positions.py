import asyncio
import logging
from datetime import datetime
from datetime import timedelta

from sqlalchemy import and_, or_
from sqlalchemy.future import select
from sqlalchemy.orm import Session

from src.core.celery_app import celery_app
from src.database_tasks import TaskSessionLocal_
from src.models import Challenge
from src.models.transaction import Transaction, Status
from src.services.email_service import send_mail
from src.services.fee_service import get_taoshi_values
from src.utils.constants import ERROR_QUEUE_NAME
from src.utils.redis_manager import push_to_redis_queue, delete_hash_value
from src.utils.websocket_manager import websocket_manager

logger = logging.getLogger(__name__)


def get_challenge(db: Session, challenge_id: int):
    challenge = db.scalar(
        select(Challenge).where(
            and_(
                Challenge.id == challenge_id,
            )
        )
    )
    return challenge


def send_email_to_user(db, position, _type="OPEN"):
    challenge = get_challenge(db, position.trader_id)
    if not challenge:
        return
    email = challenge.user.email
    if not email:
        return

    send_mail(
        receiver=email,
        subject=f"{_type} Position Failed for {position.trader_id}-{position.trade_pair}.",
        content=f"Dear User, You {_type.lower()}ed a position but its not {_type.lower()}ed successfully due to some technicalities.",
        template_name="EmailTemplate.html",
    )


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
                or_(
                    Transaction.status == Status.processing,
                    Transaction.status == Status.adjust_processing,
                    Transaction.status == Status.close_processing,
                )
            )
        )
        positions = result.scalars().all()
        logger.info(f"Retrieved {len(positions)} processing positions")
        return positions
    except Exception as e:
        push_to_redis_queue(data=f"**Monitor Processing Positions** Database Error - {e}", queue_name=ERROR_QUEUE_NAME)
        logger.error(f"An error occurred while fetching processing positions: {e}")
        return []


def check_initiate_position(db, position, data):
    if position.status != Status.processing:
        return

    # check if its price empty then check its time
    if data["entry_price"] != 0:
        data.update({
            "operation_type": "open",
            "status": "OPEN",
        })
        update_position(db, position, data)
        return

    now = datetime.utcnow() - timedelta(minutes=5)
    if position.open_time < now:
        push_to_redis_queue(
            data=f"**Monitor Processing Positions** => An initiated processing position is not initiated but closed because we "
                 f"are unable to get price from taoshi till 5 minutes => {position.trader_id}-{position.trade_pair}-{position.order_id}",
            queue_name=ERROR_QUEUE_NAME
        )
        asyncio.run(websocket_manager.submit_trade(position.trader_id, position.trade_pair, "FLAT", 1))
        data.update({
            "operation_type": "close",
            "status": "CLOSED",
            "close_price": data["entry_price"],
            "close_time": datetime.utcnow(),
        })
        update_position(db, position, data)
        send_email_to_user(db, position)


def check_adjust_position(db, position, data):
    if position.status != Status.adjust_processing:
        return
    # no need to update entry or initial price
    price = data.pop("entry_price")
    data.pop("initial_price")
    data.pop("max_profit_loss")

    # if you get the price and order was submitted successfully then adjust position
    if price != 0 and position.order_level < data["order_level"]:
        if data["profit_loss"] > position.max_profit_loss:
            data["max_profit_loss"] = data["profit_loss"]
        else:
            data["max_profit_loss"] = position.max_profit_loss
        data.update({
            "operation_type": "adjust",
            "status": "OPEN",
        })
        update_position(db, position, data)
        return

    # close position if it's been 20 minutes and price is still zero
    now = datetime.utcnow() - timedelta(minutes=20)
    if position.adjust_time < now:
        push_to_redis_queue(
            data=f"**Monitor Processing Positions** => An adjusted processing position is not adjusted but closed because we "
                 f"are unable to get price from taoshi till 20 minutes => {position.trader_id}-{position.trade_pair}-{position.order_id}",
            queue_name=ERROR_QUEUE_NAME
        )
        asyncio.run(websocket_manager.submit_trade(position.trader_id, position.trade_pair, "FLAT", 1))
        data.update({
            "operation_type": "close",
            "status": "CLOSED",
            "close_price": price,
            "close_time": datetime.utcnow(),
        })
        update_position(db, position, data)
        send_email_to_user(db, position, _type="ADJUST")


def check_close_position(db, position, data, closed):
    key = f"{position.trade_pair}-{position.trader_id}"
    if position.status != Status.close_processing:
        return
    # no need to update entry or initial price
    price = data.pop("entry_price")
    data.pop("initial_price")
    data.pop("max_profit_loss")
    data.update({
        "operation_type": "close",
        "status": "CLOSED",
        "close_price": price,
    })

    # if you get the price then close in the system as well
    if price != 0 and closed:
        if data["profit_loss"] > position.max_profit_loss:
            data["max_profit_loss"] = data["profit_loss"]
        update_position(db, position, data)
        delete_hash_value(key)
        return

    # close position if it's been 5 minutes and price is still zero
    # close at taoshi as well as in system
    now = datetime.utcnow() - timedelta(minutes=5)
    if position.close_time < now:
        push_to_redis_queue(
            data=f"**Monitor Processing Positions** => A close processing position is not closed with latest price because we "
                 f"are unable to get price from taoshi till 5 minutes => {position.trader_id}-{position.trade_pair}-{position.order_id}",
            queue_name=ERROR_QUEUE_NAME
        )
        asyncio.run(websocket_manager.submit_trade(position.trader_id, position.trade_pair, "FLAT", 1))
        update_position(db, position, data)
        delete_hash_value(key)
        # send_email_to_user(position, _type="CLOSE")


@celery_app.task(name='src.tasks.monitor_processing_positions.processing_positions')
def processing_positions():
    """
    PROCESS the submitted positions to initiate them
    """
    with TaskSessionLocal_() as db:
        for position in get_processing_positions(db):
            # get the price
            price, profit_loss, profit_loss_without_fee, taoshi_profit_loss, taoshi_profit_loss_without_fee, uuid, hot_key, len_order, average_entry_price, closed = get_taoshi_values(
                position.trader_id,
                position.trade_pair,
                challenge=position.source,
                position_uuid=position.uuid,
                closed=True,
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

            check_initiate_position(db, position, data)
            check_adjust_position(db, position, data)
            check_close_position(db, position, data, closed)
