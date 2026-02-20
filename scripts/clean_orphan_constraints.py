"""清理残留的约束。"""
import asyncio
import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from sqlalchemy import text
from app.db import async_session_maker


async def clean_constraints():
    """清理残留约束。"""
    async with async_session_maker() as session:
        try:
            # 查找所有约束
            print("1. 查找所有约束...")
            result = await session.execute(text("""
                SELECT 
                    conname as constraint_name,
                    conrelid::regclass as table_name
                FROM pg_constraint
                WHERE conname LIKE '%intent_category%'
                ORDER BY conname;
            """))
            constraints = result.fetchall()
            
            if constraints:
                print(f"   找到 {len(constraints)} 个约束:")
                for constraint in constraints:
                    print(f"     - {constraint[0]} (表: {constraint[1]})")
                
                # 删除所有相关约束
                print("\n2. 删除所有相关约束...")
                for constraint in constraints:
                    constraint_name = constraint[0]
                    try:
                        await session.execute(text(f"""
                            DROP CONSTRAINT IF EXISTS {constraint_name};
                        """))
                        await session.commit()
                        print(f"   ✓ 删除约束: {constraint_name}")
                    except Exception as e:
                        print(f"   ✗ 删除约束失败 {constraint_name}: {e}")
                        await session.rollback()
            else:
                print("   未找到相关约束")
            
            # 删除表
            print("\n3. 删除表...")
            await session.execute(text("DROP TABLE IF EXISTS intent_rules CASCADE;"))
            await session.execute(text("DROP TABLE IF EXISTS intent_categories CASCADE;"))
            await session.commit()
            print("   ✓ 删除表成功")
            
            print("\n✓ 清理完成！")
            
        except Exception as e:
            print(f"\n✗ 清理失败: {e}")
            import traceback
            traceback.print_exc()
            await session.rollback()
            raise


async def create_table():
    """创建表。"""
    async with async_session_maker() as session:
        try:
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
            
            print("5. 创建唯一约束...")
            await session.execute(text("""
                ALTER TABLE intent_categories 
                ADD CONSTRAINT uq_application_category_code 
                UNIQUE (application_id, code);
            """))
            
            print("6. 创建索引...")
            await session.execute(text("""
                CREATE INDEX idx_intent_categories_application_id 
                ON intent_categories(application_id);
            """))
            
            await session.execute(text("""
                CREATE INDEX idx_intent_categories_code 
                ON intent_categories(code);
            """))
            
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
            
            print("\n✓ 恢复完成！")
            print("\n提示：现在可以通过 Web UI 添加分类数据了")
            
        except Exception as e:
            print(f"\n✗ 创建表失败: {e}")
            import traceback
            traceback.print_exc()
            await session.rollback()
            raise


if __name__ == "__main__":
    print("=" * 60)
    print("清理残留约束并重新创建 intent_categories 表")
    print("=" * 60)
    
    try:
        asyncio.run(clean_constraints())
        asyncio.run(create_table())
        print("\n✓ 恢复成功！")
    except Exception as e:
        print(f"\n✗ 恢复失败: {e}")
        sys.exit(1)
