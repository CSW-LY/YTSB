"""
简化的数据库迁移脚本，添加新字段到applications表。
"""

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT


def connect_db():
    """连接到PostgreSQL数据库。"""
    try:
        conn = psycopg2.connect(
            host="localhost",
            port=5432,
            database="intent_service",
            user="postgres",
            password="123"
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        print("✓ 连接数据库成功")
        return conn
    except Exception as e:
        print(f"✗ 连接数据库失败: {e}")
        exit(1)


def add_fields_to_applications(conn):
    """添加字段到applications表。"""
    cursor = conn.cursor()
    
    fields = [
        ("enable_cache", "BOOLEAN DEFAULT TRUE"),
        ("fallback_intent_code", "VARCHAR(50)"),
        ("confidence_threshold", "FLOAT DEFAULT 0.7")
    ]
    
    for field_name, field_type in fields:
        try:
            cursor.execute(f"""
                ALTER TABLE applications 
                ADD COLUMN IF NOT EXISTS {field_name} {field_type}
            """)
            print(f"✓ 添加字段 {field_name} 成功")
        except Exception as e:
            print(f"  字段 {field_name} 已存在或添加失败: {e}")
    
    cursor.close()


def verify_migration(conn):
    """验证迁移结果。"""
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_name = 'applications'
            AND column_name IN ('enable_cache', 'fallback_intent_code', 'confidence_threshold')
            ORDER BY column_name
        """)
        
        columns = cursor.fetchall()
        
        if len(columns) == 3:
            print("\n✓ 迁移验证成功！")
            print("新添加的字段:")
            for col in columns:
                print(f"  - {col[0]}: {col[1]} (nullable: {col[2]}, default: {col[3]})")
        else:
            print(f"\n✗ 验证失败：期望3个字段，实际找到{len(columns)}个")
    except Exception as e:
        print(f"\n✗ 验证失败: {e}")
    finally:
        cursor.close()


def main():
    """主函数。"""
    print("开始数据库迁移...")
    conn = connect_db()
    
    try:
        add_fields_to_applications(conn)
        verify_migration(conn)
        print("\n✓ 迁移完成！")
    finally:
        conn.close()
        print("✓ 数据库连接已关闭")


if __name__ == "__main__":
    main()
