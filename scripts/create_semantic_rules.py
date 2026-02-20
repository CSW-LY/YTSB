"""为 PLM 分类创建语义规则。"""
import asyncio
import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from sqlalchemy import text
from app.db import async_session_maker


# PLM 语义规则数据
PLM_SEMANTIC_RULES = [
    # 查找零件
    {
        "category_code": "SEARCH_PART",
        "examples": [
            "我想查一下这个零件的信息",
            "帮我找个零件，编号是 P-001",
            "这个零件叫什么名字？",
            "查一下部件的详细信息",
            "我想了解这个零件的情况",
            "帮我查询零件资料",
            "这个零件的规格是什么？"
        ]
    },
    
    # 搜索图纸
    {
        "category_code": "SEARCH_DRAWING",
        "examples": [
            "我需要看产品的图纸",
            "帮我找一下技术图纸",
            "有没有这个产品的图纸？",
            "查看产品蓝图",
            "我想看CAD图纸",
            "这个产品有三维模型吗？",
            "显示产品图档"
        ]
    },
    
    # 查看BOM
    {
        "category_code": "VIEW_BOM",
        "examples": [
            "我想看看这个产品的物料清单",
            "显示一下BOM表",
            "这个产品由哪些零件组成？",
            "查看产品结构树",
            "我想了解产品的组成结构",
            "列出所有物料明细",
            "查看零件清单"
        ]
    },
    
    # 查询工艺
    {
        "category_code": "QUERY_PROCESS",
        "examples": [
            "这个零件是怎么加工的？",
            "我想了解一下生产工艺",
            "加工流程是什么？",
            "工艺参数是多少？",
            "告诉我制造流程",
            "这个零件的加工工艺是什么",
            "查看生产步骤"
        ]
    },
    
    # 查询库存
    {
        "category_code": "CHECK_INVENTORY",
        "examples": [
            "这个零件还有多少库存？",
            "查一下库存数量",
            "仓库里还有没有这个物料？",
            "当前的库存状况如何？",
            "我想知道库存余量",
            "物料够不够用？",
            "查一下存货情况"
        ]
    },
    
    # 查看订单
    {
        "category_code": "VIEW_ORDER",
        "examples": [
            "我想查一下订单状态",
            "这个订单到哪一步了？",
            "显示生产订单信息",
            "采购订单是什么情况？",
            "帮我查订单",
            "订单进度怎么样了？",
            "查看销售订单"
        ]
    },
    
    # 查询项目
    {
        "category_code": "QUERY_PROJECT",
        "examples": [
            "项目进展怎么样了？",
            "我想查一下项目信息",
            "这个项目的计划是什么？",
            "项目任务有哪些？",
            "显示项目详情",
            "项目的执行情况如何？",
            "我想了解项目状态"
        ]
    },
    
    # 查询供应商
    {
        "category_code": "QUERY_SUPPLIER",
        "examples": [
            "这个零件是哪家供应商提供的？",
            "查一下供应商信息",
            "供应商资质怎么样？",
            "供货商是谁？",
            "我想了解供应商情况",
            "这个物料从哪买的？",
            "查看供货商资质"
        ]
    },
    
    # 查看变更记录
    {
        "category_code": "VIEW_CHANGE_LOG",
        "examples": [
            "我想看看这个产品的变更历史",
            "查一下修改记录",
            "这个零件有过什么变更？",
            "显示变更日志",
            "查看产品修改历史",
            "这个零件改过哪些内容？",
            "我想了解变更情况"
        ]
    },
    
    # 查询质量
    {
        "category_code": "QUERY_QUALITY",
        "examples": [
            "质量检查结果如何？",
            "这个零件合格吗？",
            "有没有质量问题？",
            "查看质量检验记录",
            "质检通过了吗？",
            "这个零件的质量状况",
            "显示质量报告"
        ]
    },
    
    # 查询成本
    {
        "category_code": "QUERY_COST",
        "examples": [
            "这个零件成本是多少？",
            "我想了解产品成本",
            "费用大概多少钱？",
            "查一下成本明细",
            "零件价格多少？",
            "我想知道成本情况",
            "显示成本信息"
        ]
    },
    
    # 查看工作流
    {
        "category_code": "VIEW_WORKFLOW",
        "examples": [
            "审批流程走到哪一步了？",
            "我想查看工作流状态",
            "流程还在审批中吗？",
            "显示流程流转情况",
            "审批到哪个环节了？",
            "我想了解流程进度",
            "查看工作流"
        ]
    },
    
    # 查询版本
    {
        "category_code": "QUERY_VERSION",
        "examples": [
            "这是第几个版本？",
            "查一下版本信息",
            "产品版本是多少？",
            "看看版本历史",
            "我想知道版本号",
            "这是哪个版次？",
            "显示版本记录"
        ]
    },
    
    # 生命周期管理
    {
        "category_code": "MANAGE_LIFECYCLE",
        "examples": [
            "我想把这个产品停用",
            "启用这个产品",
            "产品状态改成什么？",
            "管理产品生命周期",
            "把这个零件激活",
            "更改产品状态",
            "设置生命周期"
        ]
    },
    
    # 数据分析
    {
        "category_code": "DATA_ANALYSIS",
        "examples": [
            "帮我分析一下产品数据",
            "生成一个统计报表",
            "看看数据趋势",
            "分析生产数据",
            "我想看统计分析",
            "生成数据报表",
            "查看数据分析结果"
        ]
    },
    
    # 通用查询
    {
        "category_code": "GENERAL_QUERY",
        "examples": [
            "请问这个功能怎么用？",
            "我该怎么操作？",
            "有什么帮助吗？",
            "能帮我解答一下吗？",
            "我想了解一下系统功能",
            "怎么使用这个功能？",
            "请帮帮我"
        ]
    }
]


