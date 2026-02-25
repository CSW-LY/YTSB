"""Add 'enabled' column to intent_rules table."""
import asyncio
import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from sqlalchemy import text
from app.db import async_session_maker


async def migrate():
    """Add enabled column to intent_rules table."""
    async with async_session_maker() as session:
        try:
            print("Checking if 'enabled' column exists in intent_rules table...")
            result = await session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'intent_rules' 
                AND column_name = 'enabled';
            """))
            column_exists = result.fetchone() is not None
            
            if column_exists:
                print("Column 'enabled' already exists. Migration not needed.")
                return
            
            print("Adding 'enabled' column to intent_rules table...")
            await session.execute(text("""
                ALTER TABLE intent_rules 
                ADD COLUMN enabled BOOLEAN DEFAULT TRUE;
            """))
            await session.commit()
            print("Successfully added 'enabled' column to intent_rules table.")
            
            print("Verifying the column was added...")
            result = await session.execute(text("""
                SELECT column_name, data_type, column_default 
                FROM information_schema.columns 
                WHERE table_name = 'intent_rules' 
                AND column_name = 'enabled';
            """))
            column_info = result.fetchone()
            if column_info:
                print(f"Column details: {column_info}")
            
            print("\nMigration completed successfully!")
            
        except Exception as e:
            print(f"\nMigration failed: {e}")
            import traceback
            traceback.print_exc()
            await session.rollback()
            raise


if __name__ == "__main__":
    print("=" * 60)
    print("Add 'enabled' column to intent_rules table")
    print("=" * 60)
    
    try:
        asyncio.run(migrate())
    except Exception as e:
        print(f"\nFailed to complete migration: {e}")
        sys.exit(1)
