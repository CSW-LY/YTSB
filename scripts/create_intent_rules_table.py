"""创建 intent_rules 表。"""
import asyncio
import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from sqlalchemy import text
from app.db import async_session_maker


async def create_rules_table():
    """创建规则表。"""
    async with async_session_maker() as session:
        try:
            # 检查表是否存在
            print("1. 检查 intent_rules 表...")
            result = await session.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'intent_rules'
                );
            """))
            table_exists = result.scalar()
            
            if table_exists:
                print("   ✓ intent_rules 表已存在")
                return
            
            # 创建表
            print("2. 创建 intent_rules 表...")
            await session.execute(text("""
                CREATE TABLE intent_rules (
                    id SERIAL PRIMARY KEY,
                    category_id INTEGER NOT NULL,
                    rule_type VARCHAR(20) NOT NULL,
                    content TEXT NOT NULL,
                    weight FLOAT DEFAULT 1.0,
                    rule_metadata TEXT,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    CONSTRAINT fk_category 
                        FOREIGN KEY (category_id) 
                        REFERENCES intent_categories(id) 
                        ON DELETE CASCADE
                );
            """))
            
            # 创建索引
            print("3. 创建索引...")
            await session.execute(text("""
                CREATE INDEX idx_intent_rules_category_id 
                ON intent_rules(category_id);
            """))
            
            await session.execute(text("""
                CREATE INDEX idx_intent_rules_rule_type 
                ON intent_rules(rule_type);
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
                CREATE TRIGGER update_intent_rules_updated_at
                    BEFORE UPDATE ON intent_rules
                    FOR EACH ROW
                    EXECUTE FUNCTION update_updated_at_column();
            """))
            
            await session.commit()
            print("\n✓ intent_rules 表创建成功！")
            
        except Exception as e:
            print(f"\n✗ 创建失败: {e}")
            import traceback
            traceback.print_exc()
            await session.rollback()
            raise


if __name__ == "__main__":
    print("=" * 60)
    print("创建 intent_rules 表")
    print("=" * 60)
    
    try:
        asyncio.run(create_rules_table())
        print("\n✓ 创建成功！")
    except Exception as e:
        print(f"\n✗ 创建失败: {e}")
        sys.exit(1)
