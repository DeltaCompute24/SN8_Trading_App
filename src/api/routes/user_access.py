from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session
from src.database import get_db
from src.models.payout import Payout
from src.schemas.user_access import  UserAccessSchema
from src.services.payout_service import PayoutService
from src.utils.logging import setup_logging
from typing import Dict, Any, Optional  

logger = setup_logging()
router = APIRouter()



@router.post("/access", response_model=PayoutSchema)
async def invite_user(access: UserAccessSchema, firebase_id: str =  Path(..., description="Firebase ID of the user"), db: Session = Depends(get_db)):
    
    # checks if the user has been already invited - user accepted invitation or its in pending
    is_user_already_invited_to_account()
      
      #creates a new referral code for the user 
    Referralcodeservice.create
      
      #generates and sends the email to the user
    send_email()
    
  return payout


@router.get("/{firebase_id}", response_model= Optional[PayoutSchema])
async def get_payout_information(firebase_id: str =  Path(..., description="Firebase ID of the user"), db: Session = Depends(get_db)):
    """
    If the payout is not found, it will return a new payout with the firebase_id and type "wire"
    """
    
    payout = await PayoutService.get_by_user_id( db, firebase_id  )
    logger.info(f"Retrieved payout information for firebase_id={firebase_id}")
    return payout or Payout(user_id=firebase_id, type="wire")
