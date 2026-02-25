"""数据库迁移脚本：添加规则策略配置字段和规则启用控制字段。"""
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
            # 1. 为 applications 表添加规则策略配置字段
            print("1. 检查并添加 applications 表的字段...")
            
            columns_to_add = [
                ('enable_keyword', 'BOOLEAN DEFAULT TRUE'),
                ('enable_regex', 'BOOLEAN DEFAULT TRUE'),
                ('enable_semantic', 'BOOLEAN DEFAULT TRUE'),
                ('enable_llm_fallback', 'BOOLEAN DEFAULT FALSE'),
            ]
            
            for column_name, column_def in columns_to_add:
                check_query = text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'applications' 
                    AND column_name = :column_name
                """)
                result = await session.execute(check_query, {"column_name": column_name})
                column_exists = result.scalar() is not None
                
                if not column_exists:
                    print(f"   - 添加 {column_name} 字段...")
                    alter_query = text(f"""
                        ALTER TABLE applications 
                        ADD COLUMN {column_name} {column_def}
                    """)
                    await session.execute(alter_query)
                    print(f"     ✓ {column_name} 字段添加成功")
                else:
                    print(f"   - {column_name} 字段已存在，跳过")
            
            # 2. 为 intent_rules 表添加 enabled 字段
            print("\n2. 检查并添加 intent_rules 表的字段...")
            
            check_enabled = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'intent_rules' 
                AND column_name = 'enabled'
            """)
            result = await session.execute(check_enabled)
            enabled_exists = result.scalar() is not None
            
            if not enabled_exists:
                print("   - 添加 enabled 字段...")
                alter_query = text("""
                    ALTER TABLE intent_rules 
                    ADD COLUMN enabled BOOLEAN DEFAULT TRUE
                """)
                await session.execute(alter_query)
                print("     ✓ enabled 字段添加成功")
            else:
                print("   - enabled 字段已存在，跳过")
            
            # 3. 同步现有数据的 enabled 字段（与 is_active 保持一致）
            print("\n3. 同步 intent_rules 表的 enabled 字段...")
            update_query = text("""
                UPDATE intent_rules 
                SET enabled = is_active 
                WHERE enabled IS NULL OR enabled != is_active
            """)
            result = await session.execute(update_query)
            updated_count = result.rowcount
            if updated_count > 0:
                print(f"   ✓ 已同步 {updated_count} 条规则的 enabled 字段")
            else:
                print("   - 无需同步数据")
            
            await session.commit()
            print("\n" + "=" * 60)
            print("✓ 数据库迁移完成！")
            print("=" * 60)
            
        except Exception as e:
            print(f"\n✗ 迁移失败: {e}")
            import traceback
            traceback.print_exc()
            await session.rollback()
            raise


async def verify_migration():
    """验证迁移结果。"""
    async with async_session_maker() as session:
        try:
            print("\n验证迁移结果...")
            
            # 验证 applications 表
            print("\napplications 表字段:")
            result = await session.execute(text("""
                SELECT column_name, data_type, column_default
                FROM information_schema.columns
                WHERE table_name = 'applications'
                AND column_name IN ('enable_keyword', 'enable_regex', 'enable_semantic', 'enable_llm_fallback')
                ORDER BY column_name
            """))
            columns = result.fetchall()
            for col in columns:
                print(f"  - {col[0]}: {col[1]} (default: {col[2]})")
            
            # 验证 intent_rules 表
            print("\nintent_rules 表字段:")
            result = await session.execute(text("""
                SELECT column_name, data_type, column_default
                FROM information_schema.columns
                WHERE table_name = 'intent_rules'
                AND column_name = 'enabled'
            """))
            columns = result.fetchall()
            for col in columns:
                print(f"  - {col[0]}: {col[1]} (default: {col[2]})")
            
            # 检查现有数据
            print("\n数据统计:")
            result = await session.execute(text("""
                SELECT COUNT(*) FROM applications
            """))
            app_count = result.scalar()
            print(f"  - applications 表记录数: {app_count}")
            
            result = await session.execute(text("""
                SELECT COUNT(*) FROM intent_rules
            """))
            rule_count = result.scalar()
            print(f"  - intent_rules 表记录数: {rule_count}")
            
        except Exception as e:
            print(f"\n✗ 验证失败: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    print("=" * 60)
    print("数据库迁移脚本：规则策略配置字段")
    print("=" * 60)
    print("\n本次迁移将添加以下字段:")
    print("  - applications 表:")
    print("    * enable_keyword (BOOLEAN DEFAULT TRUE)")
    print("    * enable_regex (BOOLEAN DEFAULT TRUE)")
    print("    * enable_semantic (BOOLEAN DEFAULT TRUE)")
    print("    * enable_llm_fallback (BOOLEAN DEFAULT FALSE)")
    print("  - intent_rules 表:")
    print("    * enabled (BOOLEAN DEFAULT TRUE)")
    print("=" * 60)
    
    try:
        asyncio.run(migrate())
        asyncio.run(verify_migration())
        print("\n✓ 迁移成功！")
    except Exception as e:
        print(f"\n✗ 迁移失败: {e}")
        sys.exit(1)
