from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from src.config import DATABASE_URL, DATABASE_URL_SYNC

task_engine = create_async_engine(DATABASE_URL, echo=True, pool_size=20, max_overflow=30, pool_timeout=30)
TaskSessionLocal = sessionmaker(
    bind=task_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# postgres without asynchronous
task_engine_ = create_engine(DATABASE_URL_SYNC, echo=True, pool_size=20, max_overflow=30, pool_timeout=30)
TaskSessionLocal_ = sessionmaker(
    bind=task_engine_,
    expire_on_commit=False
)

Base = declarative_base()


def get_sync_db():
    db = TaskSessionLocal_()
    try:
        yield db
    finally:
        db.close()
