from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes.websocket import router as prices_websocket
from src.utils.websocket_manager import forex_websocket_manager, crypto_websocket_manager, stocks_websocket_manager

app = FastAPI()

# Include routes
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
    print("Starting to Listen for Multiple Prices...")
    print()
    # asyncio.create_task(stocks_websocket_manager.listen_for_prices_multiple())
    # asyncio.create_task(forex_websocket_manager.listen_for_prices_multiple())
    # asyncio.create_task(crypto_websocket_manager.listen_for_prices_multiple())
