"""恢复 intent_categories 表。"""
import asyncio
import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from sqlalchemy import text
from app.db import async_session_maker


async def restore_categories_table():
    """恢复分类表结构。"""
    async with async_session_maker() as session:
        try:
            # 检查表是否存在
            print("检查表是否存在...")
            result = await session.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'intent_categories'
                );
            """))
            table_exists = result.scalar()
            
            if table_exists:
                print("⚠️  intent_categories 表已存在")
                choice = input("是否要删除并重建？这将清空所有数据！(y/n): ")
                if choice.lower() != 'y':
                    print("操作取消")
                    return
                
                print("删除现有表和约束...")
                # 先删除外键依赖的表
                await session.execute(text("DROP TABLE IF EXISTS intent_rules CASCADE;"))
                await session.execute(text("DROP TABLE IF EXISTS intent_categories CASCADE;"))
                await session.commit()
            
            # 创建表
            print("\n创建 intent_categories 表...")
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
            print("创建索引...")
            await session.execute(text("""
                CREATE INDEX idx_intent_categories_application_id 
                ON intent_categories(application_id);
            """))
            
            await session.execute(text("""
                CREATE INDEX idx_intent_categories_code 
                ON intent_categories(code);
            """))
            
            # 创建触发器用于更新 updated_at
            print("创建触发器...")
            await session.execute(text("""
                CREATE OR REPLACE FUNCTION update_updated_at_column()
                RETURNS TRIGGER AS $$
                BEGIN
                    NEW.updated_at = CURRENT_TIMESTAMP;
                    RETURN NEW;
                END;
                $$ language 'plpgsql';
            """))
            
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
            print("\n✓ intent_categories 表创建成功！")
            
            # 检查是否有 applications 表
            result = await session.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'applications'
                );
            """))
            apps_exist = result.scalar()
            
            if apps_exist:
                result = await session.execute(text("SELECT id, app_key FROM applications;"))
                apps = result.fetchall()
                if apps:
                    print(f"\n可用的应用:")
                    for app in apps:
                        print(f"  - ID: {app[0]}, app_key: {app[1]}")
                    
                    print("\n提示：现在需要为分类数据。请使用 Web UI 添加分类，或者运行数据恢复脚本。")
                else:
                    print("\n⚠️  applications 表中没有数据，请先创建应用")
            else:
                print("\n⚠️  applications 表不存在，请先创建应用")
            
        except Exception as e:
            print(f"\n✗ 恢复失败: {e}")
            import traceback
            traceback.print_exc()
            await session.rollback()
            raise


if __name__ == "__main__":
    print("=" * 60)
    print("恢复 intent_categories 表")
    print("=" * 60)
    
    try:
        asyncio.run(restore_categories_table())
        print("\n✓ 恢复成功！")
    except Exception as e:
        print(f"\n✗ 恢复失败: {e}")
        sys.exit(1)
