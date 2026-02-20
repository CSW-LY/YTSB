"""Test PostgreSQL connection and create database if needed."""

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT


def test_postgres_connection():
    """Test PostgreSQL connection and create database if needed."""
    print("Testing PostgreSQL connection...")
    
    try:
        # Connect to default postgres database
        conn = psycopg2.connect(
            host="localhost",
            port=5432,
            user="postgres",
            password="postgres",
            database="postgres"
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        
        print("Connected to default PostgreSQL database!")
        
        # Check if intent_service database exists
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM pg_database WHERE datname='intent_service'")
        exists = cursor.fetchone()
        
        if not exists:
            print("Creating intent_service database...")
            cursor.execute("CREATE DATABASE intent_service")
            print("Database created successfully!")
        else:
            print("Database intent_service already exists!")
        
        cursor.close()
        conn.close()
        
        # Test connection to the new database
        print("Testing connection to intent_service database...")
        conn = psycopg2.connect(
            host="localhost",
            port=5432,
            user="postgres",
            password="postgres",
            database="intent_service"
        )
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        print(f"Connection test result: {result}")
        print("Connected to intent_service database successfully!")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"PostgreSQL connection error: {e}")
        return False


def main():
    """Main function."""
    success = test_postgres_connection()
    if success:
        print("PostgreSQL setup completed successfully!")
    else:
        print("PostgreSQL setup failed. Please check your PostgreSQL configuration.")


if __name__ == "__main__":
    main()
