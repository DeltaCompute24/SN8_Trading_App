from enum import Enum

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.sql import text

from src.api.routes.adjust_position import router as adjust_router
from src.api.routes.close_position import router as close_router
from src.api.routes.favorite_trade_pairs import router as favorite_pairs_router
from src.api.routes.generate_pdf import router as generate_certificate
from src.api.routes.get_positions import router as get_positions_router
from src.api.routes.initiate_position import router as initiate_router
from src.api.routes.payments import router as payment_routers
from src.api.routes.payout import router as payout
from src.api.routes.profit_loss import router as profit_loss_router
from src.api.routes.referral_code import router as referral_code_router
from src.api.routes.tournaments import router as tournament_routers
from src.api.routes.users_balance import router as balance_routers
from src.database import engine, Base, DATABASE_URL
from src.services.user_service import populate_ambassadors

app = FastAPI()


# tag enums
class Tags(Enum):
    positions = "Positions"
    payments = "Payments"
    tournaments = "Tournaments"
    payouts = "Payouts"
    certificate = "Generate Certificate"
    balances = "Users Balance"
    codes = "Referral Codes"
    fav_pairs = "Favorite Pairs"


# Include routes
app.include_router(initiate_router, prefix="/trades", tags=[Tags.positions])
app.include_router(adjust_router, prefix="/trades", tags=[Tags.positions])
app.include_router(close_router, prefix="/trades", tags=[Tags.positions])
app.include_router(profit_loss_router, prefix="/trades", tags=[Tags.positions])
app.include_router(get_positions_router, prefix="/trades", tags=[Tags.positions])

app.include_router(payment_routers, prefix="/payments", tags=[Tags.payments])

app.include_router(tournament_routers, prefix="/tournaments", tags=[Tags.tournaments])

app.include_router(payout, prefix="/payout", tags=[Tags.payouts])

app.include_router(generate_certificate, prefix="/generate-certificate", tags=[Tags.certificate])

app.include_router(balance_routers, prefix="/users-balance", tags=[Tags.balances])

app.include_router(referral_code_router, prefix="/referral-code", tags=[Tags.codes])

app.include_router(favorite_pairs_router, prefix="/favorite-pairs", tags=[Tags.fav_pairs])

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
