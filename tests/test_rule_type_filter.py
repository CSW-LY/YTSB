import urllib.request
import json

BASE_URL = "http://localhost:8000"

def test_rule_type_filter():
    print("测试1：单独使用 rule_type 过滤")
    url = f"{BASE_URL}/api/ui/rules?rule_type=regex"
    with urllib.request.urlopen(url) as response:
        data = json.loads(response.read().decode())
        print(f"状态码: {response.status}")
        print(f"返回规则数: {len(data['items'])}")
        if data['items']:
            print(f"第一条规则类型: {data['items'][0]['rule_type']}")
    print()

    print("测试2：组合使用 rule_type 和 category_id 过滤")
    url = f"{BASE_URL}/api/ui/rules?rule_type=regex&category_id=2&page=1&page_size=10"
    with urllib.request.urlopen(url) as response:
        data = json.loads(response.read().decode())
        print(f"状态码: {response.status}")
        print(f"返回规则数: {len(data['items'])}")
        if data['items']:
            print(f"第一条规则类型: {data['items'][0]['rule_type']}, 分类ID: {data['items'][0]['category_id']}")
    print()

    print("测试3：使用所有过滤条件")
    url = f"{BASE_URL}/api/ui/rules?rule_type=keyword&category_id=2&is_active=true"
    with urllib.request.urlopen(url) as response:
        data = json.loads(response.read().decode())
        print(f"状态码: {response.status}")
        print(f"返回规则数: {len(data['items'])}")
        if data['items']:
            print(f"第一条规则类型: {data['items'][0]['rule_type']}, 分类ID: {data['items'][0]['category_id']}, 激活状态: {data['items'][0]['is_active']}")
    print()

    print("测试4：不使用任何过滤条件")
    url = f"{BASE_URL}/api/ui/rules"
    with urllib.request.urlopen(url) as response:
        data = json.loads(response.read().decode())
        print(f"状态码: {response.status}")
        print(f"返回规则数: {len(data['items'])}")
        print(f"总规则数: {data['total']}")
    print()

    print("测试5：验证 rule_type 过滤是否正确")
    url = f"{BASE_URL}/api/ui/rules?rule_type=regex"
    with urllib.request.urlopen(url) as response:
        data = json.loads(response.read().decode())
        print(f"状态码: {response.status}")
        print(f"返回规则数: {len(data['items'])}")
        all_regex = all(rule['rule_type'] == 'regex' for rule in data['items'])
        print(f"所有规则都是regex类型: {all_regex}")
        if data['items']:
            for rule in data['items'][:3]:
                print(f"  - 规则ID {rule['id']}: 类型={rule['rule_type']}, 内容={rule['content'][:30]}...")

if __name__ == "__main__":
    test_rule_type_filter()
