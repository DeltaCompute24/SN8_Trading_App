import asyncio

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.sql import text

from src.api.routes.adjust_position import router as adjust_router
from src.api.routes.close_position import router as close_router
from src.api.routes.create_users import router as create_user_router
from src.api.routes.get_positions import router as get_positions_router
from src.api.routes.get_users import router as get_users_router
from src.api.routes.initiate_position import router as initiate_router
from src.api.routes.payments import router as payment_routers
from src.api.routes.profit_loss import router as profit_loss_router
from src.api.routes.send_email import router as send_email
from src.api.routes.users import router as user_routers
from src.api.routes.websocket import router as prices_websocket
from src.api.routes.payout import router as payout
from src.database import engine, Base, DATABASE_URL
from src.services.user_service import populate_ambassadors
from src.utils.websocket_manager import forex_websocket_manager, crypto_websocket_manager

app = FastAPI()

# Include routes
app.include_router(initiate_router, prefix="/trades")
app.include_router(adjust_router, prefix="/trades")
app.include_router(close_router, prefix="/trades")
app.include_router(profit_loss_router, prefix="/trades")
app.include_router(get_positions_router, prefix="/trades")
app.include_router(create_user_router, prefix="/trades")
app.include_router(get_users_router, prefix="/trades")
app.include_router(user_routers, prefix="/users")
app.include_router(payment_routers, prefix="/payments")
app.include_router(send_email, prefix="/send-email")
app.include_router(payout, prefix="/payout")
app.include_router(prices_websocket, prefix="/ws")


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
    print("Starting to listen for prices multiple...")
    print()
    asyncio.create_task(forex_websocket_manager.listen_for_prices_multiple())
    asyncio.create_task(crypto_websocket_manager.listen_for_prices_multiple())
    # Uncomment the following line if you want to use indices_websocket_manager
    # asyncio.create_task(indices_websocket_manager.listen_for_prices_multiple())

    default_db_url = DATABASE_URL.rsplit("/", 1)[0] + "/postgres"
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

    print("Populate Ambassadors dict!")
    populate_ambassadors()
