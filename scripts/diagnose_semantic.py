"""诊断语义识别问题。"""
import asyncio
import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from sqlalchemy import text
from app.db import async_session_maker
from app.core.config import get_settings
from app.ml.embedding import EmbeddingModel


async def diagnose():
    """诊断语义识别问题。"""
    settings = get_settings()
    
    print("=" * 60)
    print("语义识别诊断")
    print("=" * 60)
    
    # 1. 检查配置
    print("\n1. 检查配置...")
    print(f"   模型类型: {settings.model_type}")
    print(f"   模型路径: {settings.model_path}")
    print(f"   模型设备: {settings.model_device}")
    print(f"   启用语义匹配: {settings.enable_semantic_matching}")
    print(f"   语义相似度阈值: {settings.semantic_similarity_threshold}")
    
    # 2. 检查语义规则
    print("\n2. 检查语义规则...")
    async with async_session_maker() as session:
        result = await session.execute(text("""
            SELECT 
                ic.code,
                ic.name,
                COUNT(*) as semantic_count
            FROM intent_rules ir
            JOIN intent_categories ic ON ir.category_id = ic.id
            WHERE ir.rule_type = 'semantic' AND ir.is_active = true
            GROUP BY ic.code, ic.name
            ORDER BY semantic_count DESC;
        """))
        
        semantic_rules = result.fetchall()
        
        if semantic_rules:
            print(f"   找到 {len(semantic_rules)} 个分类有语义规则:")
            total = 0
            for rule in semantic_rules:
                print(f"     - {rule[1]} ({rule[0]}): {rule[2]} 条语义规则")
                total += rule[2]
            print(f"   总计: {total} 条语义规则")
        else:
            print("   ⚠️  未找到任何语义规则")
    
    # 3. 测试模型加载
    print("\n3. 测试模型加载...")
    try:
        embedding_model = EmbeddingModel(
            model_path=settings.model_path,
            model_name=settings.model_type,
            device=settings.model_device
        )
        
        print("   正在加载模型...")
        await embedding_model.load()
        print(f"   ✓ 模型加载成功")
        print(f"   ✓ 向量维度: {embedding_model.dimension}")
        
        # 4. 测试编码
        print("\n4. 测试文本编码...")
        test_texts = [
            "帮我看看图号零部件资料",
            "我想查一下这个零件的信息",
            "帮我找一下技术图纸",
            "显示一下BOM表",
        ]
        
        embeddings = embedding_model.encode(test_texts)
        print(f"   ✓ 成功编码 {len(test_texts)} 个文本")
        print(f"   ✓ 编码结果形状: {embeddings.shape}")
        
        # 5. 计算相似度
        print("\n5. 计算语义相似度...")
        async with async_session_maker() as session:
            result = await session.execute(text("""
                SELECT 
                    ic.code,
                    ic.name,
                    ir.content,
                    ir.weight
                FROM intent_rules ir
                JOIN intent_categories ic ON ir.category_id = ic.id
                WHERE ir.rule_type = 'semantic' AND ir.is_active = true
                ORDER BY ic.code, ir.id
                LIMIT 10;
            """))
            
            sample_rules = result.fetchall()
            
            if sample_rules:
                print(f"   找到 {len(sample_rules)} 条语义规则示例")
                
                # 对每个测试文本计算相似度
                from sklearn.metrics.pairwise import cosine_similarity
                
                for test_text in test_texts:
                    test_emb = embedding_model.encode(test_text)
                    if test_emb.ndim == 1:
                        test_emb = test_emb.reshape(1, -1)
                    
                    print(f"\n   测试文本: \"{test_text}\"")
                    similarities = []
                    
                    for rule in sample_rules[:5]:  # 只显示前5个
                        rule_emb = embedding_model.encode(rule[2])
                        if rule_emb.ndim == 1:
                            rule_emb = rule_emb.reshape(1, -1)
                        
                        similarity = cosine_similarity(test_emb, rule_emb)[0][0] * rule[3]
                        similarities.append(similarity)
                        
                        if similarity > settings.semantic_similarity_threshold:
                            print(f"     → {rule[1]} ({rule[0]}): {similarity:.3f} (超过阈值)")
                        else:
                            print(f"     → {rule[1]} ({rule[0]}): {similarity:.3f}")
                    
                    if similarities:
                        max_sim = max(similarities)
                        print(f"   最高相似度: {max_sim:.3f} (阈值: {settings.semantic_similarity_threshold})")
                        if max_sim >= settings.semantic_similarity_threshold:
                            print(f"   ✓ 可以识别为该意图")
                        else:
                            print(f"   ✗ 低于阈值，无法识别")
        
        # 6. 诊断建议
        print("\n6. 诊断建议:")
        if not semantic_rules:
            print("   ⚠️  没有语义规则数据，请先创建语义规则")
        else:
            print("   ✓ 语义规则数据正常")
        
        if embedding_model.is_loaded:
            print("   ✓ 模型加载正常")
        else:
            print("   ✗ 模型未加载，请检查模型路径和设备设置")
        
        if settings.semantic_similarity_threshold > 0.8:
            print(f"   ⚠️  阈值 {settings.semantic_similarity_threshold} 较高，可能导致识别困难")
            print("   建议: 可以将阈值降低到 0.6-0.7")
        elif settings.semantic_similarity_threshold < 0.5:
            print(f"   ⚠️  阈值 {settings.semantic_similarity_threshold} 较低，可能导致误识别")
            print("   建议: 可以将阈值提高到 0.7-0.8")
        else:
            print(f"   ✓ 阈值 {settings.semantic_similarity_threshold} 设置合理")
        
        await embedding_model.unload()
        
    except Exception as e:
        print(f"\n✗ 诊断失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    try:
        asyncio.run(diagnose())
    except Exception as e:
        print(f"\n✗ 诊断失败: {e}")
        sys.exit(1)
