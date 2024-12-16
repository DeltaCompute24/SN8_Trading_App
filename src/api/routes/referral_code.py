from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from src.database import get_db
from src.schemas.referral_code import ReferralCodeCreate,ReferralCodeValidate , ReferralCodeResponse, ReferralCodeListResponse
from src.services.referral_code import ReferralCodeService
from src.utils.logging import setup_logging

logger = setup_logging()
router = APIRouter()



@router.post("/", response_model=ReferralCodeResponse)
async def create_code(referral_code_data: ReferralCodeCreate,  db: Session = Depends(get_db)):
    referral_code = await ReferralCodeService.update_or_create( db, referral_code_data )
    return referral_code

@router.delete("/", response_model=ReferralCodeResponse)
async def delete_code(referral_code_data: ReferralCodeCreate, db : Session = Depends(get_db)):
    referral_code = await ReferralCodeService.delete( db, referral_code_data )
    return referral_code

@router.post("/validate", response_model= ReferralCodeResponse)
async def validate_code(referral_code_data: ReferralCodeValidate, db: Session = Depends(get_db)):
    """
    Validate a referral code
    """
    referral_code = await ReferralCodeService.validate_code( db, referral_code_data )
    return referral_code

@router.get("/", response_model=ReferralCodeListResponse)
async def get_all_codes(db: Session = Depends(get_db)):
    """
   Get all Codes
    """
    codes = await ReferralCodeService.get_all_codes(db)
    return ReferralCodeListResponse(codes=codes)
