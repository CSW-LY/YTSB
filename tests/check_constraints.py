import sqlalchemy as sa
from sqlalchemy import create_engine, text
from app.core.config import get_settings

settings = get_settings()
engine = create_engine(settings.database_url)

with engine.connect() as conn:
    print("AppIntents表的约束:")
    result = conn.execute(text('''
        SELECT conname, conrelid::regclass, confrelid::regclass 
        FROM pg_constraint 
        WHERE conrelid = (SELECT oid FROM pg_class WHERE relname = 'app_intents');
    '''))
    for row in result:
        print(row)
    
    print("\nIntentCategories表的约束:")
    result2 = conn.execute(text('''
        SELECT conname, conrelid::regclass, confrelid::regclass 
        FROM pg_constraint 
        WHERE conrelid = (SELECT oid FROM pg_class WHERE relname = 'intent_categories');
    '''))
    for row in result2:
        print(row)
    
    print("\nAppIntents表的结构:")
    result3 = conn.execute(text('''
        SELECT column_name, data_type, character_maximum_length, column_default, is_nullable 
        FROM information_schema.columns 
        WHERE table_name = 'app_intents';
    '''))
    for row in result3:
        print(row)
    
    print("\nIntentCategories表的数据:")
    result4 = conn.execute(text('''
        SELECT id, code, name, application_id 
        FROM intent_categories 
        ORDER BY id;
    '''))
    for row in result4:
        print(row)
    
    print("\nAppIntents表的数据:")
    result5 = conn.execute(text('''
        SELECT id, app_key, fallback_intent_code, application_id 
        FROM app_intents 
        ORDER BY id;
    '''))
    for row in result5:
        print(row)
