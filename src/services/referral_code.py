from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from src.models.referral_code import ReferralCode
from src.schemas.referral_code import ReferralCodeCreate
from datetime import date

class ReferralCodeService:
    @staticmethod
    async def get_code(db: AsyncSession, code: str) -> Optional[ReferralCode]:
        query = select(ReferralCode).filter(ReferralCode.code == code)
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    @staticmethod
    async def validate_code(db: AsyncSession, code_data: ReferralCodeCreate) -> ReferralCode:
      referral_code = await ReferralCodeService.get_code(db, code_data.code)
      if not referral_code:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Referral code not found for code: {code_data.code}"
        )
      result = await ReferralCodeService.update(db, code_data , referral_code , validate=True)
      return result
      
    
    @staticmethod
    async def update_or_create(db: AsyncSession, code_data: ReferralCodeCreate) -> ReferralCode:
        referral_code = await ReferralCodeService.get_code(db, code_data.code)
        result = await ReferralCodeService.update(db, code_data , referral_code) if referral_code else await ReferralCodeService.create(db,code_data)
        return result
    
    @staticmethod
    async def create(db: AsyncSession, code_data: ReferralCodeCreate) -> ReferralCode:
        referral_code = ReferralCode(**code_data.model_dump())
        db.add(referral_code)
        try:
            await db.commit()
            await db.refresh(referral_code)
            return referral_code
        except Exception as e:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Could not create referral code: {str(e)}"
            )

    @staticmethod
    async def update(
        db: AsyncSession, 
        code_data: ReferralCodeCreate,
        referral_code: ReferralCode,
        validate: bool = False
    ) -> Optional[ReferralCode]:
      
        for key, value in code_data.model_dump(exclude_unset=True).items():
            setattr(referral_code, key, value)
        
        
        if validate:
          today = date.today()
          if today > referral_code.valid_to or today < referral_code.valid_from:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Referral code validity period has expired"
            )
          
          if not referral_code.is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Referral code is not valid"
            )
            
          is_referral_code_used_already = referral_code.users.count() > 0 and not referral_code.multiple_use
          if is_referral_code_used_already:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Referral code is single use only!"
            )
          
          
          referral_code.users.append(code_data.user_id)
          
          if not referral_code.multiple_use:
            referral_code.is_valid = False
        try:
            await db.commit()
            await db.refresh(referral_code)
            return referral_code
        except Exception as e:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Could not update referral code: {str(e)}"
            )



    @staticmethod
    async def delete(db: AsyncSession, code: str) -> bool:
        referral_code = await ReferralCodeService.get_code(db, code)
        if not referral_code:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Referral code not found for code: {code}"
            )

        try:
            await db.delete(referral_code)
            await db.commit()
            return True
        except Exception as e:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Could not delete referral code: {str(e)}"
            )

