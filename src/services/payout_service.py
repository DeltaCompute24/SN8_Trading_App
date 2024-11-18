from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from src.models.payout import Payout
from src.schemas.payout import PayoutSchema

class PayoutService:
    @staticmethod
    async def get_by_user_id(db: AsyncSession, user_id: str) -> Optional[Payout]:
        query = select(Payout).filter(Payout.user_id == str(user_id))
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    @staticmethod
    async def update_or_create(db: AsyncSession, user_id: str, payout_data: PayoutSchema) -> Payout:
        payout = await PayoutService.get_by_user_id(db, user_id)
        result = await PayoutService.update(db, user_id, payout_data, payout) if payout else await PayoutService.create(db,user_id, payout_data)
        return result
    
    @staticmethod
    async def create(db: AsyncSession, user_id: str, payout_data: PayoutSchema) -> Payout:
        # Create new payout
        payout = Payout(**payout_data.model_dump(exclude={"user_id"}), user_id=user_id)
        db.add(payout)
        try:
            await db.commit()
            await db.refresh(payout)
            return payout
        except Exception as e:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Could not create payout: {str(e)}"
            )

    @staticmethod
    async def update(
        db: AsyncSession, 
        user_id: str, 
        payout_data: PayoutSchema,
        payout: Payout
    ) -> Optional[Payout]:
      
        for key, value in payout_data.model_dump(exclude_unset=True).items():
            setattr(payout, key, value)

        try:
            await db.commit()
            await db.refresh(payout)
            return payout
        except Exception as e:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Could not update payout: {str(e)}"
            )



    @staticmethod
    async def delete(db: AsyncSession, user_id: str) -> bool:
        payout = await PayoutService.get_by_user_id(db, user_id)
        if not payout:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Payout not found for user_id: {user_id}"
            )

        try:
            await db.delete(payout)
            await db.commit()
            return True
        except Exception as e:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Could not delete payout: {str(e)}"
            )

