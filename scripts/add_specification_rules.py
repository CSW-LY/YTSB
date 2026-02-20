"""添加规格相关的规则。"""
import asyncio
import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from sqlalchemy import text
from app.db import async_session_maker


# 规格相关的规则
SPECIFICATION_RULES = [
    {
        "category_code": "SEARCH_PART",
        "rule_type": "keyword",
        "content": "规格,spec,specification",
        "weight": 0.9,
        "description": "零件规格相关关键词"
    },
    {
        "category_code": "SEARCH_PART",
        "rule_type": "regex",
        "content": r"(查找|搜索|查询|找).*规格.*(为|是)\s*([a-zA-Z0-9]+)",
        "weight": 1.0,
        "description": "查找规格为X的零件"
    },
    {
        "category_code": "SEARCH_DRAWING",
        "rule_type": "keyword",
        "content": "规格,spec,specification",
        "weight": 0.9,
        "description": "图纸规格相关关键词"
    },
    {
        "category_code": "SEARCH_DRAWING",
        "rule_type": "regex",
        "content": r"(查找|搜索|查询|找).*规格.*(为|是)\s*([a-zA-Z0-9]+)",
        "weight": 1.0,
        "description": "查找规格为X的图纸"
    },
    {
        "category_code": "SEARCH_PART",
        "rule_type": "semantic",
        "content": "这个零件的规格是什么",
        "weight": 1.0,
        "description": "查询零件规格的语义示例"
    },
    {
        "category_code": "SEARCH_PART",
        "rule_type": "semantic",
        "content": "规格是X的零件",
        "weight": 1.0,
        "description": "规格相关零件查询的语义示例"
    },
    {
        "category_code": "SEARCH_DRAWING",
        "rule_type": "semantic",
        "content": "这个图纸的规格是多少",
        "weight": 1.0,
        "description": "查询图纸规格的语义示例"
    },
]


async def add_specification_rules():
    """添加规格相关规则。"""
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
            
            # 获取所有分类
            print(f"\n2. 获取分类列表...")
            result = await session.execute(text("""
                SELECT id, code, name FROM intent_categories 
                WHERE application_id = :app_id 
                ORDER BY code;
            """), {"app_id": application_id})
            
            categories = result.fetchall()
            category_map = {cat[1]: cat[0] for cat in categories}
            
            print(f"   找到 {len(categories)} 个分类")
            
            # 添加规则
            print(f"\n3. 添加规格相关规则...")
            inserted_count = 0
            skipped_count = 0
            
            for rule_data in SPECIFICATION_RULES:
                category_code = rule_data["category_code"]
                
                # 检查分类是否存在
                if category_code not in category_map:
                    print(f"   ⚠️  分类 {category_code} 不存在，跳过")
                    skipped_count += 1
                    continue
                
                category_id = category_map[category_code]
                
                # 检查规则是否已存在
                result = await session.execute(text("""
                    SELECT id FROM intent_rules 
                    WHERE category_id = :category_id 
                    AND rule_type = :rule_type 
                    AND content = :content;
                """), {
                    "category_id": category_id,
                    "rule_type": rule_data["rule_type"],
                    "content": rule_data["content"]
                })
                
                existing = result.fetchone()
                
                if existing:
                    print(f"   - {category_code}: {rule_data['description']} (已存在，跳过)")
                    skipped_count += 1
                    continue
                
                # 插入新规则
                await session.execute(text("""
                    INSERT INTO intent_rules 
                    (category_id, rule_type, content, weight, is_active)
                    VALUES (:category_id, :rule_type, :content, :weight, true);
                """), {
                    "category_id": category_id,
                    "rule_type": rule_data["rule_type"],
                    "content": rule_data["content"],
                    "weight": rule_data["weight"]
                })
                
                inserted_count += 1
                print(f"   ✓ {category_code}: {rule_data['description']}")
            
            await session.commit()
            print(f"\n✓ 成功添加 {inserted_count} 条规则，跳过 {skipped_count} 条！")
            
            # 显示统计
            print(f"\n4. 查看规则统计...")
            result = await session.execute(text("""
                SELECT 
                    ic.code,
                    ic.name,
                    ir.rule_type,
                    COUNT(*) as rule_count
                FROM intent_rules ir
                JOIN intent_categories ic ON ir.category_id = ic.id
                WHERE ic.application_id = :app_id
                GROUP BY ic.code, ic.name, ir.rule_type
                ORDER BY ic.code, ir.rule_type;
            """), {"app_id": application_id})
            
            rules_stats = result.fetchall()
            
            if rules_stats:
                type_name_map = {'keyword': '关键词', 'regex': '正则表达式', 'semantic': '语义'}
                print(f"\n   规则统计:")
                for stat in rules_stats:
                    type_str = type_name_map.get(stat[2], stat[2])
                    print(f"     - {stat[1]} ({stat[0]}): {type_str} - {stat[3]} 条")
            
            print("\n✓ 完成！")
            print("\n提示：现在可以测试 '找规格为56476的零部件' 等查询了")
            
        except Exception as e:
            print(f"\n✗ 添加规则失败: {e}")
            import traceback
            traceback.print_exc()
            await session.rollback()
            raise


if __name__ == "__main__":
    print("=" * 60)
    print("添加规格相关的规则")
    print("=" * 60)
    
    try:
        asyncio.run(add_specification_rules())
        print("\n✓ 添加成功！")
    except Exception as e:
        print(f"\n✗ 添加失败: {e}")
        sys.exit(1)
