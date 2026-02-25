"""Add rule strategy configuration fields to applications table."""

import sys
sys.path.insert(0, ".")

import psycopg2
from sqlalchemy import create_engine, text
from app.core.config import get_settings

settings = get_settings()

print("=" * 50)
print("Adding rule strategy fields to applications table")
print("=" * 50)

# Connect to PostgreSQL
conn = psycopg2.connect(
    host=settings.db_host,
    port=settings.db_port,
    database=settings.db_name,
    user=settings.db_user,
    password=settings.db_password
)

try:
    with conn.cursor() as cursor:
        # Check if columns already exist
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'applications' 
            AND column_name IN ('enable_keyword', 'enable_regex', 'enable_semantic', 'enable_llm_fallback')
        """)
        existing_columns = [row[0] for row in cursor.fetchall()]
        
        print(f"Existing columns: {existing_columns}")
        
        # Add columns if they don't exist
        if 'enable_keyword' not in existing_columns:
            print("Adding enable_keyword column...")
            cursor.execute("ALTER TABLE applications ADD COLUMN enable_keyword BOOLEAN DEFAULT TRUE NOT NULL")
        
        if 'enable_regex' not in existing_columns:
            print("Adding enable_regex column...")
            cursor.execute("ALTER TABLE applications ADD COLUMN enable_regex BOOLEAN DEFAULT TRUE NOT NULL")
        
        if 'enable_semantic' not in existing_columns:
            print("Adding enable_semantic column...")
            cursor.execute("ALTER TABLE applications ADD COLUMN enable_semantic BOOLEAN DEFAULT TRUE NOT NULL")
        
        if 'enable_llm_fallback' not in existing_columns:
            print("Adding enable_llm_fallback column...")
            cursor.execute("ALTER TABLE applications ADD COLUMN enable_llm_fallback BOOLEAN DEFAULT FALSE NOT NULL")
        
        conn.commit()
        print("All columns added successfully!")
        
        # Verify the columns
        cursor.execute("""
            SELECT column_name, data_type, column_default 
            FROM information_schema.columns 
            WHERE table_name = 'applications' 
            AND column_name IN ('enable_keyword', 'enable_regex', 'enable_semantic', 'enable_llm_fallback')
        """)
        print("\nUpdated table structure:")
        for row in cursor.fetchall():
            print(f"  {row[0]}: {row[1]} (default: {row[2]})")

except Exception as e:
    conn.rollback()
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
finally:
    conn.close()
