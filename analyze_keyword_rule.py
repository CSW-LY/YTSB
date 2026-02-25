#!/usr/bin/env python3
"""分析关键词匹配规则的逻辑"""

import sys
sys.path.insert(0, '.')

from app.services.recognizer.keyword import KeywordRecognizer
from app.models.database import IntentCategory, IntentRule

# 模拟创建分类和规则
class MockCategory:
    def __init__(self, id, code, name, is_active=True):
        self.id = id
        self.code = code
        self.name = name
        self.is_active = is_active

class MockRule:
    def __init__(self, id, category_id, rule_type, content, weight, is_active=True):
        self.id = id
        self.category_id = category_id
        self.rule_type = rule_type
        self.content = content
        self.weight = weight
        self.is_active = is_active

# 创建测试数据
def create_test_data():
    """创建测试分类和规则"""
    category = MockCategory(1, "SEARCH_PART", "零件搜索")
    
    # 测试规则: 零件,part,component,组件,部件,查找,搜索,查询
    rule = MockRule(
        id=1,
        category_id=1,
        rule_type="keyword",
        content="零件,part,component,组件,部件,查找,搜索,查询",
        weight=1.0
    )
    
    return [category], [rule]

# 分析关键词规则
def analyze_keyword_rule():
    """分析关键词匹配规则"""
    print("=" * 60)
    print("关键词匹配规则分析")
    print("=" * 60)
    
    # 创建测试数据
    categories, rules = create_test_data()
    
    # 创建关键词识别器
    recognizer = KeywordRecognizer()
    
    # 构建索引
    print("1. 构建关键词索引")
    print("规则内容:", rules[0].content)
    print("权重:", rules[0].weight)
    
    # 手动展示关键词分割过程
    content = rules[0].content.strip().lower()
    keywords = [k.strip() for k in content.split(",")]
    print("分割后的关键词:", keywords)
    print(f"共 {len(keywords)} 个关键词")
    print()
    
    # 构建索引
    recognizer._build_indices(categories, rules)
    print("2. 索引构建结果")
    print("关键词索引:", list(recognizer._keyword_index.keys()))
    print()
    
    # 测试不同输入
    test_inputs = [
        "查找零件",
        "帮我查询component信息",
        "搜索部件的详细资料",
        "我需要part的规格",
        "请帮我找个组件",
        "部件在哪里可以找到",
        "帮我搜索一下零件的库存",
        "查询这个component的价格",
        "找一下component的供应商",
        "帮我查一下部件的状态"
    ]
    
    print("3. 测试输入匹配")
    print("=" * 40)
    
    for i, test_input in enumerate(test_inputs, 1):
        print(f"测试 {i}: '{test_input}'")
        
        # 模拟识别过程
        text_normalized = test_input.strip().lower()
        print(f"标准化文本: '{text_normalized}'")
        
        # 检查匹配
        matches = []
        for keyword, entries in recognizer._keyword_index.items():
            if keyword in text_normalized:
                for category, rule in entries:
                    # 计算置信度
                    match_score = recognizer._calculate_confidence(text_normalized, keyword)
                    confidence = match_score * rule.weight
                    matches.append({
                        "keyword": keyword,
                        "category": category.code,
                        "confidence": confidence,
                        "match_score": match_score,
                        "weight": rule.weight
                    })
        
        if matches:
            # 按置信度排序
            matches.sort(key=lambda x: x["confidence"], reverse=True)
            print("匹配结果:")
            for match in matches:
                print(f"  - 关键词: '{match['keyword']}'")
                print(f"    置信度: {match['confidence']:.3f} (匹配得分: {match['match_score']:.3f} × 权重: {match['weight']})")
            
            best_match = matches[0]
            print(f"最佳匹配: '{best_match['keyword']}' (置信度: {best_match['confidence']:.3f})")
        else:
            print("无匹配结果")
        
        print("-" * 40)
    
    print("4. 置信度计算说明")
    print("=" * 40)
    print("置信度计算因素:")
    print("- 精确匹配: 1.0")
    print("- 开头匹配: 0.9")
    print("- 结尾匹配: 0.85")
    print("- 词边界匹配: 0.8")
    print("- 子字符串匹配: 0.6")
    print("- 长度比例奖励: 最长 +0.2")
    print("- 最终置信度: 匹配得分 × 规则权重")
    print()
    
    print("5. 规则匹配逻辑总结")
    print("=" * 40)
    print("1. 规则解析: 分割逗号分隔的关键词")
    print("2. 索引构建: 为每个关键词创建索引")
    print("3. 匹配检查: 检查输入是否包含任何关键词")
    print("4. 置信度计算: 基于匹配位置和长度")
    print("5. 结果返回: 返回置信度最高的匹配")
    print()
    
    print("6. 示例解释")
    print("=" * 40)
    print("对于输入 '查找零件':")
    print("- 匹配关键词: '查找' 和 '零件'")
    print("- '查找' 的匹配: 开头匹配，得分 0.9")
    print("- '零件' 的匹配: 词边界匹配，得分 0.8")
    print("- 规则权重: 1.0")
    print("- 最终置信度: 取最高值 (0.9 × 1.0 = 0.9)")
    print()
    
    print("对于输入 '查询component':")
    print("- 匹配关键词: '查询' 和 'component'")
    print("- '查询' 的匹配: 开头匹配，得分 0.9")
    print("- 'component' 的匹配: 词边界匹配，得分 0.8")
    print("- 规则权重: 1.0")
    print("- 最终置信度: 取最高值 (0.9 × 1.0 = 0.9)")

if __name__ == "__main__":
    analyze_keyword_rule()
