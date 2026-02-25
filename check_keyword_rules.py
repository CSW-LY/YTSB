from app.database.session import get_db
from app.models.database import IntentCategory, IntentRule

db = next(get_db())
categories = db.query(IntentCategory).filter_by(is_active=True).all()
rules = db.query(IntentRule).filter_by(rule_type='keyword', is_active=True).all()

print('=== Active Keyword Rules ===')
for rule in rules:
    category = next((c for c in categories if c.id == rule.category_id), None)
    if category:
        print(f'Category: {category.code} - {category.name}')
        print(f'  Rule: {rule.content}')
        print(f'  Weight: {rule.weight}')
        print()
