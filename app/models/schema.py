"""Pydantic schemas for API request/response models."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


# ============================================================================
# Base Schemas
# ============================================================================

class ApplicationBase(BaseModel):
    """Base schema for application."""

    app_key: str = Field(..., description="Unique application key", min_length=1, max_length=100)
    name: str = Field(..., description="Application name", min_length=1, max_length=200)
    description: Optional[str] = Field(None, description="Application description")
    enable_keyword: bool = Field(default=True, description="Enable keyword matching")
    enable_regex: bool = Field(default=True, description="Enable regex matching")
    enable_semantic: bool = Field(default=True, description="Enable semantic matching")
    enable_llm_fallback: bool = Field(default=False, description="Enable LLM fallback")
    enable_cache: bool = Field(default=True, description="Enable recognition result caching")
    fallback_intent_code: Optional[str] = Field(None, description="Fallback intent code when no rules match", max_length=50)
    confidence_threshold: float = Field(default=0.7, ge=0, le=1, description="Confidence threshold for recognition results")

class IntentCategoryBase(BaseModel):
    """Base schema for intent category."""

    application_id: int = Field(..., description="Application ID")
    code: str = Field(..., description="Unique intent code within application", min_length=1, max_length=50)
    name: str = Field(..., description="Human-readable name", min_length=1, max_length=100)
    description: Optional[str] = Field(None, description="Detailed description")
    priority: int = Field(default=0, ge=0, description="Priority for matching order")

class IntentRuleBase(BaseModel):
    """Base schema for intent rule."""

    category_id: int = Field(..., description="Associated category ID")
    rule_type: str = Field(..., description="Rule type: keyword, regex, or semantic")
    content: str = Field(..., description="Rule content (keyword, pattern, or example)")
    weight: float = Field(default=1.0, ge=0, le=10, description="Rule weight for scoring")

# ============================================================================
# Request Schemas
# ============================================================================

class RecognizeRequest(BaseModel):
    """Request schema for intent recognition."""

    app_key: str = Field(..., description="Application key", min_length=1, max_length=100)
    text: str = Field(..., description="User input text to analyze", min_length=1)
    context: Optional[Dict[str, Any]] = Field(default=None, description="Additional context (user_id, session_id, etc.)")

    @field_validator("text")
    @classmethod
    def sanitize_text(cls, v: str) -> str:
        """Sanitize input text."""
        # Remove excessive whitespace
        return " ".join(v.split())


class BatchRecognizeRequest(BaseModel):
    """Request schema for batch intent recognition."""

    app_key: str = Field(..., description="Application key", min_length=1, max_length=100)
    texts: List[str] = Field(..., description="List of texts to analyze", min_length=1, max_length=100)


# ============================================================================
# Response Schemas
# ============================================================================

class MatchedRule(BaseModel):
    """Matched rule information."""

    id: int
    rule_type: str
    content: str
    weight: float


class RecognizeResponse(BaseModel):
    """Response schema for intent recognition."""

    intent: Optional[str] = Field(None, description="Matched intent code")
    confidence: Optional[float] = Field(None, ge=0, le=1, description="Confidence score")
    entities: Dict[str, Any] = Field(default_factory=dict, description="Extracted entities")
    matched_rules: List[MatchedRule] = Field(default_factory=list, description="Matched rules")
    cached: bool = Field(default=False, description="Whether result was from cache")
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")
    recognition_chain: List[Dict[str, Any]] = Field(default_factory=list, description="Recognition chain steps")

    success: bool = Field(default=True, description="Whether recognition was successful")
    fallback_used: bool = Field(default=False, description="Whether fallback intent was used")
    fallback_reason: Optional[str] = Field(None, description="Reason for fallback usage")
    final_recognizer: Optional[str] = Field(None, description="Final recognizer that matched intent")
    failure_reason: Optional[str] = Field(None, description="Reason for failure")
    failure_type: Optional[str] = Field(None, description="Type of failure")
    threshold: Optional[float] = Field(None, description="Required confidence threshold")
    suggestion: Optional[str] = Field(None, description="Suggestion for fixing the issue")
    llm_error: Optional[str] = Field(None, description="LLM error message (if any)")
    llm_error_reason: Optional[str] = Field(None, description="LLM error reason code (if any)")


class RecognitionFailureResponse(BaseModel):
    """Response schema for recognition failure with detailed information."""

    success: bool = Field(default=False, description="Recognition failed")
    intent: Optional[str] = Field(None, description="Matched intent code (if any)")
    confidence: Optional[float] = Field(None, description="Confidence score (if any)")
    failure_reason: str = Field(..., description="Reason for failure")
    failure_type: str = Field(..., description="Type of failure: no_match, low_confidence, system_error, config_missing")
    recognition_chain: List[Dict[str, Any]] = Field(default_factory=list, description="Full recognition chain")
    matched_rules: List[MatchedRule] = Field(default_factory=list, description="Matched rules (if any)")
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")
    threshold: Optional[float] = Field(None, description="Required confidence threshold")
    suggestion: Optional[str] = Field(None, description="Suggestion for fixing the issue")
    llm_error: Optional[str] = Field(None, description="LLM error message (if any)")
    llm_error_reason: Optional[str] = Field(None, description="LLM error reason code (if any)")


class BatchRecognizeResponse(BaseModel):
    """Response schema for batch intent recognition."""

    results: List[RecognizeResponse]
    total_count: int
    cached_count: int


class ApplicationResponse(ApplicationBase):
    """Response schema for application."""

    id: int
    is_active: bool
    enable_keyword: bool
    enable_regex: bool
    enable_semantic: bool
    enable_llm_fallback: bool
    enable_cache: bool
    fallback_intent_code: Optional[str]
    confidence_threshold: float
    created_at: datetime
    updated_at: datetime

class IntentCategoryResponse(IntentCategoryBase):
    """Response schema for intent category."""

    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class IntentRuleResponse(IntentRuleBase):
    """Response schema for intent rule."""

    id: int
    is_active: bool
    enabled: bool
    created_at: datetime
    updated_at: datetime


# ============================================================================
# Create/Update Schemas
# ============================================================================

class ApplicationCreate(ApplicationBase):
    """Schema for creating application."""

    pass

class ApplicationUpdate(BaseModel):
    """Schema for updating application."""

    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    is_active: Optional[bool] = None
    enable_keyword: Optional[bool] = Field(None, description="Enable keyword matching")
    enable_regex: Optional[bool] = Field(None, description="Enable regex matching")
    enable_semantic: Optional[bool] = Field(None, description="Enable semantic matching")
    enable_llm_fallback: Optional[bool] = Field(None, description="Enable LLM fallback")
    enable_cache: Optional[bool] = Field(None, description="Enable recognition result caching")
    fallback_intent_code: Optional[str] = Field(None, description="Fallback intent code when no rules match", max_length=50)
    confidence_threshold: Optional[float] = Field(None, ge=0, le=1, description="Confidence threshold for recognition results")

    @field_validator("enable_keyword", "enable_regex", "enable_semantic", "enable_llm_fallback")
    @classmethod
    def validate_matching_strategy(cls, v: Optional[bool], info) -> Optional[bool]:
        """Validate that at least one matching strategy is enabled."""
        if v is None:
            return v
        
        return v

    def model_post_init(self, __context: Any) -> None:
        """Validate that at least one matching strategy is enabled when updating."""
        matching_fields = [
            self.enable_keyword,
            self.enable_regex,
            self.enable_semantic,
        ]
        
        updated_matching_fields = [f for f in matching_fields if f is not None]
        
        if updated_matching_fields and not any(updated_matching_fields) and not self.enable_llm_fallback:
            raise ValueError(
                "At least one matching strategy (keyword, regex, or semantic) must be enabled"
            )

class IntentCategoryCreate(IntentCategoryBase):
    """Schema for creating intent category."""

    pass


class IntentCategoryUpdate(BaseModel):
    """Schema for updating intent category."""

    code: Optional[str] = Field(None, min_length=1, max_length=50)
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    priority: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None


class IntentRuleCreate(IntentRuleBase):
    """Schema for creating intent rule."""

    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")


class IntentRuleUpdate(BaseModel):
    """Schema for updating intent rule."""

    category_id: Optional[int] = None
    rule_type: Optional[str] = None
    content: Optional[str] = None
    weight: Optional[float] = Field(None, ge=0, le=10)
    is_active: Optional[bool] = None
    enabled: Optional[bool] = None

# ============================================================================
# Health Check Schemas
# ============================================================================

class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., description="Service status: healthy, degraded, or unhealthy")
    version: str
    timestamp: datetime
    dependencies: Dict[str, str] = Field(default_factory=dict)


class ReadyResponse(BaseModel):
    """Readiness check response."""

    ready: bool
    is_model_loaded: bool
    database_connected: bool
    cache_connected: bool


# ============================================================================
# API Key Schemas
# ============================================================================

class ApiKeyBase(BaseModel):
    """Base schema for API key."""

    description: Optional[str] = Field(None, description="API key description")
    rate_limit: int = Field(default=1000, ge=1, description="Requests per minute limit")
    app_keys: Optional[List[str]] = Field(None, description="Allowed application keys")
    expires_at: Optional[datetime] = Field(None, description="Expiration time")


class ApiKeyCreate(ApiKeyBase):
    """Schema for creating API key."""

    permissions: Dict[str, Any] = Field(default_factory=dict, description="API key permissions")


class ApiKeyUpdate(BaseModel):
    """Schema for updating API key."""

    description: Optional[str] = None
    permissions: Optional[Dict[str, Any]] = None
    rate_limit: Optional[int] = Field(None, ge=1)
    app_keys: Optional[List[str]] = None
    expires_at: Optional[datetime] = None
    is_active: Optional[bool] = None


class ApiKeyResponse(ApiKeyBase):
    """Response schema for API key."""

    id: int
    key_prefix: str
    full_key: str
    permissions: Dict[str, Any]
    is_active: bool
    created_at: datetime
    last_used_at: Optional[datetime]


class ApiKeyCreateResponse(ApiKeyResponse):
    """Response schema for created API key (includes the actual key)."""

    api_key: str = Field(..., description="Generated API key (only returned once)")


class ApiKeyListResponse(BaseModel):
    """Response schema for API key list."""

    items: List[ApiKeyResponse]
    total_items: int
    total_pages: int
    current_page: int
    page_size: int
