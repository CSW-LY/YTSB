"""为 PLM 分类创建对应的规则。"""
import asyncio
import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from sqlalchemy import text
from app.db import async_session_maker


# PLM 规则数据
PLM_RULES = [
    # 查找零件
    {
        "category_code": "SEARCH_PART",
        "rule_type": "keyword",
        "content": "零件,part,component,组件,部件,查找,搜索,查询",
        "weight": 1.0,
        "description": "零件相关的关键词"
    },
    {
        "category_code": "SEARCH_PART",
        "rule_type": "regex",
        "content": r"(查找|搜索|查询|显示|查看).*(零件|部件|组件|配件)",
        "weight": 1.2,
        "description": "查找零件的正则表达式"
    },
    {
        "category_code": "SEARCH_PART",
        "rule_type": "keyword",
        "content": "part number,零件号,编码,型号",
        "weight": 0.9,
        "description": "零件编号相关关键词"
    },
    
    # 搜索图纸
    {
        "category_code": "SEARCH_DRAWING",
        "rule_type": "keyword",
        "content": "图纸,drawing,蓝图,文档,技术文档,图档",
        "weight": 1.0,
        "description": "图纸相关关键词"
    },
    {
        "category_code": "SEARCH_DRAWING",
        "rule_type": "regex",
        "content": r"(搜索|查找|查询|显示|查看).*(图纸|图档|蓝图|文档)",
        "weight": 1.2,
        "description": "搜索图纸的正则表达式"
    },
    {
        "category_code": "SEARCH_DRAWING",
        "rule_type": "keyword",
        "content": "cad,模型,三维,二维,2d,3d",
        "weight": 0.8,
        "description": "CAD和模型相关关键词"
    },
    
    # 查看BOM
    {
        "category_code": "VIEW_BOM",
        "rule_type": "keyword",
        "content": "bom,物料清单,bill of materials,清单,明细,结构,组成",
        "weight": 1.0,
        "description": "BOM相关关键词"
    },
    {
        "category_code": "VIEW_BOM",
        "rule_type": "regex",
        "content": r"(查看|显示|查询).*(bom|物料清单|明细|结构)",
        "weight": 1.2,
        "description": "查看BOM的正则表达式"
    },
    
    # 查询工艺
    {
        "category_code": "QUERY_PROCESS",
        "rule_type": "keyword",
        "content": "工艺,process,流程,生产流程,工艺参数,加工,制造",
        "weight": 1.0,
        "description": "工艺相关关键词"
    },
    {
        "category_code": "QUERY_PROCESS",
        "rule_type": "regex",
        "content": r"(查询|查看|显示).*(工艺|流程|参数)",
        "weight": 1.2,
        "description": "查询工艺的正则表达式"
    },
    
    # 查询库存
    {
        "category_code": "CHECK_INVENTORY",
        "rule_type": "keyword",
        "content": "库存,inventory,stock,存货,可用,余量,入库,出库",
        "weight": 1.0,
        "description": "库存相关关键词"
    },
    {
        "category_code": "CHECK_INVENTORY",
        "rule_type": "regex",
        "content": r"(查询|查看|显示|检查).*(库存|存货|余量)",
        "weight": 1.2,
        "description": "查询库存的正则表达式"
    },
    
    # 查看订单
    {
        "category_code": "VIEW_ORDER",
        "rule_type": "keyword",
        "content": "订单,order,生产订单,采购单,销售订单,下单",
        "weight": 1.0,
        "description": "订单相关关键词"
    },
    {
        "category_code": "VIEW_ORDER",
        "rule_type": "regex",
        "content": r"(查询|查看|显示).*(订单)",
        "weight": 1.2,
        "description": "查看订单的正则表达式"
    },
    
    # 查询项目
    {
        "category_code": "QUERY_PROJECT",
        "rule_type": "keyword",
        "content": "项目,project,工程,任务,计划,进度",
        "weight": 1.0,
        "description": "项目相关关键词"
    },
    {
        "category_code": "QUERY_PROJECT",
        "rule_type": "regex",
        "content": r"(查询|查看|显示).*(项目|工程|进度)",
        "weight": 1.2,
        "description": "查询项目的正则表达式"
    },
    
    # 查询供应商
    {
        "category_code": "QUERY_SUPPLIER",
        "rule_type": "keyword",
        "content": "供应商,supplier,供应商信息,供货商,厂家,厂商",
        "weight": 1.0,
        "description": "供应商相关关键词"
    },
    {
        "category_code": "QUERY_SUPPLIER",
        "rule_type": "regex",
        "content": r"(查询|查看|显示).*(供应商|供货商|厂家)",
        "weight": 1.2,
        "description": "查询供应商的正则表达式"
    },
    
    # 查看变更记录
    {
        "category_code": "VIEW_CHANGE_LOG",
        "rule_type": "keyword",
        "content": "变更,change,修改,历史,记录,日志,变更记录",
        "weight": 1.0,
        "description": "变更记录相关关键词"
    },
    {
        "category_code": "VIEW_CHANGE_LOG",
        "rule_type": "regex",
        "content": r"(查看|查询|显示).*(变更|历史|日志)",
        "weight": 1.2,
        "description": "查看变更记录的正则表达式"
    },
    
    # 查询质量
    {
        "category_code": "QUERY_QUALITY",
        "rule_type": "keyword",
        "content": "质量,quality,检验,质检,合格,不合格,质量记录,质量问题",
        "weight": 1.0,
        "description": "质量相关关键词"
    },
    {
        "category_code": "QUERY_QUALITY",
        "rule_type": "regex",
        "content": r"(查询|查看|显示).*(质量|检验|质检)",
        "weight": 1.2,
        "description": "查询质量的正则表达式"
    },
    
    # 查询成本
    {
        "category_code": "QUERY_COST",
        "rule_type": "keyword",
        "content": "成本,cost,费用,价格,报价,成本分析,成本核算",
        "weight": 1.0,
        "description": "成本相关关键词"
    },
    {
        "category_code": "QUERY_COST",
        "rule_type": "regex",
        "content": r"(查询|查看|显示).*(成本|费用|价格)",
        "weight": 1.2,
        "description": "查询成本的正则表达式"
    },
    
    # 查看工作流
    {
        "category_code": "VIEW_WORKFLOW",
        "rule_type": "keyword",
        "content": "工作流,workflow,流程,审批,审批流程,状态,流转",
        "weight": 1.0,
        "description": "工作流相关关键词"
    },
    {
        "category_code": "VIEW_WORKFLOW",
        "rule_type": "regex",
        "content": r"(查看|查询|显示).*(工作流|审批|流程状态)",
        "weight": 1.2,
        "description": "查看工作流的正则表达式"
    },
    
    # 查询版本
    {
        "category_code": "QUERY_VERSION",
        "rule_type": "keyword",
        "content": "版本,version,版次,修订,更新,版本历史",
        "weight": 1.0,
        "description": "版本相关关键词"
    },
    {
        "category_code": "QUERY_VERSION",
        "rule_type": "regex",
        "content": r"(查询|查看|显示).*(版本|版次|修订)",
        "weight": 1.2,
        "description": "查询版本的正则表达式"
    },
    
    # 生命周期管理
    {
        "category_code": "MANAGE_LIFECYCLE",
        "rule_type": "keyword",
        "content": "生命周期,lifecycle,状态,状态管理,启用,停用,发布",
        "weight": 1.0,
        "description": "生命周期相关关键词"
    },
    {
        "category_code": "MANAGE_LIFECYCLE",
        "rule_type": "regex",
        "content": r"(管理|控制|改变).*(状态|生命周期|启用|停用)",
        "weight": 1.2,
        "description": "管理生命周期的正则表达式"
    },
    
    # 数据分析
    {
        "category_code": "DATA_ANALYSIS",
        "rule_type": "keyword",
        "content": "分析,analysis,统计,报表,数据,趋势,统计信息",
        "weight": 1.0,
        "description": "数据分析相关关键词"
    },
    {
        "category_code": "DATA_ANALYSIS",
        "rule_type": "regex",
        "content": r"(分析|统计|生成).*(报表|数据|图表|趋势)",
        "weight": 1.2,
        "description": "数据分析的正则表达式"
    },
    
    # 通用查询
    {
        "category_code": "GENERAL_QUERY",
        "rule_type": "keyword",
        "content": "查询,query,搜索,search,查找,问,请问,如何,什么",
        "weight": 0.5,
        "description": "通用查询关键词"
    },
    {
        "category_code": "GENERAL_QUERY",
        "rule_type": "regex",
        "content": r"(请问|怎么|如何|什么|帮助|help)",
        "weight": 0.7,
        "description": "通用查询的正则表达式"
    }
]


