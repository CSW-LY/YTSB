"""添加针对图号的语义规则。"""
import asyncio
import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from sqlalchemy import text
from app.db import async_session_maker


# 针对图号的语义规则
DRAWING_NUMBER_RULES = [
    "我想查看图号",
    "帮我查看图号",
    "图号是什么",
    "显示图号信息",
    "帮我看看图号",
    "查询图号",
    "图号查询",
    "查一下图号",
    "帮我查图号",
    "这个图号是",
    "图号是多少",
    "查看图号资料",
    "帮我查看图号资料",
    "图号相关",
    "查看图号和零部件",
    "帮我看看图号零部件资料",
    "图号零部件资料",
    "查询图号零部件资料",
]


async def add_drawing_number_rules():
    """添加图号相关的语义规则。"""
    async with async_session_maker() as session:
        try:
            # 查找 PLM 应用
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
            
            # 查找"搜索图纸"分类
            print(f"\n2. 查找'搜索图纸'分类...")
            result = await session.execute(text("""
                SELECT id, code, name FROM intent_categories 
                WHERE application_id = :app_id AND code = 'SEARCH_DRAWING';
            """), {"app_id": application_id})
            
            category = result.fetchone()
            
            if not category:
                print("   ⚠️  未找到'搜索图纸'分类")
                return
            
            category_id = category[0]
            print(f"   ✓ 找到分类: {category[2]} (ID: {category_id})")
            
            # 检查现有规则
            print(f"\n3. 检查现有规则...")
            result = await session.execute(text("""
                SELECT COUNT(*) FROM intent_rules 
                WHERE category_id = :category_id AND rule_type = 'semantic';
            """), {"category_id": category_id})
            
            existing_count = result.scalar()
            print(f"   现有 {existing_count} 条语义规则")
            
            # 添加新规则
            print(f"\n4. 添加图号相关语义规则...")
            inserted_count = 0
            skipped_count = 0
            
            for example in DRAWING_NUMBER_RULES:
                # 检查规则是否已存在
                result = await session.execute(text("""
                    SELECT id FROM intent_rules 
                    WHERE category_id = :category_id 
                    AND rule_type = 'semantic' 
                    AND content = :content;
                """), {
                    "category_id": category_id,
                    "content": example
                })
                
                existing = result.fetchone()
                
                if existing:
                    print(f"   - {example[:30]}... (已存在，跳过)")
                    skipped_count += 1
                    continue
                
                # 插入新规则
                await session.execute(text("""
                    INSERT INTO intent_rules 
                    (category_id, rule_type, content, weight, is_active)
                    VALUES (:category_id, 'semantic', :content, 1.0, true);
                """), {
                    "category_id": category_id,
                    "content": example
                })
                
                inserted_count += 1
                print(f"   ✓ {example[:30]}...")
            
            await session.commit()
            print(f"\n✓ 成功添加 {inserted_count} 条规则，跳过 {skipped_count} 条！")
            
            # 显示统计
            print(f"\n5. 查看统计...")
            result = await session.execute(text("""
                SELECT COUNT(*) FROM intent_rules 
                WHERE category_id = :category_id AND rule_type = 'semantic';
            """), {"category_id": category_id})
            
            total_count = result.scalar()
            print(f"   '搜索图纸'分类现在有 {total_count} 条语义规则")
            
            print("\n✓ 完成！")
            print("\n提示：现在可以通过 Web UI 测试图号相关查询了")
            
        except Exception as e:
            print(f"\n✗ 添加规则失败: {e}")
            import traceback
            traceback.print_exc()
            await session.rollback()
            raise


if __name__ == "__main__":
    print("=" * 60)
    print("添加图号相关的语义规则")
    print("=" * 60)
    
    try:
        asyncio.run(add_drawing_number_rules())
        print("\n✓ 添加成功！")
    except Exception as e:
        print(f"\n✗ 添加失败: {e}")
        sys.exit(1)
