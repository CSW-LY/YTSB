import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import text

async def delete_test_key():
    engine = create_async_engine("postgresql+asyncpg://postgres:123@localhost:5432/intent_service", echo=False)
    async_session_maker = async_sessionmaker(engine, expire_on_commit=False)

    async with async_session_maker() as session:
        await session.execute(text("DELETE FROM api_keys WHERE key_prefix LIKE 'test%'"))
        await session.commit()
        print("Deleted existing test API keys")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(delete_test_key())
