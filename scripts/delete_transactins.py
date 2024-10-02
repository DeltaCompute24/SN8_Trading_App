from sqlalchemy import text

from src.database_tasks import TaskSessionLocal_
from src.models.transaction import Transaction


def delete_transactions():
    with TaskSessionLocal_() as db:
        # Step 1: Fetch the objects based on a condition
        transactions = db.query(Transaction).all()

        # Step 4: Delete objects from the database
        for obj in transactions:
            position_id = obj.position_id
            db.delete(obj)
            db.execute(
                text("DELETE FROM monitored_positions WHERE position_id = :position_id"),
                {"position_id": position_id}
            )

        db.commit()

        return {"detail": "Objects deleted successfully"}


delete_transactions()
