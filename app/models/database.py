"""SQLAlchemy database models for intent service."""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    ARRAY,
    Boolean,
    Column,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """Base class for all models."""

    pass


class Application(Base):
    """Application model for managing app-level categories."""

    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    app_key = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    
    # Rule strategy configuration fields
    enable_keyword = Column(Boolean, default=True, nullable=False)
    enable_regex = Column(Boolean, default=True, nullable=False)
    enable_semantic = Column(Boolean, default=True, nullable=False)
    enable_llm_fallback = Column(Boolean, default=False, nullable=False)

    # Intent recognition configuration fields
    enable_cache = Column(Boolean, default=True)
    fallback_intent_code = Column(String(50), nullable=True)
    confidence_threshold = Column(Float, default=0.7)

    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(
        TIMESTAMP,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    categories = relationship("IntentCategory", back_populates="application", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Application(id={self.id}, app_key={self.app_key}, name={self.name})>"


class IntentCategory(Base):
    """Intent category (classification) model - app scoped."""

    __tablename__ = "intent_categories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    application_id = Column(Integer, ForeignKey("applications.id", ondelete="CASCADE"), nullable=False)
    code = Column(String(50), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    priority = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(
        TIMESTAMP,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    application = relationship("Application", back_populates="categories")
    rules = relationship("IntentRule", back_populates="category", cascade="all, delete-orphan")

    # Composite unique constraint
    __table_args__ = (
        UniqueConstraint('application_id', 'code', name='uq_application_category_code'),
    )

    def __repr__(self) -> str:
        return f"<IntentCategory(id={self.id}, application_id={self.application_id}, code={self.code}, name={self.name})>"


class IntentRule(Base):
    """Intent rule configuration model."""

    __tablename__ = "intent_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    category_id = Column(Integer, ForeignKey("intent_categories.id", ondelete="CASCADE"), nullable=False)
    rule_type = Column(String(20), nullable=False)  # keyword, regex, semantic
    content = Column(Text, nullable=False)
    weight = Column(Float, default=1.0)
    rule_metadata = Column(Text, nullable=True)  # JSON string for additional config
    is_active = Column(Boolean, default=True)
    enabled = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(
        TIMESTAMP,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    category = relationship("IntentCategory", back_populates="rules")

    def __repr__(self) -> str:
        return f"<IntentRule(type={self.rule_type}, category_id={self.category_id})>"


class IntentRecognitionLog(Base):
    """Intent recognition log model."""

    __tablename__ = "intent_recognition_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    app_key = Column(String(100), nullable=False, index=True)
    api_key_id = Column(Integer, nullable=True, index=True)  # 关联API密钥
    input_text = Column(Text, nullable=False)
    recognized_intent = Column(String(50), nullable=True)
    confidence = Column(Float, nullable=True)
    processing_time_ms = Column(Float, nullable=True)
    is_success = Column(Boolean, nullable=False)
    error_message = Column(Text, nullable=True)
    recognition_chain = Column(Text, nullable=True)  # JSON string
    matched_rules = Column(Text, nullable=True)  # JSON string
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)

    def __repr__(self) -> str:
        return f"<IntentRecognitionLog(app_key={self.app_key}, intent={self.recognized_intent}, success={self.is_success})>"


class ApiKey(Base):
    """API key management model."""

    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key_hash = Column(String(255), unique=True, nullable=False, index=True)
    key_prefix = Column(String(20), nullable=False, index=True)  # 用于识别密钥
    full_key = Column(String(255), nullable=False)  # 完整API密钥（仅存储，不用于认证）
    description = Column(String(255), nullable=True)
    permissions = Column(Text, nullable=False)  # JSON格式的权限配置
    rate_limit = Column(Integer, default=1000)  # 每分钟请求限制
    app_keys = Column(ARRAY(String), nullable=True)  # 允许访问的APP列表
    expires_at = Column(TIMESTAMP, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    last_used_at = Column(TIMESTAMP, nullable=True)

    def __repr__(self) -> str:
        return f"<ApiKey(key_prefix={self.key_prefix}, description={self.description})>"
