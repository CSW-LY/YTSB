"""验证表结构。"""
import asyncio
import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from sqlalchemy import text
from app.db import async_session_maker


async def verify():
    """验证表结构。"""
    async with async_session_maker() as session:
        try:
            # 检查表是否存在
            print("1. 检查 intent_categories 表...")
            result = await session.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'intent_categories'
                );
            """))
            table_exists = result.scalar()
            
            if table_exists:
                print("   ✓ intent_categories 表存在")
                
                # 检查列
                print("\n2. 检查表结构...")
                result = await session.execute(text("""
                    SELECT column_name, data_type, is_nullable, column_default
                    FROM information_schema.columns
                    WHERE table_name = 'intent_categories'
                    ORDER BY ordinal_position;
                """))
                columns = result.fetchall()
                
                print("   列结构:")
                for col in columns:
                    nullable = "NULL" if col[2] == "YES" else "NOT NULL"
                    default = f" DEFAULT {col[3]}" if col[3] else ""
                    print(f"     - {col[0]}: {col[1]} {nullable}{default}")
                
                # 检查约束
                print("\n3. 检查约束...")
                result = await session.execute(text("""
                    SELECT conname as constraint_name, contype as constraint_type
                    FROM pg_constraint
                    WHERE conrelid = 'intent_categories'::regclass
                    ORDER BY conname;
                """))
                constraints = result.fetchall()
                
                if constraints:
                    print("   约束:")
                    for con in constraints:
                        type_map = {'c': '检查', 'f': '外键', 'p': '主键', 'u': '唯一'}
                        type_str = type_map.get(con[1], con[1])
                        print(f"     - {con[0]} ({type_str})")
                else:
                    print("   无约束")
                
                # 检查数据
                print("\n4. 检查数据...")
                result = await session.execute(text("SELECT COUNT(*) FROM intent_categories;"))
                count = result.scalar()
                print(f"   当前有 {count} 条分类数据")
                
                if count > 0:
                    result = await session.execute(text("""
                        SELECT id, application_id, code, name, is_active
                        FROM intent_categories
                        ORDER BY id;
                    """))
                    categories = result.fetchall()
                    print("\n   分类列表:")
                    for cat in categories:
                        status = "激活" if cat[4] else "停用"
                        print(f"     - ID: {cat[0]}, 应用ID: {cat[1]}, 代码: {cat[2]}, 名称: {cat[3]}, 状态: {status}")
            else:
                print("   ✗ intent_categories 表不存在")
            
            print("\n✓ 验证完成！")
            
        except Exception as e:
            print(f"\n✗ 验证失败: {e}")
            import traceback
            traceback.print_exc()
            raise


if __name__ == "__main__":
    print("=" * 60)
    print("验证 intent_categories 表结构")
    print("=" * 60)
    
    try:
        asyncio.run(verify())
        print("\n✓ 验证成功！")
    except Exception as e:
        print(f"\n✗ 验证失败: {e}")
        sys.exit(1)
