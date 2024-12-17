from fastapi import Depends, HTTPException, status
from firebase_admin import auth
from src.services.user_service import get_user_by_firebase_id

async def get_current_user(token: str = Depends(get_token)):
    try:
        decoded_token = auth.verify_id_token(token)
        user = await get_user_by_firebase_id(decoded_token['uid'])
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        return user
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        ) 