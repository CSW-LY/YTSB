"""运行数据库迁移（修复版）。"""
import asyncio
import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from sqlalchemy import text
from app.db import async_session_maker


async def migrate():
    """执行迁移。"""
    async with async_session_maker() as session:
        try:
            # 1. 创建新表
            print("1. 创建 applications 表...")
            await session.execute(text("""
                CREATE TABLE IF NOT EXISTS applications (
                    id SERIAL PRIMARY KEY,
                    app_key VARCHAR(100) UNIQUE NOT NULL,
                    name VARCHAR(200) NOT NULL,
                    description TEXT,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """))
            
            # 2. 添加外键
            print("2. 添加外键到 intent_categories 表...")
            await session.execute(text("""
                ALTER TABLE intent_categories 
                ADD COLUMN IF NOT EXISTS application_id INTEGER 
                REFERENCES applications(id) ON DELETE CASCADE;
            """))
            
            print("3. 添加外键到 app_intents 表...")
            await session.execute(text("""
                ALTER TABLE app_intents 
                ADD COLUMN IF NOT EXISTS application_id INTEGER 
                REFERENCES applications(id) ON DELETE CASCADE;
            """))
            
            # 3. 创建复合唯一约束
            print("4. 创建复合唯一约束...")
            await session.execute(text("""
                ALTER TABLE intent_categories 
                DROP CONSTRAINT IF EXISTS uq_application_category_code;
            """))
            await session.execute(text("""
                ALTER TABLE intent_categories 
                ADD CONSTRAINT uq_application_category_code 
                UNIQUE (application_id, code);
            """))
            
            # 4. 迁移数据
            print("5. 迁移应用配置到 applications 表...")
            result = await session.execute(text("""
                INSERT INTO applications (app_key, name, description, is_active)
                SELECT DISTINCT 
                    COALESCE(ai.app_key, 'default_app') as app_key,
                    'Migrated Application' as name,
                    'Application created from migration' as description,
                    true as is_active
                FROM app_intents ai
                WHERE NOT EXISTS (
                    SELECT 1 FROM applications a WHERE a.app_key = ai.app_key
                )
                RETURNING id, app_key;
            """))
            migrated_apps = result.fetchall()
            print(f"   迁移了 {len(migrated_apps)} 个应用:")
            for app in migrated_apps:
                print(f"      - ID={app[0]}, app_key={app[1]}")
            
            print("6. 迁移分类到应用...")
            result = await session.execute(text("""
                UPDATE intent_categories ic
                SET application_id = (
                    SELECT a.id 
                    FROM applications a 
                    JOIN app_intents ai ON a.app_key = ai.app_key
                    WHERE ai.intent_ids @> ARRAY[ic.id]
                    LIMIT 1
                )
                WHERE ic.application_id IS NULL
                RETURNING id, application_id;
            """))
            migrated_categories = result.fetchall()
            print(f"   迁移了 {len(migrated_categories)} 个分类")
            
            # 检查还有多少分类没有 application_id
            result = await session.execute(text("""
                SELECT COUNT(*) FROM intent_categories WHERE application_id IS NULL;
            """))
            null_count = result.scalar()
            if null_count > 0:
                print(f"   警告: 还有 {null_count} 个分类没有 application_id")
                print("   为这些分类创建默认应用...")
                
                # 创建默认应用
                result = await session.execute(text("""
                    INSERT INTO applications (app_key, name, description, is_active)
                    VALUES ('default_app', 'Default Application', 'Default application for unmigrated categories', true)
                    ON CONFLICT (app_key) DO NOTHING
                    RETURNING id;
                """))
                default_app_id = result.scalar()
                print(f"   默认应用 ID: {default_app_id}")
                
                # 将剩余分类分配给默认应用
                result = await session.execute(text("""
                    UPDATE intent_categories 
                    SET application_id = :app_id
                    WHERE application_id IS NULL
                    RETURNING id;
                """), {"app_id": default_app_id})
                updated_count = len(result.fetchall())
                print(f"   更新了 {updated_count} 个分类到默认应用")
            
            print("7. 迁移应用配置...")
            result = await session.execute(text("""
                UPDATE app_intents ai
                SET application_id = (
                    SELECT a.id 
                    FROM applications a 
                    WHERE a.app_key = ai.app_key
                )
                WHERE ai.application_id IS NULL
                RETURNING id, application_id;
            """))
            migrated_app_intents = result.fetchall()
            print(f"   迁移了 {len(migrated_app_intents)} 个应用配置")
            
            # 5. 设置非空约束
            print("8. 设置非空约束...")
            await session.execute(text("""
                ALTER TABLE intent_categories 
                ALTER COLUMN application_id SET NOT NULL;
            """))
            
            await session.execute(text("""
                ALTER TABLE app_intents 
                ALTER COLUMN application_id SET NOT NULL;
            """))
            
            # 6. 删除旧约束
            print("9. 删除旧的唯一约束...")
            await session.execute(text("""
                ALTER TABLE intent_categories 
                DROP CONSTRAINT IF EXISTS intent_categories_code_key;
            """))
            
            await session.commit()
            print("\n✓ 数据库迁移完成！")
            
        except Exception as e:
            print(f"\n✗ 迁移失败: {e}")
            import traceback
            traceback.print_exc()
            await session.rollback()
            raise


if __name__ == "__main__":
    print("=" * 60)
    print("数据库迁移脚本（修复版）")
    print("=" * 60)
    
    try:
        asyncio.run(migrate())
        print("\n✓ 迁移成功！")
    except Exception as e:
        print(f"\n✗ 迁移失败: {e}")
        sys.exit(1)
