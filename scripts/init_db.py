"""Database initialization script - Simple synchronous version."""

import logging
import sys

# Add parent directory to path for imports
sys.path.insert(0, ".")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.models.database import AppIntent, Base, IntentCategory, IntentRule

logging.basicConfig(level=logging.INFO, format='%(message)s')
settings = get_settings()

print("=" * 50)
print("Database Initialization Script")
print("=" * 50)
print(f"Database: {settings.db_name}")
print(f"Host: {settings.db_host}:{settings.db_port}")
print(f"User: {settings.db_user}")
print("=" * 50)
print()

# Use sync engine for simplicity
sync_url = f"postgresql+psycopg2://{settings.db_user}:{settings.db_password}@{settings.db_host}:{settings.db_port}/{settings.db_name}"
engine = create_engine(sync_url, echo=True)
Session = sessionmaker(bind=engine)


def create_tables():
    """Create all database tables."""
    print("Creating database tables...")
    Base.metadata.create_all(engine)
    print("Done!")


def drop_tables():
    """Drop all database tables."""
    if not input("This will delete all data. Type 'yes' to confirm: ").lower() == "yes":
        print("Aborted")
        return

    print("Dropping database tables...")
    Base.metadata.drop_all(engine)
    print("Done!")


def seed_data():
    """Insert sample data."""
    print("Inserting sample data...")

    with Session() as session:
        # Create or get application
        print("Creating or getting application...")
        from app.models.database import Application
        from sqlalchemy import select
        
        # Check if application exists
        result = session.execute(select(Application).where(Application.app_key == "plm_assistant"))
        application = result.scalar_one_or_none()
        
        if not application:
            application = Application(
                app_key="plm_assistant",
                name="PLM Assistant",
                description="PLM 智能助手应用"
            )
            session.add(application)
            session.flush()
            print("  Created application")
        else:
            print("  Using existing application")

        # Delete existing categories for this application
        print("Deleting existing categories...")
        from app.models.database import IntentCategory, IntentRule
        
        # Delete rules first (due to foreign key constraint)
        result = session.execute(
            select(IntentRule).join(IntentCategory).where(IntentCategory.application_id == application.id)
        )
        rules_to_delete = result.scalars().all()
        for rule in rules_to_delete:
            session.delete(rule)
        print(f"  Deleted {len(rules_to_delete)} rules")
        
        # Delete categories
        result = session.execute(select(IntentCategory).where(IntentCategory.application_id == application.id))
        categories_to_delete = result.scalars().all()
        for cat in categories_to_delete:
            session.delete(cat)
        print(f"  Deleted {len(categories_to_delete)} categories")
        
        session.flush()

        # Create categories
        print("Creating intent categories...")
        categories = [
            IntentCategory(application_id=application.id, code="bom.query", name="BOM查询", description="查询BOM结构、物料清单等信息", priority=100),
            IntentCategory(application_id=application.id, code="bom.modify", name="BOM修改", description="修改BOM结构、添加或删除物料", priority=90),
            IntentCategory(application_id=application.id, code="SEARCH_PART", name="零件搜索", description="搜索零件、查看零件详情", priority=100),
            IntentCategory(application_id=application.id, code="part.create", name="零件创建", description="创建新零件、定义零件属性", priority=80),
            IntentCategory(application_id=application.id, code="workflow.approve", name="流程审批", description="审批流程、查看审批状态", priority=70),
            IntentCategory(application_id=application.id, code="drawing.view", name="图纸查看", description="查看工程图纸、CAD文件", priority=60),
            IntentCategory(application_id=application.id, code="ecr.submit", name="ECR提交", description="提交工程变更请求", priority=70),
        ]

        for cat in categories:
            session.add(cat)

        session.flush()
        print(f"  Created {len(categories)} categories")

        # Create rules
        print("Creating intent rules...")
        rules = [
            # BOM Query
            IntentRule(category_id=categories[0].id, rule_type="keyword", content="查询bom", weight=1.0),
            IntentRule(category_id=categories[0].id, rule_type="keyword", content="查看bom", weight=1.0),
            IntentRule(category_id=categories[0].id, rule_type="keyword", content="bom结构", weight=0.9),

            # BOM Modify
            IntentRule(category_id=categories[1].id, rule_type="keyword", content="修改bom", weight=1.0),

            # Part Search
            IntentRule(category_id=categories[2].id, rule_type="keyword", content="搜索零件", weight=1.0),
            IntentRule(category_id=categories[2].id, rule_type="keyword", content="找零件", weight=1.0),
            IntentRule(category_id=categories[2].id, rule_type="keyword", content="查找零件", weight=1.0),

            # Part Create
            IntentRule(category_id=categories[3].id, rule_type="keyword", content="创建零件", weight=1.0),

            # Workflow Approve
            IntentRule(category_id=categories[4].id, rule_type="keyword", content="审批", weight=1.0),

            # Drawing View
            IntentRule(category_id=categories[5].id, rule_type="keyword", content="图纸", weight=0.9),

            # ECR Submit
            IntentRule(category_id=categories[6].id, rule_type="keyword", content="ecr", weight=1.0),
        ]

        for rule in rules:
            session.add(rule)

        session.flush()
        print(f"  Created {len(rules)} rules")

        # Create or update app config
        print("Creating or updating app configuration...")
        
        # Check if app config exists
        from sqlalchemy import select
        result = session.execute(select(AppIntent).where(AppIntent.app_key == "plm_assistant"))
        app_config = result.scalar_one_or_none()
        
        if not app_config:
            app_config = AppIntent(
            application_id=application.id,
            app_key="plm_assistant",
            intent_ids=[c.id for c in categories],
            fallback_intent_code="SEARCH_PART",
            confidence_threshold=0.7,
        )
            session.add(app_config)
            print("  Created app configuration")
        else:
            # Update existing app config
            app_config.application_id = application.id
            app_config.intent_ids = [c.id for c in categories]
            app_config.fallback_intent_code = "SEARCH_PART"
            app_config.confidence_threshold = 0.7
            print("  Updated app configuration")

        session.commit()
        print("  App configuration saved")

    print("Done!")


def show_status():
    """Show database status."""
    from sqlalchemy import text, func

    print("Checking database status...")

    with Session() as session:
        # List tables
        result = session.execute(text("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name
        """))
        tables = [row[0] for row in result]
        print(f"  Tables: {tables}")

        if not tables:
            print("  No tables found! Run 'init' first.")
            return

        # Count records
        cat_count = session.scalar(func.count(IntentCategory.id))
        rule_count = session.scalar(func.count(IntentRule.id))
        app_count = session.scalar(func.count(AppIntent.id))

        print()
        print("  Intent Categories:", cat_count or 0)
        print("  Intent Rules:", rule_count or 0)
        print("  App Configs:", app_count or 0)


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("""
Usage: python scripts/init_db.py <command>

Commands:
  init      Create database tables
  seed      Insert sample data
  reset      Reset database (drop and recreate)
  drop       Drop all tables
  status     Show database status
  setup      Full setup (init + seed)
        """)
        return

    command = sys.argv[1].lower()

    try:
        if command == "init":
            create_tables()
        elif command == "seed":
            seed_data()
        elif command == "reset":
            drop_tables()
            create_tables()
            seed_data()
        elif command == "drop":
            drop_tables()
        elif command == "status":
            show_status()
        elif command == "setup":
            create_tables()
            seed_data()
        else:
            print(f"Unknown command: {command}")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
