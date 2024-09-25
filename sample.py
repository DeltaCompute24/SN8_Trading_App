# import json
# from datetime import datetime
#
# from fastapi import Depends, HTTPException
# from sqlalchemy import text
# from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy.future import select
#
# from src.database import get_db
# from src.models.transaction import Transaction
# from src.schemas.transaction import Transaction as TransactionSchema
#
#
# class CustomJSONEncoder(json.JSONEncoder):
#     def default(self, obj):
#         if isinstance(obj, datetime):
#             return obj.isoformat()  # Convert datetime to ISO 8601 string
#         return super().default(obj)
#
#
# def delete_objects(db: AsyncSession = Depends(get_db)):
#     # Step 1: Fetch the objects based on a condition
#     query = select(Transaction).where(Transaction.status == "CLOSED")  # Replace condition here
#     result = db.execute(query)
#     objects_to_delete = result.scalars().all()
#
#     if not objects_to_delete:
#         raise HTTPException(status_code=404, detail="No objects found to delete")
#
#     # Step 2: Convert objects to JSON format
#     objects_json = [TransactionSchema.from_orm(obj).dict() for obj in objects_to_delete]
#
#     # Step 3: Backup JSON (store in file, or other table)
#     with open("backup_objects.json", "w") as backup_file:
#         json.dump(objects_json, backup_file, cls=CustomJSONEncoder)
#         # json.dump(objects_json, backup_file)
#
#     # Optional: Log backup details to another table in the database if needed
#
#     # Step 4: Delete objects from the database
#     for obj in objects_to_delete:
#         position_id = obj.position_id
#         db.delete(obj)
#         db.execute(
#             text("DELETE FROM monitored_positions WHERE position_id = :position_id"),
#             {"position_id": position_id}
#         )
#
#     db.commit()
#
#     return {"detail": "Objects deleted successfully", "backup": objects_json}
from datetime import datetime

from sqlalchemy.future import select
from sqlalchemy.orm import Session
from sqlalchemy.sql import and_
from sqlalchemy.sql import func

from database_tasks import TaskSessionLocal_
from services.trade_service import get_latest_position
from src.models.transaction import Transaction
from src.models.users import Users
from src.services.api_service import call_main_net, ambassadors
from src.validations.position import forex_polygon_pairs, indices_pairs, crypto_polygon_pairs


def convert_timestamp_to_datetime(timestamp_ms):
    timestamp_sec = timestamp_ms / 1000.0
    return datetime.fromtimestamp(timestamp_sec)


def get_position_id_or_trade_order(db, trader_id):
    max_position_id = db.scalar(
        select(func.max(Transaction.position_id)).filter(Transaction.trader_id == trader_id))
    position_id = (max_position_id or 0) + 1
    return position_id, 1


def get_asset_type(trade_pair):
    if trade_pair in crypto_polygon_pairs:
        return "crypto"
    if trade_pair in forex_polygon_pairs:
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

def get_user(db: Session, hot_key: str):
    user = db.scalar(
        select(Users).where(
            and_(
                Users.hot_key == hot_key,
            )
        )
    )
    return user


def populate_transactions(db: Session):
    data = call_main_net()
    if not data:
        return

    _id = 110001

    for hot_key, content in data.items():
        trader_id = ambassadors.get(hot_key, _id)
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
                if position["is_closed_position"] is True:
                    continue

                trade_pair = position["trade_pair"][0]
                existing_position = get_open_position(db, trader_id, trade_pair)
                if existing_position:
                    continue
                status = "OPEN"
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
                    operation_type="initiate",
                    cumulative_leverage=net_leverage,
                    cumulative_order_type=cumulative_order_type,
                    average_entry_price=avg_entry_price,
                    status=status,
                    old_status=status,
                    profit_loss=profit_loss,
                    profit_loss_without_fee=profit_loss_without_fee,
                    position_id=position_id,
                    trade_order=trade_order,
                    entry_price_list=prices,
                    leverage_list=leverages,
                    order_type_list=order_types,
                    modified_by=str(trader_id),
                )
                db.add(new_transaction)
                db.commit()
                db.refresh(new_transaction)

            except Exception as ex:
                print(f"Error while creating position and hot_key: {hot_key} - {position['open_ms']}")
        _id += 1


with TaskSessionLocal_() as _db:
    populate_transactions(_db)
