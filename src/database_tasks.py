from contextlib import asynccontextmanager

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from src.config import DATABASE_URL

task_engine = create_async_engine(DATABASE_URL, echo=True, pool_size=20, max_overflow=30, pool_timeout=30)
TaskSessionLocal = sessionmaker(
    bind=task_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# mysql
DATABASE_URL="mysql+mysqlconnector://root:password@localhost:3306/database_name"
task_engine_2 = create_engine(DATABASE_URL, echo=True, pool_size=20, max_overflow=30, pool_timeout=30)
TaskSessionLocal_2 = sessionmaker(
    bind=task_engine_2,
    expire_on_commit=False
)

# postgres
DATABASE_URL = "postgresql+psycopg2://developer:DeltaCompute123@rococo-db-server-postgres-aurora.cluster-c3y444mm80qj.eu-west-1.rds.amazonaws.com/postgres"
task_engine_3 = create_engine(DATABASE_URL, echo=True, pool_size=20, max_overflow=30, pool_timeout=30)
TaskSessionLocal_3 = sessionmaker(
    bind=task_engine_3,
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
