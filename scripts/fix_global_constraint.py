"""修复全局约束问题。"""
import asyncio
import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from sqlalchemy import text
from app.db import async_session_maker


async def fix_constraint():
    """修复约束问题。"""
    async with async_session_maker() as session:
        try:
            # 查找所有约束，包括孤立约束
            print("1. 查找所有约束...")
            result = await session.execute(text("""
                SELECT 
                    conname as constraint_name,
                    contype as constraint_type,
                    conrelid::regclass as table_name
                FROM pg_constraint
                WHERE conname = 'uq_application_category_code'
                ORDER BY conname;
            """))
            constraints = result.fetchall()
            
            if constraints:
                print(f"   找到 {len(constraints)} 个 uq_application_category_code 约束:")
                for constraint in constraints:
                    table = constraint[2] if constraint[2] else '(无表)'
                    print(f"     - {constraint[0]} (类型: {constraint[1]}, 表: {table})")
                
                # 删除所有这些约束
                print("\n2. 删除所有 uq_application_category_code 约束...")
                for constraint in constraints:
                    table_name = constraint[2]
                    if table_name:
                        try:
                            await session.execute(text(f"""
                                ALTER TABLE {table_name} 
                                DROP CONSTRAINT IF EXISTS uq_application_category_code;
                            """))
                            await session.commit()
                            print(f"   ✓ 从表 {table_name} 删除约束")
                        except Exception as e:
                            print(f"   ✗ 删除约束失败: {e}")
                            await session.rollback()
                
                # 如果没有关联的表，尝试直接删除约束
                if not any(c[2] for c in constraints):
                    print("\n   尝试删除孤立约束...")
                    try:
                        await session.execute(text("DROP CONSTRAINT uq_application_category_code;"))
                        await session.commit()
                        print("   ✓ 删除孤立约束成功")
                    except Exception as e:
                        print(f"   ✗ 删除孤立约束失败: {e}")
                        await session.rollback()
            else:
                print("   未找到 uq_application_category_code 约束")
            
            # 再次检查表
            print("\n3. 检查 intent_categories 表...")
            result = await session.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'intent_categories'
                );
            """))
            table_exists = result.scalar()
            
            if table_exists:
                print("   intent_categories 表存在，正在检查数据...")
                result = await session.execute(text("SELECT COUNT(*) FROM intent_categories;"))
                count = result.scalar()
                print(f"   当前有 {count} 条分类数据")
            else:
                print("   intent_categories 表不存在")
            
            # 创建表（如果不存在）
            if not table_exists:
                print("\n4. 创建 intent_categories 表...")
                await session.execute(text("""
                    CREATE TABLE intent_categories (
                        id SERIAL PRIMARY KEY,
                        application_id INTEGER NOT NULL,
                        code VARCHAR(50) NOT NULL,
                        name VARCHAR(100) NOT NULL,
                        description TEXT,
                        priority INTEGER DEFAULT 0,
                        is_active BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                        CONSTRAINT fk_application 
                            FOREIGN KEY (application_id) 
                            REFERENCES applications(id) 
                            ON DELETE CASCADE
                    );
                """))
                
                # 创建唯一约束
                print("5. 创建唯一约束...")
                try:
                    await session.execute(text("""
                        ALTER TABLE intent_categories 
                        ADD CONSTRAINT uq_application_category_code 
                        UNIQUE (application_id, code);
                    """))
                    print("   ✓ 唯一约束创建成功")
                except Exception as e:
                    print(f"   ⚠️  唯一约束创建失败: {e}")
                
                # 创建索引
                print("6. 创建索引...")
                await session.execute(text("""
                    CREATE INDEX idx_intent_categories_application_id 
                    ON intent_categories(application_id);
                """))
                
                await session.execute(text("""
                    CREATE INDEX idx_intent_categories_code 
                    ON intent_categories(code);
                """))
                
                # 创建触发器函数
                print("7. 创建触发器函数...")
                await session.execute(text("""
                    CREATE OR REPLACE FUNCTION update_updated_at_column()
                    RETURNS TRIGGER AS $$
                    BEGIN
                        NEW.updated_at = CURRENT_TIMESTAMP;
                        RETURN NEW;
                    END;
                    $$ language 'plpgsql';
                """))
                
                # 创建触发器
                print("8. 创建触发器...")
                await session.execute(text("""
                    CREATE TRIGGER update_intent_categories_updated_at
                        BEFORE UPDATE ON intent_categories
                        FOR EACH ROW
                        EXECUTE FUNCTION update_updated_at_column();
                """))
                
                await session.commit()
                print("\n✓ intent_categories 表创建成功！")
            
            # 检查 applications 表
            print("\n9. 检查 applications 表...")
            result = await session.execute(text("""
                SELECT id, app_key, name FROM applications ORDER BY id;
            """))
            apps = result.fetchall()
            
            if apps:
                print(f"   可用的应用:")
                for app in apps:
                    print(f"     - ID: {app[0]}, app_key: {app[1]}, name: {app[2]}")
            else:
                print("   ⚠️  applications 表中没有数据")
            
            print("\n✓ 修复完成！")
            print("\n提示：现在可以通过 Web UI 添加分类数据了")
            
        except Exception as e:
            print(f"\n✗ 修复失败: {e}")
            import traceback
            traceback.print_exc()
            await session.rollback()
            raise


if __name__ == "__main__":
    print("=" * 60)
    print("修复全局约束并重新创建 intent_categories 表")
    print("=" * 60)
    
    try:
        asyncio.run(fix_constraint())
        print("\n✓ 修复成功！")
    except Exception as e:
        print(f"\n✗ 修复失败: {e}")
        sys.exit(1)
