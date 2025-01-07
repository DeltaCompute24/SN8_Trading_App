import asyncio
from datetime import datetime

from sqlalchemy.future import select
from sqlalchemy.orm import Session
from sqlalchemy.sql import and_
from sqlalchemy.sql import func

from src.models.transaction import Transaction
from src.models.users import Users
from src.services.api_service import call_main_net, testnet_websocket
from src.services.user_service import get_challenge_for_hotkey
from src.utils.constants import forex_pairs, indices_pairs, crypto_pairs


def convert_timestamp_to_datetime(timestamp_ms):
    timestamp_sec = timestamp_ms / 1000.0
    return datetime.fromtimestamp(timestamp_sec)


def get_position_id_or_trade_order(db, trader_id):
    max_position_id = db.scalar(
        select(func.max(Transaction.position_id)).filter(Transaction.trader_id == trader_id))
    position_id = (max_position_id or 0) + 1
    return position_id, 1


def get_asset_type(trade_pair):
    if trade_pair in crypto_pairs:
        return "crypto"
    if trade_pair in forex_pairs:
        return "forex"
    if trade_pair in indices_pairs:
        return "indices"


def get_open_position(db: Session, trader_id: int, trade_pair: str):
    open_transaction = db.scalar(
        select(Transaction).where(
            and_(
                Transaction.trader_id == trader_id,
                Transaction.trade_pair == trade_pair,
                Transaction.status == "OPEN"
            )
        ).order_by(Transaction.trade_order.desc())
    )
    return open_transaction


def get_uuid_position(db: Session, uuid: str, hot_key: str):
    uuid_transaction = db.scalar(
        select(Transaction).where(
            and_(
                Transaction.uuid == uuid,
                Transaction.hot_key == hot_key,
            )
        ).order_by(Transaction.trade_order.desc())
    )
    return uuid_transaction


def get_user(db: Session, hot_key: str):
    user = db.scalar(
        select(Users).where(
            and_(
                Users.hot_key == hot_key,
            )
        )
    )
    return user


def process_data(db: Session, data, source):
    for hot_key, content in data.items():
        challenge = get_challenge_for_hotkey(hot_key)
        if not challenge:
            continue
        trader_id = challenge.trader_id

        try:
            user = get_user(db, hot_key)
            if not user:
                new_user = Users(
                    trader_id=trader_id,
                    hot_key=hot_key,
                )
                db.add(new_user)
                db.commit()
                db.refresh(new_user)
        except Exception as ex:
            print(f"Error while creating trader_id and hot_key: {hot_key}")

        positions = content["positions"]
        for position in positions:
            try:
                trade_pair = position["trade_pair"][0]
                position_uuid = position["position_uuid"]
                existing_position = get_open_position(db, trader_id, trade_pair)
                if existing_position:
                    continue

                existing_position = get_uuid_position(db, position_uuid, hot_key)
                if existing_position:
                    continue

                open_time = convert_timestamp_to_datetime(position["open_ms"])
                net_leverage = position["net_leverage"]
                avg_entry_price = position["average_entry_price"]
                cumulative_order_type = position["position_type"]
                profit_loss = position["return_at_close"]
                profit_loss_without_fee = position["current_return"]

                orders = position["orders"]
                leverage = orders[0]["leverage"]
                order_type = orders[0]["order_type"]
                entry_price = orders[0]["price"]
                leverages = []
                order_types = []
                prices = []

                for order in orders:
                    leverages.append(order["leverage"])
                    order_types.append(order["order_type"])
                    prices.append(order["price"])

                close_time = None
                close_price = None
                operation_type = "initiate"
                status = "OPEN"
                if position["is_closed_position"] is True:
                    status = "CLOSED"
                    close_time = convert_timestamp_to_datetime(position["close_ms"])
                    close_price = orders[-1]["price"]
                    leverage = orders[-1]["leverage"]
                    order_type = orders[-1]["order_type"]
                    operation_type = "close"

                position_id, trade_order = get_position_id_or_trade_order(db, trader_id)
                asset_type = get_asset_type(trade_pair) or "forex"

                new_transaction = Transaction(
                    trader_id=trader_id,
                    trade_pair=trade_pair,
                    open_time=open_time,
                    entry_price=entry_price,
                    initial_price=entry_price,
                    leverage=leverage,
                    order_type=order_type,
                    asset_type=asset_type,
                    operation_type=operation_type,
                    cumulative_leverage=net_leverage,
                    cumulative_order_type=cumulative_order_type,
                    average_entry_price=avg_entry_price,
                    status=status,
                    old_status="OPEN",
                    profit_loss=((profit_loss * 100) - 100),
                    profit_loss_without_fee=((profit_loss_without_fee * 100) - 100),
                    taoshi_profit_loss=profit_loss,
                    taoshi_profit_loss_without_fee=profit_loss_without_fee,
                    close_time=close_time,
                    close_price=close_price,
                    position_id=position_id,
                    trade_order=trade_order,
                    entry_price_list=prices,
                    leverage_list=leverages,
                    order_type_list=order_types,
                    modified_by="taoshi",
                    uuid=position_uuid,
                    hot_key=hot_key,
                    upward=-1,
                    source=source,
                )
                db.add(new_transaction)
                db.commit()
                db.refresh(new_transaction)

            except Exception as ex:
                print(f"Error while creating position and hot_key: {hot_key} - {position['open_ms']}")


def populate_transactions(db: Session):
    main_net_data = call_main_net()
    test_net_data = testnet_websocket()

    process_data(db, main_net_data, source="main")
    process_data(db, test_net_data, source="test")
