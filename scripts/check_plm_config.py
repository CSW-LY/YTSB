import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import text

async def check_plm_config():
    engine = create_async_engine("postgresql+asyncpg://postgres:123@localhost:5432/intent_service", echo=False)
    async_session_maker = async_sessionmaker(engine, expire_on_commit=False)

    async with async_session_maker() as session:
        print("=" * 60)
        print("检查 plm_assistant 应用配置")
        print("=" * 60)

        # Check app configs
        result = await session.execute(text("SELECT app_key, intent_ids FROM app_intents"))
        apps = result.fetchall()
        print(f"\n应用配置数量: {len(apps)}")
        for app in apps:
            print(f"  - {app[0]}: {app[1]}")

        # Check part.search category
        result = await session.execute(
            text("SELECT id, code, name, description FROM intent_categories WHERE code = 'part.search'")
        )
        part_search = result.fetchone()
        if part_search:
            print(f"\n找到 part.search 意图:")
            print(f"  ID: {part_search[0]}")
            print(f"  Code: {part_search[1]}")
            print(f"  Name: {part_search[2]}")
            print(f"  Description: {part_search[3]}")
        else:
            print("\n未找到 part.search 意图!")

        # Check rules for part.search
        result = await session.execute(
            text("""
                SELECT rule_type, content, weight, is_active
                FROM intent_rules
                WHERE category_id = :cat_id
                ORDER BY rule_type, content
            """),
            {"cat_id": part_search[0] if part_search else 0}
        )
        rules = result.fetchall()
        print(f"\npart.search 意图规则数量: {len(rules)}")
        for rule in rules:
            active = "✓" if rule[3] else "✗"
            print(f"  [{active}] {rule[0]:10s} {rule[1]:20s} (权重: {rule[2]})")

        # Check specifically for "检索零件"
        result = await session.execute(
            text("""
                SELECT ir.*, ic.code as category_code
                FROM intent_rules ir
                JOIN intent_categories ic ON ir.category_id = ic.id
                WHERE ir.content LIKE '%检索零件%' OR ir.content LIKE '%我要检索零件%'
            """)
        )
        search_rules = result.fetchall()
        print(f"\n包含'检索零件'的规则:")
        if search_rules:
            for rule in search_rules:
                print(f"  - {rule[3]}: {rule[2]} (类别: {rule[5]})")
        else:
            print("  未找到!")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check_plm_config())
