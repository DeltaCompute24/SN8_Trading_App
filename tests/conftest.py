import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from httpx import AsyncClient
from src.main import app
from src.database import get_db
from src.models import Base
from src.config import DATABASE_URL

# Set up the database connection
SQLALCHEMY_DATABASE_URL = DATABASE_URL
engine = create_async_engine(SQLALCHEMY_DATABASE_URL, future=True, echo=True)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=AsyncSession)

# Create a new database session for each test
@pytest.fixture(scope="function")
async def session():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with TestingSessionLocal() as session:
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

# Override the get_db dependency to use the testing session
@pytest.fixture(scope="function")
async def async_client(session: AsyncSession):
    async def _get_test_db():
        yield session

    app.dependency_overrides[get_db] = _get_test_db
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides[get_db] = get_db
    