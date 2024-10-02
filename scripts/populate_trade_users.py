from database_tasks import TaskSessionLocal_
from scripts.populate_transactions import get_user
from src.models.users import Users
from src.services.api_service import ambassadors


def populate_trade_users():
    with TaskSessionLocal_() as db:
        for hot_key, trader_id in ambassadors.items():
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


populate_trade_users()