async def create_semantic_rules():
    """创建语义规则数据。"""
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
            
            # 检查现有语义规则
            print(f"\n3. 检查现有语义规则...")
            result = await session.execute(text("""
                SELECT COUNT(*) FROM intent_rules ir
                JOIN intent_categories ic ON ir.category_id = ic.id
                WHERE ic.application_id = :app_id AND ir.rule_type = 'semantic';
            """), {"app_id": application_id})
            
            existing_count = result.scalar()
            if existing_count > 0:
                print(f"   已有 {existing_count} 条语义规则")
                choice = input("是否要继续添加新语义规则？(y/n): ")
                if choice.lower() != 'y':
                    print("操作取消")
                    return
            
            # 插入语义规则
            print(f"\n4. 创建语义规则...")
            inserted_count = 0
            skipped_count = 0
            
            for rule_data in PLM_SEMANTIC_RULES:
                category_code = rule_data["category_code"]
                
                # 检查分类是否存在
                if category_code not in category_map:
                    print(f"   ⚠️  分类 {category_code} 不存在，跳过")
                    skipped_count += 1
                    continue
                
                category_id = category_map[category_code]
                
                # 为每个示例创建一条规则
                for example in rule_data["examples"]:
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
                        print(f"   - {category_code}: {example[:30]}... (已存在，跳过)")
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
                    print(f"   ✓ {category_code}: {example[:30]}...")
            
            await session.commit()
            print(f"\n✓ 成功创建 {inserted_count} 条语义规则，跳过 {skipped_count} 条！")
            
            # 显示所有规则统计
            print(f"\n5. 查看规则统计...")
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
                print(f"\n   规则统计:")
                for stat in rules_stats:
                    type_name_map = {'keyword': '关键词', 'regex': '正则表达式', 'semantic': '语义'}
                    type_str = type_name_map.get(stat[2], stat[2])
                    print(f"     - {stat[1]} ({stat[0]}) - {type_str}: {stat[3]} 条")
            
            print("\n✓ 完成！")
            print("\n提示：现在可以通过 Web UI 测试意图识别功能了")
            
        except Exception as e:
            print(f"\n✗ 创建语义规则失败: {e}")
            import traceback
            traceback.print_exc()
            await session.rollback()
            raise


if __name__ == "__main__":
    print("=" * 60)
    print("为 PLM 分类创建语义规则")
    print("=" * 60)
    
    try:
        asyncio.run(create_semantic_rules())
        print("\n✓ 创建成功！")
    except Exception as e:
        print(f"\n✗ 创建失败: {e}")
        sys.exit(1)
