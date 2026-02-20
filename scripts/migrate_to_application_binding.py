"""迁移脚本：将现有数据迁移到应用绑定架构。"""
import asyncio
import logging
from sqlalchemy import text
from app.db import async_session_maker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def migrate():
    """执行迁移。"""
    async with async_session_maker() as session:
        try:
            # 1. 创建新表
            logger.info("创建 applications 表...")
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
            logger.info("添加外键到 intent_categories 表...")
            await session.execute(text("""
                ALTER TABLE intent_categories 
                ADD COLUMN IF NOT EXISTS application_id INTEGER 
                REFERENCES applications(id) ON DELETE CASCADE;
            """))
            
            logger.info("添加外键到 app_intents 表...")
            await session.execute(text("""
                ALTER TABLE app_intents 
                ADD COLUMN IF NOT EXISTS application_id INTEGER 
                REFERENCES applications(id) ON DELETE CASCADE;
            """))
            
            # 3. 创建复合唯一约束
            logger.info("创建复合唯一约束...")
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
            logger.info("迁移应用配置到 applications 表...")
            await session.execute(text("""
                INSERT INTO applications (app_key, name, description, is_active)
                SELECT DISTINCT 
                    COALESCE(ai.app_key, 'default_app') as app_key,
                    'Migrated Application' as name,
                    'Application created from migration' as description,
                    true as is_active
                FROM app_intents ai
                WHERE NOT EXISTS (
                    SELECT 1 FROM applications a WHERE a.app_key = ai.app_key
                );
            """))
            
            logger.info("迁移分类到应用...")
            await session.execute(text("""
                UPDATE intent_categories ic
                SET application_id = (
                    SELECT a.id 
                    FROM applications a 
                    JOIN app_intents ai ON a.app_key = ai.app_key
                    WHERE ai.intent_ids @> ARRAY[ic.id]
                    LIMIT 1
                )
                WHERE ic.application_id IS NULL;
            """))
            
            logger.info("迁移应用配置...")
            await session.execute(text("""
                UPDATE app_intents ai
                SET application_id = (
                    SELECT a.id 
                    FROM applications a 
                    WHERE a.app_key = ai.app_key
                )
                WHERE ai.application_id IS NULL;
            """))
            
            # 5. 设置非空约束
            logger.info("设置非空约束...")
            await session.execute(text("""
                ALTER TABLE intent_categories 
                ALTER COLUMN application_id SET NOT NULL;
            """))
            
            await session.execute(text("""
                ALTER TABLE app_intents 
                ALTER COLUMN application_id SET NOT NULL;
            """))
            
            # 6. 删除旧约束
            logger.info("删除旧的唯一约束...")
            await session.execute(text("""
                ALTER TABLE intent_categories 
                DROP CONSTRAINT IF EXISTS intent_categories_code_key;
            """))
            
            await session.commit()
            logger.info("迁移完成！")
            
        except Exception as e:
            logger.error(f"迁移失败: {e}")
            await session.rollback()
            raise

if __name__ == "__main__":
    asyncio.run(migrate())
