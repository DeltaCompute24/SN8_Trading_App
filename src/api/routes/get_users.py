from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy import desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.database import get_db
from src.models.users import Users
from src.schemas.user import UsersSchema
from src.utils.logging import setup_logging

logger = setup_logging()
router = APIRouter()


@router.get("/users/", response_model=List[UsersSchema])
async def get_users(
        db: AsyncSession = Depends(get_db),
):
    logger.info("Fetching Users")
    query = select(Users)
    query = query.order_by(desc(Users.updated_at), desc(Users.created_at))
    result = await db.execute(query)
    return result.scalars().all()

@router.get("/hello/", response_model=str)
def hello_world():
    return "Helloo World testing"
