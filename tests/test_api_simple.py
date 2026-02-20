"""简单的API测试脚本。"""
import requests
import json

BASE_URL = "http://localhost:8000/api/ui"

def test_applications_api():
    """测试应用管理API。"""
    print("=" * 60)
    print("测试应用管理API")
    print("=" * 60)
    
    # 1. 创建应用
    print("\n1. POST /applications - 创建应用")
    try:
        response = requests.post(
            f"{BASE_URL}/applications",
            json={
                "app_key": "test_app_simple",
                "name": "简单测试应用",
                "description": "用于测试的应用"
            },
            timeout=5
        )
        print(f"   状态码: {response.status_code}")
        if response.status_code == 200:
            app_data = response.json()
            print(f"   ✓ 创建成功: {app_data}")
            app_id = app_data['id']
        else:
            print(f"   ✗ 创建失败: {response.text}")
            return False
    except Exception as e:
        print(f"   ✗ 连接失败: {e}")
        print("   提示: 请确保服务已启动 (python start_with_ui.py)")
        return False
    
    # 2. 列出应用
    print("\n2. GET /applications - 列出应用")
    try:
        response = requests.get(f"{BASE_URL}/applications", timeout=5)
        print(f"   状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✓ 列出成功: 共 {len(data['items'])} 个应用")
            for app in data['items']:
                print(f"      - {app['app_key']}: {app['name']}")
        else:
            print(f"   ✗ 列出失败: {response.text}")
            return False
    except Exception as e:
        print(f"   ✗ 请求失败: {e}")
        return False
    
    # 3. 创建分类
    print("\n3. POST /applications/{id}/categories - 创建分类")
    try:
        response = requests.post(
            f"{BASE_URL}/applications/{app_id}/categories",
            json={
                "code": "test_category_simple",
                "name": "简单测试分类",
                "description": "用于测试的分类",
                "priority": 10
            },
            timeout=5
        )
        print(f"   状态码: {response.status_code}")
        if response.status_code == 200:
            category_data = response.json()
            print(f"   ✓ 创建成功: {category_data}")
        else:
            print(f"   ✗ 创建失败: {response.text}")
            return False
    except Exception as e:
        print(f"   ✗ 请求失败: {e}")
        return False
    
    # 4. 获取应用的分类
    print("\n4. GET /applications/{id}/categories - 获取应用分类")
    try:
        response = requests.get(
            f"{BASE_URL}/applications/{app_id}/categories",
            timeout=5
        )
        print(f"   状态码: {response.status_code}")
        if response.status_code == 200:
            categories = response.json()
            print(f"   ✓ 获取成功: 共 {len(categories)} 个分类")
            for cat in categories:
                print(f"      - {cat['code']}: {cat['name']}")
        else:
            print(f"   ✗ 获取失败: {response.text}")
            return False
    except Exception as e:
        print(f"   ✗ 请求失败: {e}")
        return False
    
    # 5. 获取所有分类（带应用过滤）
    print("\n5. GET /categories?application_id={id} - 获取分类")
    try:
        response = requests.get(
            f"{BASE_URL}/categories?application_id={app_id}",
            timeout=5
        )
        print(f"   状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✓ 获取成功: 共 {len(data['items'])} 个分类")
        else:
            print(f"   ✗ 获取失败: {response.text}")
            return False
    except Exception as e:
        print(f"   ✗ 请求失败: {e}")
        return False
    
    return True


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("应用与分类绑定功能API测试")
    print("=" * 60)
    
    success = test_applications_api()
    
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    
    if success:
        print("✓ 所有API测试通过！")
        print("\n您可以在浏览器中访问以下地址查看UI:")
        print("http://localhost:8000/ui")
    else:
        print("✗ 部分API测试失败，请检查错误信息。")
