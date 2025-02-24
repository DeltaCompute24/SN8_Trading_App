from typing import List
from fastapi import APIRouter, HTTPException
from src.utils.redis_manager import get_top_traders_by_rank_and_metrics
from src.schemas.trader import TraderRead
from src.utils.logging import setup_logging

logger = setup_logging()
router = APIRouter()

@router.get("/top-traders", response_model=List[TraderRead])
def get_top_traders():
    logger.info("Fetching top traders by all_time_returns")
    try:
        top_traders = get_top_traders_by_rank_and_metrics()
        return [
            TraderRead(
                hot_key=top_trader["hot_key"],
                rank=top_trader["rank"],
                trader_pairs=top_trader["trader_pairs"],
                username=top_trader["username"],
                email=top_trader["email"],
                sortino_ratio=str(top_trader["sortino"]),
                omega_ratio=str(top_trader["omega"]),
                sharpe_ratio=str(top_trader["sharpe"]),
                all_time_returns=str(top_trader["all_time_returns"]),
                thirty_days_return=str(top_trader["thirty_days_return"]),
            ) for top_trader in top_traders
        ]
    except Exception as e:
        logger.error(f"Error fetching top traders: {e}")
        raise HTTPException(status_code=500, detail=str(e))