from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from src.config import DATABASE_URL

task_engine = create_async_engine(DATABASE_URL, echo=True, pool_size=25, max_overflow=50, pool_timeout=60)
TaskSessionLocal = sessionmaker(
    bind=task_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

Base = declarative_base()


@asynccontextmanager
async def get_task_db():
    async with TaskSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
