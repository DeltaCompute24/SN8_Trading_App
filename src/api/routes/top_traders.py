from typing import Dict
from fastapi import APIRouter, HTTPException
from src.utils.redis_manager import get_all_hash_value
from src.schemas.trader import UserDetails
from src.utils.logging import setup_logging
from src.utils.constants import TOP_TRADERS
import json

logger = setup_logging()
router = APIRouter()

@router.get("/top-traders", response_model=Dict[str, UserDetails])
def get_top_traders():
   
    top_traders = get_all_hash_value(TOP_TRADERS)
    parsed_top_traders = {k: json.loads(v) if isinstance(v, str) else v for k, v in top_traders.items()}

    return parsed_top_traders
 