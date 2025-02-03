from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from src.models.notifications import Notification
from src.schemas.notification import NotificationCreate
from sqlalchemy.orm import joinedload , Session
from src.models.firebase_user import FirebaseUser
from src.models.transaction import Transaction
from src.services.user_service import get_firebase_user_by_trader_id
class NotificationService:
    @staticmethod
    async def get_notifications(
        db: AsyncSession, 
        firebase_id: str,
        type: Optional[str] = None,
        trader_id: Optional[int] = None,
        trader_pair: Optional[str] = None
    ) -> List[Notification]:
        """Get all notifications for a user with optional filters"""
        query = (
            select(Notification)
            .options(joinedload(Notification.user))
            .filter(Notification.user_id == firebase_id)
        )
        
        # Apply filters if provided
        if type:
            query = query.filter(Notification.type == type)
        if trader_id:
            query = query.filter(Notification.trader_id == trader_id)
        if trader_pair:
            query = query.filter(Notification.trader_pair == trader_pair)
            
        # Add ordering by created_at descending
        query = query.order_by(Notification.created_at.desc())
            
        result = await db.execute(query)
        return result.scalars().unique().all()
    
    @staticmethod
    def save_notification(db, position : Transaction , message :str):
    
        try:
            user =  get_firebase_user_by_trader_id(db , position.trader_id)
        
        
            NotificationService.create_notification(db, NotificationCreate( 
                trader_id= position.trader_id,
                trader_pair = position.trade_pair,
                message = message ,
                type = 'position-monitor-sync-challenge'
                ) , user = user )

        except Exception as e:
            print(f"An error occurred while saving notification :{e} {message}")
        
    
    
    @staticmethod
    def create_notification(db: Session, notification_data: NotificationCreate , user = None) -> Notification:
        """Create a new notification"""
        # First, get the user
        
        if notification_data.user_id:
          user_query = select(FirebaseUser).filter(FirebaseUser.firebase_id == notification_data.user_id)
          result =  db.execute(user_query)
          user = result.scalar_one_or_none()
          
          
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User not found , cannot create Notification"
            )

        # Create notification with user relationship
        notification = Notification(**notification_data.model_dump())
        notification.user = user  # This will automatically set user_id and establish the relationship
      
        db.add(notification)
        try:
            db.commit()
            db.refresh(notification)
            return notification
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Could not create notification: {str(e)}"
            )