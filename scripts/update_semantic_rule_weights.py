"""更新语义规则权重。"""
import asyncio
import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from sqlalchemy import text
from app.db import async_session_maker


async def update_weights():
    """更新语义规则权重为 1.0。"""
    async with async_session_maker() as session:
        try:
            # 查找 PLM 应用的 ID
            print("1. 查找 PLM 应用...")
            result = await session.execute(text("""
                SELECT id, app_key, name 
                FROM applications 
                WHERE app_key = :app_key;
            """), {"app_key": "plm_assistant"})
            
            app = result.fetchone()
            
            if not app:
                print("   ⚠️  未找到 PLM 应用")
                return
            
            application_id = app[0]
            print(f"   ✓ 找到 PLM 应用: {app[2]} (ID: {application_id})")
            
            # 更新所有语义规则的权重
            print(f"\n2. 更新语义规则权重...")
            result = await session.execute(text("""
                UPDATE intent_rules 
                SET weight = 1.0 
                WHERE id IN (
                    SELECT ir.id 
                    FROM intent_rules ir
                    JOIN intent_categories ic ON ir.category_id = ic.id
                    WHERE ic.application_id = :app_id 
                    AND ir.rule_type = 'semantic'
                    AND ir.is_active = true
                );
            """), {"app_id": application_id})
            
            updated_count = result.rowcount
            print(f"   ✓ 已更新 {updated_count} 条语义规则的权重")
            
            # 验证更新
            print(f"\n3. 验证更新结果...")
            result = await session.execute(text("""
                SELECT COUNT(*) as count,
                       AVG(weight) as avg_weight
                FROM intent_rules ir
                JOIN intent_categories ic ON ir.category_id = ic.id
                WHERE ic.application_id = :app_id 
                AND ir.rule_type = 'semantic'
                AND ir.is_active = true;
            """), {"app_id": application_id})
            
            stats = result.fetchone()
            print(f"   语义规则数量: {stats[0]}")
            print(f"   平均权重: {stats[1]:.2f}")
            
            await session.commit()
            print("\n✓ 更新完成！")
            
        except Exception as e:
            print(f"\n✗ 更新失败: {e}")
            import traceback
            traceback.print_exc()
            await session.rollback()
            raise


if __name__ == "__main__":
    print("=" * 60)
    print("更新语义规则权重")
    print("=" * 60)
    
    try:
        asyncio.run(update_weights())
        print("\n✓ 更新成功！")
    except Exception as e:
        print(f"\n✗ 更新失败: {e}")
        sys.exit(1)
