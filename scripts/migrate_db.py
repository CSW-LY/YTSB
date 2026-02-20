"""Database migration script to add api_key_id field to intent_recognition_logs table."""

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.config import get_settings


async def migrate_database():
    """Migrate database schema."""
    settings = get_settings()
    
    print("Migrating database schema...")
    print(f"Database URL: {settings.async_database_url}")
    
    try:
        # Create engine
        engine = create_async_engine(
            settings.async_database_url,
            echo=True,
        )
        
        # Connect to database
        async with engine.connect() as conn:
            # Check if api_key_id column exists in intent_recognition_logs table
            check_query = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'intent_recognition_logs' 
                AND column_name = 'api_key_id'
            """)
            
            result = await conn.execute(check_query)
            column_exists = result.scalar() is not None
            
            if not column_exists:
                print("Adding api_key_id column to intent_recognition_logs table...")
                # Add api_key_id column
                alter_query = text("""
                    ALTER TABLE intent_recognition_logs 
                    ADD COLUMN api_key_id INTEGER REFERENCES api_keys(id)
                """)
                await conn.execute(alter_query)
                await conn.commit()
                print("Column added successfully!")
            else:
                print("api_key_id column already exists, skipping migration.")
        
        await engine.dispose()
        print("Database migration completed successfully!")
        return True
        
    except Exception as e:
        print(f"Database migration error: {e}")
        return False


async def main():
    """Main function."""
    success = await migrate_database()
    if success:
        print("Migration completed successfully!")
    else:
        print("Migration failed. Please check the error message above.")


if __name__ == "__main__":
    asyncio.run(main())
