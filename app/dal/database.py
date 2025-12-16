from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker, Session
import os

# Database configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://postgres:password@cc_db:5432/curiosity_cottage"
)

# Create engine
engine = create_engine(DATABASE_URL, pool_pre_ping=True, echo=False)

# Async Engine (For Phase 4 Scalability)
# Ensure we use the asyncpg driver
ASYNC_DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
async_engine = create_async_engine(ASYNC_DATABASE_URL, pool_pre_ping=True, echo=False)

# Session factory (Sync)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Session factory (Async)
async_session_maker = async_sessionmaker(
    async_engine, class_=AsyncSession, expire_on_commit=False
)


def get_db() -> Session:
    """Dependency for FastAPI/Litestar to inject DB session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_async_db() -> AsyncSession:
    """Dependency for Async consumers"""
    async with async_session_maker() as session:
        yield session


def init_db():
    """Initialize database tables"""
    from app.dal.models import Base

    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created/verified")
