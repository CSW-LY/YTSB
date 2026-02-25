"""
Migration script to add intent recognition configuration fields to the applications table.

This script adds the following fields:
- enable_cache: Enable/disable recognition result caching
- fallback_intent_code: Fallback intent code when no rules match
- confidence_threshold: Confidence threshold for recognition results
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.core.database import async_session_maker, engine


async def migrate():
    """Run the migration."""
    
    print("Starting migration: Add intent recognition configuration fields to applications table...")
    
    async with async_session_maker() as session:
        try:
            async with engine.begin() as conn:
                # Add enable_cache field
                try:
                    await conn.execute(text("""
                        ALTER TABLE applications 
                        ADD COLUMN IF NOT EXISTS enable_cache BOOLEAN DEFAULT TRUE
                    """))
                    print("✓ Added enable_cache field")
                except Exception as e:
                    print(f"  enable_cache field already exists or error: {e}")
                
                # Add fallback_intent_code field
                try:
                    await conn.execute(text("""
                        ALTER TABLE applications 
                        ADD COLUMN IF NOT EXISTS fallback_intent_code VARCHAR(50)
                    """))
                    print("✓ Added fallback_intent_code field")
                except Exception as e:
                    print(f"  fallback_intent_code field already exists or error: {e}")
                
                # Add confidence_threshold field
                try:
                    await conn.execute(text("""
                        ALTER TABLE applications 
                        ADD COLUMN IF NOT EXISTS confidence_threshold FLOAT DEFAULT 0.7
                    """))
                    print("✓ Added confidence_threshold field")
                except Exception as e:
                    print(f"  confidence_threshold field already exists or error: {e}")
            
            await session.commit()
            
            print("\n✓ Migration completed successfully!")
            print("\nNew fields added to applications table:")
            print("  - enable_cache (BOOLEAN, DEFAULT: TRUE)")
            print("  - fallback_intent_code (VARCHAR(50), DEFAULT: NULL)")
            print("  - confidence_threshold (FLOAT, DEFAULT: 0.7)")
            
        except Exception as e:
            print(f"\n✗ Migration failed: {e}")
            await session.rollback()
            sys.exit(1)


async def verify():
    """Verify the migration."""
    
    print("\nVerifying migration...")
    
    async with async_session_maker() as session:
        result = await session.execute(text("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_name = 'applications'
            AND column_name IN ('enable_cache', 'fallback_intent_code', 'confidence_threshold')
            ORDER BY column_name
        """))
        
        columns = result.fetchall()
        
        if len(columns) == 3:
            print("✓ All 3 new columns exist in applications table")
            for col in columns:
                print(f"  - {col[0]}: {col[1]} (nullable: {col[2]}, default: {col[3]})")
        else:
            print(f"✗ Expected 3 columns, found {len(columns)}")
            return False
    
    return True


if __name__ == "__main__":
    asyncio.run(migrate())
    asyncio.run(verify())
