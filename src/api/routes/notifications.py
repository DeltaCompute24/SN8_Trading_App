from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_db
from src.services.notification_service import NotificationService
from src.schemas.notification import NotificationResponse

router = APIRouter(
    prefix="/notifications",
    tags=["notifications"]
)

@router.get("/{firebase_id}", response_model=List[NotificationResponse])
async def get_user_notifications(
    firebase_id: str,
    type: Optional[str] = Query(None, description="Filter by notification type"),
    trader_id: Optional[int] = Query(None, description="Filter by trader ID"),
    trader_pair: Optional[str] = Query(None, description="Filter by trader pair"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all notifications for a user with optional filters
    
    Parameters:
    - firebase_id: The Firebase ID of the user
    - type: Optional filter by notification type
    - trader_id: Optional filter by trader ID
    - trader_pair: Optional filter by trader pair
    """
    notifications = await NotificationService.get_notifications(
        db, 
        firebase_id,
        type=type,
        trader_id=trader_id,
        trader_pair=trader_pair
    )
    return notifications