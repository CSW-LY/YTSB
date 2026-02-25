#!/usr/bin/env python3
"""
分析 PLM 关键词匹配规则的逻辑
针对规则 "零件,part,component,组件,部件,查找,搜索,查询"
"""

import re
from typing import Dict, List, Tuple, Optional


class MockCategory:
    """模拟分类对象"""
    def __init__(self, id: int, code: str):
        self.id = id
        self.code = code
        self.is_active = True


class MockRule:
    """模拟规则对象"""
    def __init__(self, id: int, category_id: int, content: str, weight: float = 1.0):
        self.id = id
        self.category_id = category_id
        self.content = content
        self.weight = weight
        self.rule_type = "keyword"
        self.is_active = True


def build_indices(rules: List[MockRule], categories: List[MockCategory]) -> Tuple[Dict[str, List[Tuple[MockCategory, MockRule]]], Dict[str, MockCategory]]:
    """
    构建关键词索引
    """
    keyword_index = {}
    exact_match_index = {}
    
    category_map = {c.id: c for c in categories}
    
    for rule in rules:
        if rule.rule_type != "keyword" or not rule.is_active:
            continue
        
        category = category_map.get(rule.category_id)
        if not category or not category.is_active:
            continue
        
        # 标准化关键词
        content = rule.content.strip().lower()
        
        # 检查精确匹配标记（以 ^ 开头）
        if content.startswith("^"):
            exact_keyword = content[1:].strip()
            exact_match_index[exact_keyword] = category
        else:
            # 处理逗号分隔的多个关键词
            keywords = [k.strip() for k in content.split(",")]
            for keyword in keywords:
                if not keyword:
                    continue
                # 添加到模式索引
                if keyword not in keyword_index:
                    keyword_index[keyword] = []
                
                keyword_index[keyword].append((category, rule))
    
    return keyword_index, exact_match_index

def calculate_confidence(text: str, keyword: str) -> float:
    """
    计算置信度分数
    """
    # 完全匹配
    if text == keyword:
        return 1.0
    
    # 开头匹配
    if text.startswith(keyword):
        bonus = 0.9
    # 结尾匹配
    elif text.endswith(keyword):
        bonus = 0.85
    # 检查单词边界
    elif f" {keyword} " in f" {text} " or f" {keyword}" in text:
        bonus = 0.8
    else:
        bonus = 0.6
    
    # 长度比率奖励（偏好更长的关键词）
    length_ratio = len(keyword) / len(text)
    length_bonus = min(length_ratio * 0.2, 0.2)
    
    return min(bonus + length_bonus, 1.0)

def analyze_keyword_matching(rule_content: str, test_questions: List[str]):
    """
    分析关键词匹配规则的逻辑
    """
    print(f"分析规则: {rule_content}")
    print("=" * 80)
    
    # 创建模拟分类和规则
    category = MockCategory(1, "plm_assistant")
    rule = MockRule(1, 1, rule_content)
    
    # 构建索引
    keyword_index, exact_match_index = build_indices([rule], [category])
    
    # 显示解析后的关键词
    print("解析后的关键词:")
    keywords = [k.strip() for k in rule_content.lower().split(",")]
    for i, keyword in enumerate(keywords, 1):
        print(f"  {i}. {keyword}")
    print()
    
    # 测试每个问题
    for question in test_questions:
        print(f"测试问题: '{question}'")
        print("-" * 60)
        
        # 标准化问题
        text_normalized = question.strip().lower()
        
        # 检查精确匹配
        if text_normalized in exact_match_index:
            print("  ✅ 精确匹配")
            print("  置信度: 1.0")
            print(f"  匹配类别: {exact_match_index[text_normalized].code}")
        else:
            # 检查部分匹配
            matches = []
            for keyword, entries in keyword_index.items():
                if keyword in text_normalized:
                    for category, rule in entries:
                        # 计算置信度
                        match_score = calculate_confidence(text_normalized, keyword)
                        confidence = match_score * rule.weight
                        matches.append({
                            "keyword": keyword,
                            "confidence": confidence,
                            "match_score": match_score,
                            "weight": rule.weight
                        })
            
            if matches:
                # 显示所有匹配
                print("  🔍 部分匹配结果:")
                for match in matches:
                    print(f"    - 关键词: '{match['keyword']}'")
                    print(f"      匹配分数: {match['match_score']:.2f}")
                    print(f"      权重: {match['weight']}")
                    print(f"      最终置信度: {match['confidence']:.2f}")
                
                # 找出最佳匹配
                best_match = max(matches, key=lambda m: m["confidence"])
                print(f"  🎯 最佳匹配: '{best_match['keyword']}'")
                print(f"     置信度: {best_match['confidence']:.2f}")
                print(f"     匹配类别: {category.code}")
            else:
                print("  ❌ 无匹配")
        
        print()
    
    print("=" * 80)


if __name__ == "__main__":
    # 测试规则
    rule_content = "零件,part,component,组件,部件,查找,搜索,查询"
    
    # 测试问题
    test_questions = [
        "我想查找零件",
        "帮我搜索component",
        "查询部件信息",
        "寻找组件",
        "part的详细信息",
        "我需要关于零件的资料",
        "如何搜索部件",
        "component的规格是什么",
        "我想了解组件的价格",
        "查询零件库存",
        "帮我找一下part",
        "搜索组件的供应商",
        "查询部件的可用性",
        "我想购买零件",
        "component的替代品有哪些",
        "如何查找组件",
        "部件的保修期是多久",
        "搜索零件的技术文档",
        "查询component的交付时间",
        "帮我找组件的图纸"
    ]
    
    analyze_keyword_matching(rule_content, test_questions)
