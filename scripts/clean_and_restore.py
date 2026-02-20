"""清理并重新创建 intent_categories 表。"""
import asyncio
import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from sqlalchemy import text
from app.db import async_session_maker


async def clean_and_restore():
    """清理并重建分类表。"""
    async with async_session_maker() as session:
        try:
            # 删除所有相关对象
            print("1. 删除所有相关对象...")
            
            # 删除触发器
            await session.execute(text("""
                DROP TRIGGER IF EXISTS update_intent_categories_updated_at 
                ON intent_categories;
            """))
            
            # 删除函数
            await session.execute(text("""
                DROP FUNCTION IF EXISTS update_updated_at_column();
            """))
            
            # 删除索引
            await session.execute(text("""
                DROP INDEX IF EXISTS idx_intent_categories_application_id;
            """))
            
            await session.execute(text("""
                DROP INDEX IF EXISTS idx_intent_categories_code;
            """))
            
            # 删除外键约束
            await session.execute(text("""
                ALTER TABLE intent_categories 
                DROP CONSTRAINT IF EXISTS fk_application;
            """))
            
            # 删除唯一约束
            await session.execute(text("""
                ALTER TABLE intent_categories 
                DROP CONSTRAINT IF EXISTS uq_application_category_code;
            """))
            
            # 删除表
            await session.execute(text("DROP TABLE IF EXISTS intent_rules CASCADE;"))
            await session.execute(text("DROP TABLE IF EXISTS intent_categories CASCADE;"))
            
            await session.commit()
            print("   ✓ 清理完成")
            
            # 创建表
            print("\n2. 创建 intent_categories 表...")
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
                        ON DELETE CASCADE,
                    CONSTRAINT uq_application_category_code 
                        UNIQUE (application_id, code)
                );
            """))
            
            # 创建索引
            print("3. 创建索引...")
            await session.execute(text("""
                CREATE INDEX idx_intent_categories_application_id 
                ON intent_categories(application_id);
            """))
            
            await session.execute(text("""
                CREATE INDEX idx_intent_categories_code 
                ON intent_categories(code);
            """))
            
            # 创建触发器函数
            print("4. 创建触发器函数...")
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
            print("5. 创建触发器...")
            await session.execute(text("""
                DROP TRIGGER IF EXISTS update_intent_categories_updated_at 
                ON intent_categories;
            """))
            
            await session.execute(text("""
                CREATE TRIGGER update_intent_categories_updated_at
                    BEFORE UPDATE ON intent_categories
                    FOR EACH ROW
                    EXECUTE FUNCTION update_updated_at_column();
            """))
            
            await session.commit()
            print("   ✓ intent_categories 表创建成功！")
            
            # 检查 applications 表
            print("\n6. 检查 applications 表...")
            result = await session.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'applications'
                );
            """))
            apps_exist = result.scalar()
            
            if apps_exist:
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
            else:
                print("   ⚠️  applications 表不存在")
            
            print("\n✓ 恢复完成！")
            print("\n提示：请通过 Web UI 添加分类数据")
            
        except Exception as e:
            print(f"\n✗ 恢复失败: {e}")
            import traceback
            traceback.print_exc()
            await session.rollback()
            raise


if __name__ == "__main__":
    print("=" * 60)
    print("清理并重新创建 intent_categories 表")
    print("=" * 60)
    
    try:
        asyncio.run(clean_and_restore())
        print("\n✓ 恢复成功！")
    except Exception as e:
        print(f"\n✗ 恢复失败: {e}")
        sys.exit(1)
