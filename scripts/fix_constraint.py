import sqlalchemy as sa
from sqlalchemy import create_engine, text
from app.core.config import get_settings

settings = get_settings()
engine = create_engine(settings.database_url)

with engine.connect() as conn:
    print("修复AppIntents表的外键约束...")
    
    # 删除错误的外键约束
    try:
        conn.execute(text('''
            ALTER TABLE app_intents 
            DROP CONSTRAINT IF EXISTS app_intents_fallback_intent_code_fkey;
        '''))
        print("  ✓ 已删除错误的外键约束")
    except Exception as e:
        print(f"  ✗ 删除约束失败: {e}")
    
    # 检查IntentCategories表是否存在
    try:
        result = conn.execute(text('''
            SELECT COUNT(*) FROM intent_categories;
        '''))
        count = result.scalar()
        print(f"  ✓ IntentCategories表存在，有 {count} 条记录")
    except Exception as e:
        print(f"  ✗ 检查IntentCategories表失败: {e}")
    
    # 提交更改
    conn.commit()
    print("  ✓ 约束修复完成")
    
    print("\n现在可以运行初始化脚本来更新分类和配置了。")