async def create_plm_rules():
    """创建 PLM 规则数据。"""
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
            
            # 检查现有规则
            print(f"\n3. 检查现有规则...")
            result = await session.execute(text("""
                SELECT COUNT(*) FROM intent_rules ir
                JOIN intent_categories ic ON ir.category_id = ic.id
                WHERE ic.application_id = :app_id;
            """), {"app_id": application_id})
            
            existing_count = result.scalar()
            if existing_count > 0:
                print(f"   已有 {existing_count} 条规则")
                choice = input("是否要继续添加新规则？(y/n): ")
                if choice.lower() != 'y':
                    print("操作取消")
                    return
            
            # 插入规则
            print(f"\n4. 创建规则...")
            inserted_count = 0
            skipped_count = 0
            
            for rule in PLM_RULES:
                category_code = rule["category_code"]
                
                # 检查分类是否存在
                if category_code not in category_map:
                    print(f"   ⚠️  分类 {category_code} 不存在，跳过")
                    skipped_count += 1
                    continue
                
                category_id = category_map[category_code]
                
                # 检查规则是否已存在
                result = await session.execute(text("""
                    SELECT id FROM intent_rules 
                    WHERE category_id = :category_id AND rule_type = :rule_type AND content = :content;
                """), {
                    "category_id": category_id,
                    "rule_type": rule["rule_type"],
                    "content": rule["content"]
                })
                
                existing = result.fetchone()
                
                if existing:
                    print(f"   - {category_code}: {rule['description']} (已存在，跳过)")
                    skipped_count += 1
                    continue
                
                # 插入新规则
                await session.execute(text("""
                    INSERT INTO intent_rules 
                    (category_id, rule_type, content, weight, is_active)
                    VALUES (:category_id, :rule_type, :content, :weight, true);
                """), {
                    "category_id": category_id,
                    "rule_type": rule["rule_type"],
                    "content": rule["content"],
                    "weight": rule["weight"]
                })
                
                inserted_count += 1
                print(f"   ✓ {category_code}: {rule['description']}")
            
            await session.commit()
            print(f"\n✓ 成功创建 {inserted_count} 条规则，跳过 {skipped_count} 条！")
            
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
                    print(f"     - {stat[1]} ({stat[0]}) - {stat[2]}: {stat[3]} 条")
            
            print("\n✓ 完成！")
            print("\n提示：现在可以通过 Web UI 测试意图识别功能了")
            
        except Exception as e:
            print(f"\n✗ 创建规则失败: {e}")
            import traceback
            traceback.print_exc()
            await session.rollback()
            raise


if __name__ == "__main__":
    print("=" * 60)
    print("为 PLM 分类创建规则")
    print("=" * 60)
    
    try:
        asyncio.run(create_plm_rules())
        print("\n✓ 创建成功！")
    except Exception as e:
        print(f"\n✗ 创建失败: {e}")
        sys.exit(1)
