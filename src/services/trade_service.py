from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import Session
from sqlalchemy.sql import and_, text
from sqlalchemy.sql import func

from src.models.transaction import Transaction
from src.schemas.monitored_position import MonitoredPositionCreate
from src.schemas.transaction import TransactionCreate
from src.services.fee_service import get_assets_fee


async def create_transaction(db: AsyncSession, transaction_data: TransactionCreate, entry_price: float,
                             operation_type: str, initial_price: float, position_id: int = None,
                             cumulative_leverage: float = None, cumulative_stop_loss: float = None,
                             cumulative_take_profit: float = None,
                             order_type: str = None, cumulative_order_type: str = None, status: str = "OPEN", old_status: str = "OPEN",
                             close_time: datetime = None, close_price: float = None, profit_loss: float = 0,
                             upward: float = -1, order_level: int = 0, modified_by: str = None,
                             average_entry_price: float = None, entry_price_list: list = None,
                             leverage_list: list = None, order_type_list: list = None, max_profit_loss: float = 0.0,
                             profit_loss_without_fee: float = 0.0, taoshi_profit_loss: float = 0.0,
                             taoshi_profit_loss_without_fee: float = 0.0, uuid: str = None, hot_key: str = None,
                             source: str = ""):
    if operation_type == "initiate":
        max_position_id = await db.scalar(
            select(func.max(Transaction.position_id)).filter(Transaction.trader_id == transaction_data.trader_id))
        position_id = (max_position_id or 0) + 1
        trade_order = 1
        cumulative_leverage = transaction_data.leverage
        cumulative_stop_loss = transaction_data.stop_loss
        cumulative_take_profit = transaction_data.take_profit
        cumulative_order_type = order_type
    else:
        max_trade_order = await db.scalar(
            select(func.max(Transaction.trade_order)).filter(Transaction.position_id == position_id))
        trade_order = (max_trade_order or 0) + 1

    new_transaction = Transaction(
        trader_id=transaction_data.trader_id,
        trade_pair=transaction_data.trade_pair,
        open_time=datetime.utcnow(),
        entry_price=entry_price,
        initial_price=initial_price,
        leverage=transaction_data.leverage,
        stop_loss=transaction_data.stop_loss,
        take_profit=transaction_data.take_profit,
        order_type=order_type,
        asset_type=transaction_data.asset_type,
        operation_type=operation_type,
        cumulative_leverage=cumulative_leverage,
        cumulative_stop_loss=cumulative_stop_loss,
        cumulative_take_profit=cumulative_take_profit,
        cumulative_order_type=cumulative_order_type,
        average_entry_price=average_entry_price,
        status=status,
        old_status=old_status,
        close_time=close_time,
        close_price=close_price,
        profit_loss=profit_loss,
        max_profit_loss=max_profit_loss,
        profit_loss_without_fee=profit_loss_without_fee,
        position_id=position_id,
        trade_order=trade_order,
        upward=upward,
        order_level=order_level,
        entry_price_list=entry_price_list,
        leverage_list=leverage_list,
        order_type_list=order_type_list,
        modified_by=modified_by,
        taoshi_profit_loss=taoshi_profit_loss,
        taoshi_profit_loss_without_fee=taoshi_profit_loss_without_fee,
        uuid=uuid,
        hot_key=hot_key,
        source=source,
    )
    db.add(new_transaction)
    await db.commit()
    await db.refresh(new_transaction)
    return new_transaction


async def close_transaction(db: AsyncSession, order_id, trader_id, close_price: float = None,
                            profit_loss: float = None, old_status: str = "", order_level: int = 0,
                            profit_loss_without_fee: float = 0.0, taoshi_profit_loss: float = 0.0,
                            taoshi_profit_loss_without_fee: float = 0.0, average_entry_price: float = 0.0):
    close_time = datetime.utcnow()
    statement = text("""
            UPDATE transactions
            SET operation_type = :operation_type, 
                status = :status, 
                old_status = :old_status,
                close_time = :close_time, 
                close_price = :close_price,
                profit_loss = :profit_loss,
                leverage = :leverage,
                stop_loss = :stop_loss,
                take_profit = :take_profit,
                order_type = :order_type,
                modified_by = :modified_by,
                order_level = :order_level,
                profit_loss_without_fee = :profit_loss_without_fee,
                taoshi_profit_loss = :taoshi_profit_loss,
                taoshi_profit_loss_without_fee = :taoshi_profit_loss_without_fee,
                average_entry_price = :average_entry_price
            WHERE order_id = :order_id
        """)

    await db.execute(
        statement,
        {
            "operation_type": "close",
            "status": "CLOSED",
            "old_status": old_status,
            "close_time": close_time,
            "close_price": close_price,
            "profit_loss": profit_loss,
            "leverage": 1,
            "stop_loss": None,
            "take_profit": None,
            "order_type": "FLAT",
            "order_id": order_id,
            "modified_by": str(trader_id),
            "order_level": order_level,
            "profit_loss_without_fee": profit_loss_without_fee,
            "taoshi_profit_loss": taoshi_profit_loss,
            "taoshi_profit_loss_without_fee": taoshi_profit_loss_without_fee,
            "average_entry_price": average_entry_price,
        }
    )
    await db.commit()


