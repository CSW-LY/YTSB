"""创建 PLM 相关的意图分类数据。"""
import asyncio
import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from sqlalchemy import text
from app.db import async_session_maker


# PLM 相关的分类数据
PLM_CATEGORIES = [
    {
        "application_key": "plm_assistant",
        "code": "SEARCH_PART",
        "name": "查找零件",
        "description": "根据零件编号、名称等条件查找零件信息",
        "priority": 100
    },
    {
        "application_key": "plm_assistant",
        "code": "SEARCH_DRAWING",
        "name": "搜索图纸",
        "description": "搜索和查看产品图纸、技术文档",
        "priority": 100
    },
    {
        "application_key": "plm_assistant",
        "code": "VIEW_BOM",
        "name": "查看BOM",
        "description": "查看产品物料清单（BOM）结构",
        "priority": 90
    },
    {
        "application_key": "plm_assistant",
        "code": "QUERY_PROCESS",
        "name": "查询工艺",
        "description": "查询生产工艺流程和工艺参数",
        "priority": 90
    },
    {
        "application_key": "plm_assistant",
        "code": "CHECK_INVENTORY",
        "name": "查询库存",
        "description": "查询零件、物料的库存信息",
        "priority": 85
    },
    {
        "application_key": "plm_assistant",
        "code": "VIEW_ORDER",
        "name": "查看订单",
        "description": "查询生产订单、采购订单信息",
        "priority": 85
    },
    {
        "application_key": "plm_assistant",
        "code": "QUERY_PROJECT",
        "name": "查询项目",
        "description": "查询项目信息和项目进度",
        "priority": 80
    },
    {
        "application_key": "plm_assistant",
        "code": "QUERY_SUPPLIER",
        "name": "查询供应商",
        "description": "查询供应商信息和资质",
        "priority": 70
    },
    {
        "application_key": "plm_assistant",
        "code": "VIEW_CHANGE_LOG",
        "name": "查看变更记录",
        "description": "查看产品、零件的变更历史记录",
        "priority": 70
    },
    {
        "application_key": "plm_assistant",
        "code": "QUERY_QUALITY",
        "name": "查询质量",
        "description": "查询质量检验记录和质量问题",
        "priority": 70
    },
    {
        "application_key": "plm_assistant",
        "code": "QUERY_COST",
        "name": "查询成本",
        "description": "查询产品成本、零件成本信息",
        "priority": 60
    },
    {
        "application_key": "plm_assistant",
        "code": "VIEW_WORKFLOW",
        "name": "查看工作流",
        "description": "查看审批工作流和流程状态",
        "priority": 60
    },
    {
        "application_key": "plm_assistant",
        "code": "QUERY_VERSION",
        "name": "查询版本",
        "description": "查询产品、零件的版本信息",
        "priority": 60
    },
    {
        "application_key": "plm_assistant",
        "code": "MANAGE_LIFECYCLE",
        "name": "生命周期管理",
        "description": "管理产品生命周期状态",
        "priority": 50
    },
    {
        "application_key": "plm_assistant",
        "code": "DATA_ANALYSIS",
        "name": "数据分析",
        "description": "分析产品数据、生产数据等",
        "priority": 50
    },
    {
        "application_key": "plm_assistant",
        "code": "GENERAL_QUERY",
        "name": "通用查询",
        "description": "其他类型的查询请求",
        "priority": 10
    }
]


async def create_plm_categories():
    """创建 PLM 分类数据。"""
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
                print("   ⚠️  未找到 PLM 应用 (app_key: plm_assistant)")
                
                # 查看所有可用应用
                result = await session.execute(text("""
                    SELECT id, app_key, name FROM applications ORDER BY id;
                """))
                apps = result.fetchall()
                
                if apps:
                    print("\n   可用的应用:")
                    for app in apps:
                        print(f"     - ID: {app[0]}, app_key: {app[1]}, name: {app[2]}")
                    
                    print("\n请选择一个应用 ID 来创建分类：")
                    try:
                        app_id = int(input("应用 ID: "))
                        result = await session.execute(text("""
                            SELECT app_key, name FROM applications WHERE id = :id;
                        """), {"id": app_id})
                        selected_app = result.fetchone()
                        if selected_app:
                            app = (app_id, selected_app[0], selected_app[1])
                            print(f"   已选择应用: {selected_app[1]} ({selected_app[0]})")
                        else:
                            print("   无效的应用 ID")
                            return
                    except (ValueError, KeyboardInterrupt):
                        print("   操作取消")
                        return
                else:
                    print("   没有可用应用，请先创建应用")
                    return
            else:
                print(f"   ✓ 找到 PLM 应用: {app[2]} (ID: {app[0]})")
            
            application_id = app[0]
            app_key = app[1]
            
            # 检查是否已有分类数据
            print(f"\n2. 检查现有分类数据...")
            result = await session.execute(text("""
                SELECT COUNT(*) FROM intent_categories WHERE application_id = :app_id;
            """), {"app_id": application_id})
            count = result.scalar()
            
            if count > 0:
                print(f"   已有 {count} 条分类数据")
                choice = input("是否要继续添加新分类？(y/n): ")
                if choice.lower() != 'y':
                    print("操作取消")
                    return
            
            # 插入分类数据
            print(f"\n3. 创建 PLM 分类数据...")
            inserted_count = 0
            
            for cat in PLM_CATEGORIES:
                # 跳过不匹配的应用
                if cat["application_key"] != app_key:
                    continue
                
                # 检查分类是否已存在
                result = await session.execute(text("""
                    SELECT id FROM intent_categories 
                    WHERE application_id = :app_id AND code = :code;
                """), {"app_id": application_id, "code": cat["code"]})
                
                existing = result.fetchone()
                
                if existing:
                    print(f"   - {cat['name']} (已存在，跳过)")
                    continue
                
                # 插入新分类
                await session.execute(text("""
                    INSERT INTO intent_categories 
                    (application_id, code, name, description, priority, is_active)
                    VALUES (:app_id, :code, :name, :description, :priority, true);
                """), {
                    "app_id": application_id,
                    "code": cat["code"],
                    "name": cat["name"],
                    "description": cat["description"],
                    "priority": cat["priority"]
                })
                
                inserted_count += 1
                print(f"   ✓ {cat['name']}")
            
            await session.commit()
            print(f"\n✓ 成功创建 {inserted_count} 个分类！")
            
            # 显示所有分类
            print(f"\n4. 查看所有分类...")
            result = await session.execute(text("""
                SELECT code, name, description, priority, is_active
                FROM intent_categories
                WHERE application_id = :app_id
                ORDER BY priority DESC, name;
            """), {"app_id": application_id})
            
            categories = result.fetchall()
            
            if categories:
                print(f"\n   {len(categories)} 个分类:")
                for cat in categories:
                    status = "✓" if cat[4] else "✗"
                    print(f"     [{status}] {cat[1]} ({cat[0]}) - 优先级: {cat[3]}")
                    if cat[2]:
                        print(f"         描述: {cat[2]}")
            else:
                print("   无分类数据")
            
            print("\n✓ 完成！")
            print("\n提示：现在可以通过 Web UI 查看和管理这些分类了")
            
        except Exception as e:
            print(f"\n✗ 创建分类失败: {e}")
            import traceback
            traceback.print_exc()
            await session.rollback()
            raise


if __name__ == "__main__":
    print("=" * 60)
    print("创建 PLM 意图分类数据")
    print("=" * 60)
    
    try:
        asyncio.run(create_plm_categories())
        print("\n✓ 创建成功！")
    except Exception as e:
        print(f"\n✗ 创建失败: {e}")
        sys.exit(1)
