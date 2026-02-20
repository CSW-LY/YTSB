"""Database migration script to add full_key field to api_keys table."""

import asyncio
import secrets
import bcrypt
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text, select
from app.core.config import get_settings


async def migrate_database():
    """Migrate database schema and data."""
    settings = get_settings()
    
    print("Migrating api_keys table...")
    print(f"Database URL: {settings.async_database_url}")
    
    try:
        # Create engine
        engine = create_async_engine(
            settings.async_database_url,
            echo=False,
        )
        
        # Connect to database
        async with engine.connect() as conn:
            # Check if full_key column exists in api_keys table
            check_query = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'api_keys' 
                AND column_name = 'full_key'
            """)
            
            result = await conn.execute(check_query)
            column_exists = result.scalar() is not None
            
            if not column_exists:
                print("Adding full_key column to api_keys table...")
                # Add full_key column
                alter_query = text("""
                    ALTER TABLE api_keys 
                    ADD COLUMN full_key VARCHAR(255)
                """)
                await conn.execute(alter_query)
                await conn.commit()
                print("Column added successfully!")
            else:
                print("full_key column already exists, checking for NULL values...")
            
            # Check for NULL full_key values
            null_check_query = text("""
                SELECT COUNT(*) FROM api_keys WHERE full_key IS NULL
            """)
            result = await conn.execute(null_check_query)
            null_count = result.scalar()
            
            if null_count > 0:
                print(f"Found {null_count} API keys with NULL full_key values.")
                print("Generating full_key for existing records...")
                
                # Get API keys with NULL full_key
                get_null_keys_query = text("""
                    SELECT id, key_prefix FROM api_keys WHERE full_key IS NULL
                """)
                result = await conn.execute(get_null_keys_query)
                null_keys = result.fetchall()
                
                for key_id, key_prefix in null_keys:
                    # Generate a new full_key
                    key_suffix = secrets.token_urlsafe(32)
                    new_full_key = f"{key_prefix}_{key_suffix}"
                    
                    # Update the record
                    update_query = text("""
                        UPDATE api_keys 
                        SET full_key = :full_key 
                        WHERE id = :key_id
                    """)
                    await conn.execute(update_query, {"full_key": new_full_key, "key_id": key_id})
                    print(f"  Generated full_key for API key {key_id}")
                
                await conn.commit()
                print(f"Successfully updated {len(null_keys)} API keys!")
            else:
                print("No NULL full_key values found.")
        
        await engine.dispose()
        print("Database migration completed successfully!")
        return True
        
    except Exception as e:
        print(f"Database migration error: {e}")
        import traceback
        traceback.print_exc()
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