async def update_monitored_positions(db: AsyncSession, position_data: MonitoredPositionCreate):
    await db.execute(
        text("""
        INSERT INTO monitored_positions (
            position_id, order_id, trader_id, trade_pair, cumulative_leverage, cumulative_order_type, 
            cumulative_stop_loss, cumulative_take_profit, asset_type, entry_price
        ) VALUES (
            :position_id, :order_id, :trader_id, :trade_pair, :cumulative_leverage, :cumulative_order_type, 
            :cumulative_stop_loss, :cumulative_take_profit, :asset_type, :entry_price
        ) ON CONFLICT (position_id, order_id) DO UPDATE SET
            cumulative_leverage = EXCLUDED.cumulative_leverage,
            cumulative_order_type = EXCLUDED.cumulative_order_type,
            cumulative_stop_loss = EXCLUDED.cumulative_stop_loss,
            cumulative_take_profit = EXCLUDED.cumulative_take_profit,
            asset_type = EXCLUDED.asset_type,
            entry_price = EXCLUDED.entry_price
        """),
        {
            "position_id": position_data.position_id,
            "order_id": position_data.order_id,
            "trader_id": position_data.trader_id,
            "trade_pair": position_data.trade_pair,
            "cumulative_leverage": position_data.cumulative_leverage,
            "cumulative_order_type": position_data.cumulative_order_type,
            "cumulative_stop_loss": position_data.cumulative_stop_loss,
            "cumulative_take_profit": position_data.cumulative_take_profit,
            "asset_type": position_data.asset_type,
            "entry_price": position_data.entry_price
        }
    )
    await db.commit()


async def get_open_position(db: AsyncSession, trader_id: int, trade_pair: str):
    open_transaction = await db.scalar(
        select(Transaction).where(
            and_(
                Transaction.trader_id == trader_id,
                Transaction.trade_pair == trade_pair,
                Transaction.status == "OPEN"
            )
        ).order_by(Transaction.trade_order.desc())
    )
    return open_transaction


async def get_latest_position(db: AsyncSession, trader_id: int, trade_pair: str) -> Transaction:
    latest_transaction = await db.scalar(
        select(Transaction).where(
            and_(
                Transaction.trader_id == trader_id,
                Transaction.trade_pair == trade_pair,
                Transaction.status != "CLOSED"
            )
        ).order_by(Transaction.trade_order.desc())
    )
    return latest_transaction


def get_user_position(db: Session, trader_id: int):
    open_transaction = db.scalar(
        select(Transaction).where(
            and_(
                Transaction.trader_id == trader_id,
                Transaction.status != "CLOSED"
            )
        ).order_by(Transaction.trade_order.desc())
    )
    return open_transaction


def calculate_fee(leverage: float, asset_type: str) -> float:
    return get_assets_fee(asset_type) * leverage


def calculate_profit_loss(position, current_price: float) -> float:
    prices = position.entry_price_list or []
    leverages = position.leverage_list or []
    order_types = position.order_type_list or []
    asset_type = position.asset_type

    # broker fee or commission
    fee = calculate_fee(position, asset_type)
    returns = 0.0

    for entry_price, leverage, order_type in zip(prices, leverages, order_types):
        # if long which means user bet that the price will increase i.e. current_price > entry_price => it's a profit
        if order_type == "LONG":
            price_difference = (current_price - entry_price)
        # if long which means user bet that the price will increase i.e. current_price > entry_price => it's a profit
        elif order_type == "SHORT":
            price_difference = (entry_price - current_price)
        else:
            price_difference = 0.00

        profit_loss_percent = ((price_difference / entry_price) * leverage) * 100
        returns += profit_loss_percent

    return returns - fee


def calculate_unrealized_pnl(current_price, position):
    if position.entry_price == 0 or position.average_entry_price is None:
        return 1

    gain = (
            (current_price - position.average_entry_price)
            * position.cumulative_leverage
            / position.entry_price
    )
    # Check if liquidated
    if gain <= -1.0:
        return 0
    net_return = 1 + gain
    return net_return


def calculate_return_with_fees(current_return_no_fees, position):
    fee = calculate_fee(position, asset_type=position.asset_type)
    return current_return_no_fees * fee


def get_open_position_return_with_fees(realtime_price, position):
    current_return = calculate_unrealized_pnl(realtime_price, position)
    return calculate_return_with_fees(current_return, position)
