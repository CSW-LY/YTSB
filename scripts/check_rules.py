import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import select, text
import sys
sys.path.insert(0, 'D:/code/YTSB/intent-service')

async def check_rules():
    # 从配置读取数据库连接
    engine = create_async_engine("postgresql+asyncpg://postgres:123@localhost:5432/intent_service", echo=False)
    async_session_maker = async_sessionmaker(engine, expire_on_commit=False)

    async with async_session_maker() as session:
        # 查询所有意图类别
        categories_result = await session.execute(
            text("SELECT id, code, name, description FROM intent_categories WHERE is_active = true")
        )
        categories = categories_result.fetchall()

        print("\n=== 意图类别 ===")
        for cat in categories:
            print(f"  {cat[0]} | {cat[1]} | {cat[2]} | {cat[3] or ''}")

        # 查询所有规则
        rules_result = await session.execute(
            text("""
                SELECT r.id, c.code as category_code, r.rule_type, r.content, r.weight
                FROM intent_rules r
                JOIN intent_categories c ON r.category_id = c.id
                WHERE r.is_active = true
                ORDER BY c.code, r.weight DESC
            """)
        )
        rules = rules_result.fetchall()

        print("\n=== 意图规则 ===")
        for rule in rules:
            print(f"  {rule[0]} | {rule[1]} | {rule[2]} | {rule[3]} | 权重:{rule[4]}")

        # 搜索"零件"相关的规则
        search_result = await session.execute(
            text("SELECT r.id, c.code, r.rule_type, r.content FROM intent_rules r JOIN intent_categories c ON r.category_id = c.id WHERE r.content LIKE '%零件%'")
        )
        part_rules = search_result.fetchall()

        print(f"\n=== 包含'零件'的规则 (共{len(part_rules)}条) ===")
        for rule in part_rules:
            print(f"  {rule[0]} | {rule[1]} | {rule[2]} | {rule[3]}")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check_rules())
