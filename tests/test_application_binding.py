"""测试应用与分类绑定功能。"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from app.db import async_session_maker
from app.models.database import Application, IntentCategory, AppIntent
from app.services.config_service import ConfigService


async def test_database_migration():
    """测试数据库迁移是否成功。"""
    print("=" * 60)
    print("测试数据库迁移")
    print("=" * 60)

    async with async_session_maker() as session:
        # 检查 applications 表是否存在
        result = await session.execute(text("""
            SELECT table_name FROM information_schema.tables
            WHERE table_name = 'applications';
        """))
        apps_table_exists = result.scalar()
        
        print(f"✓ applications 表存在: {apps_table_exists}")
        
        # 检查 intent_categories 表是否有 application_id 字段
        result = await session.execute(text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'intent_categories' AND column_name = 'application_id';
        """))
        application_id_exists = result.scalar()
        
        print(f"✓ intent_categories.application_id 字段存在: {application_id_exists}")
        
        # 检查 app_intents 表是否有 application_id 字段
        result = await session.execute(text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'app_intents' AND column_name = 'application_id';
        """))
        app_intents_application_id_exists = result.scalar()
        
        print(f"✓ app_intents.application_id 字段存在: {app_intents_application_id_exists}")
        
        # 查询应用数量
        result = await session.execute(text("SELECT COUNT(*) FROM applications;"))
        app_count = result.scalar()
        print(f"✓ 应用数量: {app_count}")
        
        # 查询分类数量
        result = await session.execute(text("SELECT COUNT(*) FROM intent_categories;"))
        category_count = result.scalar()
        print(f"✓ 分类数量: {category_count}")
        
        # 查询有 application_id 的分类数量
        result = await session.execute(text("SELECT COUNT(*) FROM intent_categories WHERE application_id IS NOT NULL;"))
        category_with_app_count = result.scalar()
        print(f"✓ 有 application_id 的分类数量: {category_with_app_count}")
        
        if category_count > 0:
            print(f"  分类绑定率: {category_with_app_count}/{category_count} ({100*category_with_app_count/category_count:.1f}%)")
        
        return apps_table_exists and application_id_exists and app_intents_application_id_exists


async def test_config_service():
    """测试 ConfigService 的应用管理方法。"""
    print("\n" + "=" * 60)
    print("测试 ConfigService")
    print("=" * 60)
    
    async with async_session_maker() as session:
        svc = ConfigService(session)
        
        # 测试创建应用
        print("\n1. 测试创建应用...")
        try:
            app = await svc.create_application(
                app_key="test_app",
                name="测试应用",
                description="这是一个测试应用"
            )
            await session.commit()
            print(f"✓ 创建应用成功: ID={app.id}, app_key={app.app_key}")
        except Exception as e:
            print(f"✗ 创建应用失败: {e}")
            return False
        
        # 测试获取应用
        print("\n2. 测试获取应用...")
        app = await svc.get_application_by_key("test_app")
        if app:
            print(f"✓ 获取应用成功: {app.name}")
        else:
            print("✗ 获取应用失败")
            return False
        
        # 测试创建分类
        print("\n3. 测试创建分类...")
        try:
            category = await svc.create_category(
                application_id=app.id,
                code="test_category",
                name="测试分类",
                description="这是一个测试分类"
            )
            await session.commit()
            print(f"✓ 创建分类成功: ID={category.id}, code={category.code}")
        except Exception as e:
            print(f"✗ 创建分类失败: {e}")
            return False
        
        # 测试获取应用的分类
        print("\n4. 测试获取应用的分类...")
        categories = await svc.get_categories_by_application(app.id)
        if categories:
            print(f"✓ 获取应用分类成功: 共 {len(categories)} 个分类")
            for cat in categories:
                print(f"  - {cat.code}: {cat.name}")
        else:
            print("✗ 获取应用分类失败")
            return False
        
        # 测试列出所有应用
        print("\n5. 测试列出所有应用...")
        applications = await svc.list_applications()
        print(f"✓ 列出应用成功: 共 {len(applications)} 个应用")
        
        return True


async def test_api_endpoints():
    """测试 API 接口。"""
    print("\n" + "=" * 60)
    print("测试 API 接口")
    print("=" * 60)
    
    import httpx
    
    base_url = "http://localhost:8000/api/ui"
    
    async with httpx.AsyncClient() as client:
        # 测试创建应用
        print("\n1. 测试 POST /applications")
        try:
            response = await client.post(
                f"{base_url}/applications",
                json={
                    "app_key": "api_test_app",
                    "name": "API测试应用",
                    "description": "通过API创建的测试应用"
                },
                timeout=5.0
            )
            if response.status_code == 200:
                app_data = response.json()
                print(f"✓ 创建应用成功: ID={app_data['id']}, app_key={app_data['app_key']}")
                app_id = app_data['id']
            else:
                print(f"✗ 创建应用失败: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"✗ API连接失败: {e}")
            print("  提示: 请确保服务已启动 (python start_with_ui.py)")
            return False
        
        # 测试列出应用
        print("\n2. 测试 GET /applications")
        try:
            response = await client.get(f"{base_url}/applications", timeout=5.0)
            if response.status_code == 200:
                data = response.json()
                print(f"✓ 列出应用成功: 共 {len(data['items'])} 个应用")
            else:
                print(f"✗ 列出应用失败: {response.status_code}")
                return False
        except Exception as e:
            print(f"✗ API请求失败: {e}")
            return False
        
        # 测试创建分类
        print("\n3. 测试 POST /applications/{id}/categories")
        try:
            response = await client.post(
                f"{base_url}/applications/{app_id}/categories",
                json={
                    "code": "api_test_category",
                    "name": "API测试分类",
                    "description": "通过API创建的测试分类",
                    "priority": 10
                },
                timeout=5.0
            )
            if response.status_code == 200:
                category_data = response.json()
                print(f"✓ 创建分类成功: ID={category_data['id']}, code={category_data['code']}")
            else:
                print(f"✗ 创建分类失败: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"✗ API请求失败: {e}")
            return False
        
        # 测试获取应用的分类
        print("\n4. 测试 GET /applications/{id}/categories")
        try:
            response = await client.get(f"{base_url}/applications/{app_id}/categories", timeout=5.0)
            if response.status_code == 200:
                categories = response.json()
                print(f"✓ 获取应用分类成功: 共 {len(categories)} 个分类")
            else:
                print(f"✗ 获取应用分类失败: {response.status_code}")
                return False
        except Exception as e:
            print(f"✗ API请求失败: {e}")
            return False
        
        # 测试获取所有分类
        print("\n5. 测试 GET /categories (带 application_id 过滤)")
        try:
            response = await client.get(
                f"{base_url}/categories?application_id={app_id}",
                timeout=5.0
            )
            if response.status_code == 200:
                data = response.json()
                print(f"✓ 获取分类成功: 共 {len(data['items'])} 个分类")
            else:
                print(f"✗ 获取分类失败: {response.status_code}")
                return False
        except Exception as e:
            print(f"✗ API请求失败: {e}")
            return False
        
        return True


async def main():
    """主测试函数。"""
    print("\n" + "=" * 60)
    print("应用与分类绑定功能测试")
    print("=" * 60)
    
    # 测试数据库迁移
    db_ok = await test_database_migration()
    
    # 测试 ConfigService
    service_ok = await test_config_service()
    
    # 测试 API 接口
    api_ok = await test_api_endpoints()
    
    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    print(f"数据库迁移测试: {'✓ 通过' if db_ok else '✗ 失败'}")
    print(f"ConfigService测试: {'✓ 通过' if service_ok else '✗ 失败'}")
    print(f"API接口测试: {'✓ 通过' if api_ok else '✗ 失败'}")
    
    if db_ok and service_ok and api_ok:
        print("\n✓ 所有测试通过！应用与分类绑定功能正常工作。")
        return 0
    else:
        print("\n✗ 部分测试失败，请检查错误信息。")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
