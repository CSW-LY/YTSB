"""Models module for database and API schemas."""

from app.models.database import (
    Base,
    IntentCategory,
    IntentRule,
)
from app.models.schema import (
    BatchRecognizeRequest,
    BatchRecognizeResponse,
    HealthResponse,
    IntentCategoryCreate,
    IntentCategoryResponse,
    IntentCategoryUpdate,
    IntentRuleCreate,
    IntentRuleResponse,
    IntentRuleUpdate,
    MatchedRule,
    ReadyResponse,
    RecognizeRequest,
    RecognizeResponse,
)

__all__ = [
    # Database models
    "Base",
    "IntentCategory",
    "IntentRule",
    # Request schemas
    "RecognizeRequest",
    "BatchRecognizeRequest",
    "IntentCategoryCreate",
    "IntentCategoryUpdate",
    "IntentRuleCreate",
    "IntentRuleUpdate",
    # Response schemas
    "RecognizeResponse",
    "BatchRecognizeResponse",
    "MatchedRule",
    "IntentCategoryResponse",
    "IntentRuleResponse",
    "HealthResponse",
    "ReadyResponse",
]
