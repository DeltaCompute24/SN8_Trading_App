from scripts.delete_transactins import delete_transactions
from scripts.populate_transactions import populate_transactions
from src.database_tasks import TaskSessionLocal_

delete_transactions()

with TaskSessionLocal_() as _db:
    populate_transactions(_db)
