"""
Database connection and session management using SQLAlchemy.
"""

import logging
from typing import AsyncGenerator
from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

from src.core.config import get_settings

# Setup logging
logger = logging.getLogger(__name__)

# Get settings
settings = get_settings()

# Create database engines
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
    echo=settings.LOG_LEVEL == "DEBUG"
)

async_engine = create_async_engine(
    settings.DATABASE_URL_ASYNC,
    pool_pre_ping=True,
    pool_recycle=300,
    echo=settings.LOG_LEVEL == "DEBUG"
)

# Create session makers
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Create declarative base
Base = declarative_base()

# Metadata for migrations
metadata = MetaData()


def get_sync_db() -> Session:
    """
    Get synchronous database session.
    
    Yields:
        Session: SQLAlchemy database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Get asynchronous database session.
    
    Yields:
        AsyncSession: SQLAlchemy async database session
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """
    Initialize database tables.
    """
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables initialized")


async def close_db():
    """
    Close database connections.
    """
    await async_engine.dispose()
    engine.dispose()
    logger.info("Database connections closed")