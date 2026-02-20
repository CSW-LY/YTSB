import asyncio
import bcrypt
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import text
import secrets

async def create_api_key():
    engine = create_async_engine("postgresql+asyncpg://postgres:123@localhost:5432/intent_service", echo=False)
    async_session_maker = async_sessionmaker(engine, expire_on_commit=False)

    async with async_session_maker() as session:
        # Generate API key - use exactly 20 characters for prefix match
        api_key_prefix = "test_87be5660e7092c"
        api_key = f"{api_key_prefix}{secrets.token_hex(16)}"

        # Hash with bcrypt (used for verification in security.py)
        key_hash = bcrypt.hashpw(api_key.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        # Insert API key - use first 20 chars as key_prefix
        await session.execute(
            text("""
                INSERT INTO api_keys (key_prefix, key_hash, full_key, is_active, rate_limit, permissions)
                VALUES (:key_prefix, :key_hash, :full_key, true, 1000, '[]')
            """),
            {"key_prefix": api_key[:20], "key_hash": key_hash, "full_key": api_key}
        )

        await session.commit()

        print(f"Created API key: {api_key}")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(create_api_key())
