import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set in .env")

# Create Async Engine
engine = create_async_engine(
    DATABASE_URL, 
    echo=False, 
    future=True,
    pool_size=10,
    max_overflow=20
)

# Async Session Factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)

async def get_db():
    """Dependency for FastAPI routes to get a DB session."""
    async with AsyncSessionLocal() as session:
        yield session