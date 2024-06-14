import uvicorn
from fastapi import FastAPI
from src.api.routes.position import router as trade_router
from src.database import engine
from src.models.base import Base

app = FastAPI()

# Include routes
app.include_router(trade_router, prefix="/trades")

@app.on_event("startup")
async def startup_event():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
