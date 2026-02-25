#!/usr/bin/env python3
"""简化的关键词匹配规则分析"""

# 模拟关键词匹配逻辑
def analyze_keyword_matching():
    """分析关键词匹配规则"""
    print("=" * 60)
    print("关键词匹配规则分析")
    print("=" * 60)
    
    # 测试规则: 零件,part,component,组件,部件,查找,搜索,查询
    rule_content = "零件,part,component,组件,部件,查找,搜索,查询"
    rule_weight = 1.0
    
    print("1. 规则信息")
    print("规则内容:", rule_content)
    print("权重:", rule_weight)
    print()
    
    # 步骤1: 分割关键词
    print("2. 关键词分割过程")
    content_normalized = rule_content.strip().lower()
    keywords = [k.strip() for k in content_normalized.split(",")]
    print("标准化后的内容:", content_normalized)
    print("分割后的关键词:", keywords)
    print(f"共 {len(keywords)} 个关键词")
    print()
    
    # 步骤2: 构建索引
    print("3. 索引构建")
    keyword_index = {}
    for keyword in keywords:
        if keyword:
            keyword_index[keyword] = "SEARCH_PART"  # 模拟分类
    print("关键词索引:", list(keyword_index.keys()))
    print()
    
    # 模拟置信度计算
    def calculate_confidence(text, keyword):
        """计算置信度"""
        text = text.lower()
        keyword = keyword.lower()
        
        # 精确匹配
        if text == keyword:
            return 1.0
        
        # 开头匹配
        if text.startswith(keyword):
            bonus = 0.9
        # 结尾匹配
        elif text.endswith(keyword):
            bonus = 0.85
        # 词边界匹配
        elif f" {keyword} " in f" {text} " or f" {keyword}" in text:
            bonus = 0.8
        else:
            bonus = 0.6
        
        # 长度比例奖励
        length_ratio = len(keyword) / len(text)
        length_bonus = min(length_ratio * 0.2, 0.2)
        
        return min(bonus + length_bonus, 1.0)
    
    # 步骤3: 测试匹配
    print("4. 匹配测试")
    print("=" * 40)
    
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
    
    for i, test_input in enumerate(test_inputs, 1):
        print(f"测试 {i}: '{test_input}'")
        text_normalized = test_input.strip().lower()
        print(f"标准化文本: '{text_normalized}'")
        
        # 检查匹配
        matches = []
        for keyword in keywords:
            if keyword in text_normalized:
                match_score = calculate_confidence(text_normalized, keyword)
                confidence = match_score * rule_weight
                matches.append({
                    "keyword": keyword,
                    "confidence": confidence,
                    "match_score": match_score
                })
        
        if matches:
            # 按置信度排序
            matches.sort(key=lambda x: x["confidence"], reverse=True)
            print("匹配结果:")
            for match in matches:
                print(f"  - 关键词: '{match['keyword']}'")
                print(f"    置信度: {match['confidence']:.3f} (匹配得分: {match['match_score']:.3f})")
            
            best_match = matches[0]
            print(f"最佳匹配: '{best_match['keyword']}' (置信度: {best_match['confidence']:.3f})")
        else:
            print("无匹配结果")
        
        print("-" * 40)
    
    # 步骤4: 逻辑说明
    print("5. 匹配逻辑说明")
    print("=" * 40)
    print("关键词匹配的完整流程:")
    print("1. 规则解析: 分割逗号分隔的关键词")
    print("2. 索引构建: 为每个关键词创建索引")
    print("3. 输入处理: 标准化输入文本")
    print("4. 匹配检查: 检查输入是否包含任何关键词")
    print("5. 置信度计算: 基于匹配位置和长度")
    print("6. 结果选择: 返回置信度最高的匹配")
    print()
    
    print("6. 置信度计算详细说明")
    print("=" * 40)
    print("置信度计算因素:")
    print("- 精确匹配: 1.0 (最高)")
    print("- 开头匹配: 0.9 (较高)")
    print("- 结尾匹配: 0.85 (中等偏上)")
    print("- 词边界匹配: 0.8 (中等)")
    print("- 子字符串匹配: 0.6 (较低)")
    print("- 长度比例奖励: 最长 +0.2")
    print("- 最终置信度: 匹配得分 × 规则权重")
    print()
    
    print("7. 示例详细分析")
    print("=" * 40)
    print("示例1: 输入 '查找零件'")
    print("- 匹配的关键词: '查找' 和 '零件'")
    print("- '查找' 的匹配: 开头匹配，得分 0.9")
    print("- '零件' 的匹配: 词边界匹配，得分 0.8")
    print("- 规则权重: 1.0")
    print("- 计算过程: max(0.9×1.0, 0.8×1.0) = 0.9")
    print("- 最终结果: 置信度 0.9，分类 SEARCH_PART")
    print()
    
    print("示例2: 输入 '帮我查询component信息'")
    print("- 匹配的关键词: '查询' 和 'component'")
    print("- '查询' 的匹配: 子字符串匹配，得分 0.6 + 长度奖励")
    print("- 'component' 的匹配: 词边界匹配，得分 0.8 + 长度奖励")
    print("- 规则权重: 1.0")
    print("- 计算过程: max(0.6×1.0, 0.8×1.0) = 0.8")
    print("- 最终结果: 置信度 0.8，分类 SEARCH_PART")
    print()
    
    print("8. 总结")
    print("=" * 40)
    print("关键词匹配规则的核心特点:")
    print("- 逗号分隔多个关键词，每个关键词独立匹配")
    print("- 标准化处理: 去除空格、转为小写")
    print("- 多维度置信度计算，考虑匹配位置和长度")
    print("- 选择置信度最高的匹配结果")
    print("- 规则权重影响最终置信度")
    print()
    print("对于 '零件,part,component,组件,部件,查找,搜索,查询' 规则:")
    print("- 任何包含这些关键词之一的输入都会被匹配")
    print("- 匹配的置信度取决于关键词在输入中的位置和长度")
    print("- 最终返回置信度最高的匹配结果")

if __name__ == "__main__":
    analyze_keyword_matching()
