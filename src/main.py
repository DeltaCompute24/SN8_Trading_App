import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.sql import text
from src.api.routes.initiate_position import router as initiate_router
from src.api.routes.adjust_position import router as adjust_router
from src.api.routes.close_position import router as close_router
from src.api.routes.profit_loss import router as profit_loss_router
from src.api.routes.get_positions import router as get_positions_router
from src.database import engine, Base, DATABASE_URL
from src.models.transaction import Transaction  # Ensure the models are imported
from src.models.monitored_positions import MonitoredPosition  # Ensure the models are imported

app = FastAPI()

# Include routes
app.include_router(initiate_router, prefix="/trades")
app.include_router(adjust_router, prefix="/trades")
app.include_router(close_router, prefix="/trades")
app.include_router(profit_loss_router, prefix="/trades")
app.include_router(get_positions_router, prefix="/trades")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this to your needs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    # Create the monitoring database if it doesn't exist
    default_db_url = DATABASE_URL.rsplit('/', 1)[0] + "/postgres"
    default_engine = create_async_engine(default_db_url, echo=True)

    async with default_engine.connect() as conn:
        await conn.execute(text("commit"))  # Ensure any previous transaction is closed
        try:
            await conn.execute(text("CREATE DATABASE monitoring"))
            print("Database 'monitoring' created successfully")
        except ProgrammingError as e:
            if "already exists" in str(e):
                print("Database 'monitoring' already exists")
            else:
                raise e

    await default_engine.dispose()

    # Create the tables in the monitoring database
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
