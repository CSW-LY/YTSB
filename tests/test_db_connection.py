"""Test database connection and create necessary schema."""

import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

from app.models.database import Base
from app.core.config import get_settings


async def test_db_connection():
    """Test database connection and create schema if needed."""
    settings = get_settings()
    
    print("Testing database connection...")
    print(f"Database URL: {settings.async_database_url}")
    
    try:
        # Create engine
        engine = create_async_engine(
            settings.async_database_url,
            echo=True,
        )
        
        # Test connection
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            print(f"Connection test result: {result.scalar()}")
            print("Database connection successful!")
        
        # Create tables if they don't exist
        print("Creating database schema...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("Schema created successfully!")
        
        await engine.dispose()
        return True
        
    except Exception as e:
        print(f"Database connection error: {e}")
        return False


async def main():
    """Main function."""
    success = await test_db_connection()
    if success:
        print("Database setup completed successfully!")
    else:
        print("Database setup failed. Please check your database configuration.")


if __name__ == "__main__":
    asyncio.run(main())
