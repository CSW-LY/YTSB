"""修复 intent_recognition_logs 外键约束，允许 api_key_id 为 NULL。"""

import asyncio
import os
import sys
from sqlalchemy import text

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from app.db import async_session_maker


async def upgrade():
    """
    升级：删除旧的外键约束，添加允许 NULL 的新约束。
    """
    async with async_session_maker() as session:
        try:
            # 删除旧的外键约束
            await session.execute(text("""
                ALTER TABLE intent_recognition_logs
                DROP CONSTRAINT IF EXISTS intent_recognition_logs_api_key_id_fkey
            """))
            await session.commit()
            print("成功删除旧的外键约束")

            # 添加新的外键约束，允许 NULL
            await session.execute(text("""
                ALTER TABLE intent_recognition_logs
                ADD CONSTRAINT intent_recognition_logs_api_key_id_fkey
                FOREIGN KEY (api_key_id)
                REFERENCES api_keys(id)
                ON DELETE SET NULL
            """))
            await session.commit()
            print("成功添加新的外键约束（允许 NULL）")

            # 验证约束
            result = await session.execute(text("""
                SELECT COUNT(*) FROM intent_recognition_logs WHERE api_key_id IS NULL
            """))
            count = result.scalar()
            print(f"当前有 {count} 条 api_key_id 为 NULL 的记录")

            print("\n✅ 迁移完成！")
            print("- 外键约束已更新为允许 NULL")
            print("- api_key_id 为 NULL 表示未认证的请求")

        except Exception as e:
            await session.rollback()
            print(f"\n❌ 迁移失败: {e}")
            raise


async def downgrade():
    """
    降级：恢复旧的外键约束（不允许 NULL）。
    """
    async with async_session_maker() as session:
        try:
            # 删除新的外键约束
            await session.execute(text("""
                ALTER TABLE intent_recognition_logs
                DROP CONSTRAINT IF EXISTS intent_recognition_logs_api_key_id_fkey
            """))
            await session.commit()
            print("成功删除外键约束")

            # 恢复旧的外键约束（不允许 NULL）
            await session.execute(text("""
                ALTER TABLE intent_recognition_logs
                ADD CONSTRAINT intent_recognition_logs_api_key_id_fkey
                FOREIGN KEY (api_key_id)
                REFERENCES api_keys(id)
            """))
            await session.commit()
            print("成功恢复旧的外键约束（不允许 NULL）")

            print("\n⚠️ 降级完成！")
            print("- 外键约束已恢复为不允许 NULL")
            print("- 这可能导致 api_key_id 为 NULL 的请求失败")

        except Exception as e:
            await session.rollback()
            print(f"\n❌ 降级失败: {e}")
            raise


async def check_constraint():
    """
    检查当前外键约束状态。
    """
    async with async_session_maker() as session:
        result = await session.execute(text("""
            SELECT
                tc.constraint_name,
                tc.is_deferrable,
                tc.initially_deferred,
                ccu.table_name AS foreign_table_name
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage AS ccu
                ON ccu.constraint_name = tc.constraint_name
                AND ccu.table_schema = tc.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY'
                AND tc.table_name = 'intent_recognition_logs'
                AND kcu.column_name = 'api_key_id'
        """))

        constraints = result.fetchall()

        if not constraints:
            print("❌ 未找到外键约束 'intent_recognition_logs_api_key_id_fkey'")
            return False

        for constraint in constraints:
            print(f"\n外键约束信息:")
            print(f"  名称: {constraint[0]}")
            print(f"  可延迟: {constraint[1]}")
            print(f"  初始延迟: {constraint[2]}")
            print(f"  引用表: {constraint[3]}")

        return True


async def main():
    """主函数。"""
    import sys

    if len(sys.argv) < 2:
        print("用法:")
        print("  python fix_api_key_fk_constraint.py <command>")
        print("\n命令:")
        print("  upgrade   - 执行迁移（允许 NULL）")
        print("  downgrade - 回滚迁移（不允许 NULL）")
        print("  check     - 检查当前约束状态")
        return

    command = sys.argv[1]

    if command == "upgrade":
        print("执行升级...")
        await upgrade()
    elif command == "downgrade":
        print("执行降级...")
        await downgrade()
    elif command == "check":
        print("检查约束...")
        await check_constraint()
    else:
        print(f"未知命令: {command}")
        return

    print("\n完成！")


if __name__ == "__main__":
    asyncio.run(main())
