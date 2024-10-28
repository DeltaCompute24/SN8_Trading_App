from sqlalchemy.ext.asyncio import AsyncSession
import asyncio
from sqlalchemy.future import select
from src.database import get_db
from src.models import Challenge

# Function to get all hot keys from the Challenge model
async def get_all_hot_keys(db: AsyncSession):
    async with db.begin():  # Ensure the session starts and finishes cleanly
        result = await db.execute(select(Challenge.hot_key))
        hot_keys = result.fetchall()  # Fetch all hot keys

        # Filter out None values and remove duplicates using a set
        unique_hot_keys = {hot_key[0] for hot_key in hot_keys if hot_key[0] is not None}

        return list(hot_keys)

# Main function to run the async task
async def main():
    # Get the db session from the async generator
    async for db in get_db():
        # Fetch and print the list of unique hot keys
        hot_keys = await get_all_hot_keys(db)
        print(hot_keys)

# Run the async main function
if __name__ == "__main__":
    asyncio.run(main())
