from typing import Optional, Set, List
from sqlalchemy import select, exists
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from src.models.referral_code import ReferralCode, user_referral_codes
from src.schemas.referral_code import ReferralCodeCreate, ReferralCodeBase
from datetime import date
from sqlalchemy.orm import Session, joinedload
import string
import random
from src.services.user_service import get_user_by_email

class ReferralCodeService:
    @staticmethod
    async def get_code(db: AsyncSession, code: str) -> Optional[ReferralCode]:
        """Get a single referral code with its related users"""
        query = (
            select(ReferralCode)
             .options(joinedload(ReferralCode.users))
            .filter(ReferralCode.code == code)
            
        )
        result = await db.execute(query)
        return result.unique().scalar_one_or_none()
    
    @staticmethod
    async def get_all_codes(db: AsyncSession) -> List[ReferralCode]:
        """Get all referral codes with their related users"""
        query = (
            select(ReferralCode)
            .options(joinedload(ReferralCode.users))
        )
        result = await db.execute(query)
        return result.scalars().unique().all()
    
    @staticmethod
    async def validate_code(db: AsyncSession, code_data: ReferralCodeBase) -> ReferralCode:
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
        code_data.code = await ReferralCodeService.generate_unique_code(db) if code_data.auto_generate or not code_data.code else code_data.code
        referral_code = await ReferralCodeService.get_code(db, code_data.code)
        result = await ReferralCodeService.update(db, code_data , referral_code) if referral_code else await ReferralCodeService.create(db,code_data)
        return result
    
    @staticmethod
    async def create(db: AsyncSession, code_data: ReferralCodeCreate) -> ReferralCode:
        referral_code = ReferralCode(**code_data.model_dump(exclude={'auto_generate'}))
        generated_by = await get_user_by_email(db, code_data.generated_by_id)
        if not generated_by:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User not found for id: {code_data.generated_by_id}"
            )
        referral_code.generated_by = generated_by
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
      
        for key, value in code_data.model_dump(exclude_unset=True, exclude={'auto_generate'}).items():
            setattr(referral_code, key, value)
        
        
        if validate:
            ReferralCodeService.check_date_validity(referral_code)
            ReferralCodeService.check_if_code_used_already(referral_code)
            ReferralCodeService.check_if_code_is_multi_use(referral_code)
            user = await get_user_by_email(db, code_data.user_id)
            ReferralCodeService.check_if_validating_user_is_in_system(user , code_data.user_id)
            ReferralCodeService.check_if_validating_user_already_validated(db,  user = user , referral_code =referral_code)

            referral_code.users.append(user)
          
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

    @staticmethod
    def check_date_validity(referral_code : ReferralCode):
        today = date.today()
        if today > referral_code.valid_to or today < referral_code.valid_from:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Referral code validity period has expired"
            )
            
    @staticmethod
    def check_if_code_used_already(referral_code : ReferralCode):
        if not referral_code.is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Referral code is not valid"
            )
            
    @staticmethod
    def check_if_code_is_multi_use(referral_code : ReferralCode):
        is_referral_code_used_already = len(referral_code.users) > 0 and not referral_code.multiple_use
        if is_referral_code_used_already:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Referral code is single use only!"
            )
            
    @staticmethod
    def check_if_validating_user_is_in_system(user : ReferralCode, user_id : str):
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User not found for id: {user_id}"
            )
            
    @staticmethod
    def check_if_validating_user_already_validated(db: Session,referral_code : ReferralCode, user = None  , by_email = False , email = None):
        
        if not by_email:
            
            if user in referral_code.users:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"User already used this referral code"
                )
        else:
            exists_query = db.query(exists().where(
            user_referral_codes.c.referral_code_id == referral_code.id,
            user_referral_codes.c.user_id == email
            )).scalar()
            if exists_query:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User already used this referral code"
                )
            
            
        
    async def generate_unique_code(db: AsyncSession, length: int = 7) -> str:
        """
        Generate a unique alphanumeric code of specified length
        
        Args:
            db: Database session
            existing_codes: Set of codes to check against (optional)
            length: Length of code (default 7)
        
        Returns:
            str: Unique alphanumeric code
        """
        # Characters to use (uppercase letters and numbers)
        chars = string.ascii_uppercase + string.digits
        
        while True:
            # Generate a random code
            code = ''.join(random.choices(chars, k=length))
            exists = await ReferralCodeService.get_code(db, code)
            if not exists:
                return code
        