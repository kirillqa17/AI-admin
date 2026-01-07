"""
SQLAlchemy models для multi-tenant архитектуры
"""

from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import Column, String, Boolean, DateTime, Integer, Text, ForeignKey, DECIMAL
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, declarative_base
import uuid


def utcnow():
    """Helper function for SQLAlchemy default"""
    return datetime.now(timezone.utc)

Base = declarative_base()


class Company(Base):
    """Компания - клиент SAAS"""
    __tablename__ = "companies"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    phone = Column(String(50))
    
    # Subscription
    subscription_plan = Column(String(50), default="free")
    subscription_status = Column(String(50), default="active")
    subscription_expires_at = Column(DateTime)
    
    # Metadata
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
    is_active = Column(Boolean, default=True)
    
    billing_email = Column(String(255))
    
    # Relationships
    crm_settings = relationship("CompanyCRMSettings", back_populates="company", uselist=False)
    agent_settings = relationship("CompanyAgentSettings", back_populates="company", uselist=False)
    channels = relationship("CompanyChannel", back_populates="company")
    sessions = relationship("Session", back_populates="company")


class CompanyCRMSettings(Base):
    """Настройки CRM для компании"""
    __tablename__ = "company_crm_settings"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, unique=True)
    
    # CRM Configuration
    crm_type = Column(String(50), nullable=False)
    api_key_encrypted = Column(Text, nullable=False)
    base_url = Column(String(500))
    company_id_in_crm = Column(String(255))
    
    additional_settings = Column(JSONB, default={})
    
    # Status
    is_active = Column(Boolean, default=True)
    last_sync_at = Column(DateTime)
    last_sync_status = Column(String(50))
    last_sync_error = Column(Text)
    
    # Metadata
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
    
    # Relationships
    company = relationship("Company", back_populates="crm_settings")


class CompanyAgentSettings(Base):
    """Настройки AI агента для компании"""
    __tablename__ = "company_agent_settings"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, unique=True)
    
    # Company Information
    company_description = Column(Text)
    business_type = Column(String(100))
    target_audience = Column(Text)
    working_hours = Column(String(500))
    address = Column(Text)
    phone_display = Column(String(50))

    # Business Context (для AI агента)
    services_catalog = Column(JSONB, default=list)
    products_catalog = Column(JSONB, default=list)
    business_highlights = Column(Text)

    # Agent Behavior
    greeting_message = Column(Text)
    farewell_message = Column(Text)
    custom_instructions = Column(Text)
    
    # AI Settings
    temperature = Column(DECIMAL(3, 2), default=0.7)
    max_tokens = Column(Integer, default=8192)
    model_name = Column(String(100), default="gemini-2.0-flash-exp")
    
    # Custom Prompts
    custom_prompts = Column(JSONB, default={})
    
    # Features
    features = Column(JSONB, default={"auto_booking": True, "consultation": True, "reminders": True})
    
    # Metadata
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
    
    # Relationships
    company = relationship("Company", back_populates="agent_settings")


class CompanyChannel(Base):
    """Каналы коммуникации компании"""
    __tablename__ = "company_channels"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    
    # Channel Info
    channel_type = Column(String(50), nullable=False)
    channel_name = Column(String(255))
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Config
    config = Column(JSONB, default={})
    
    # Webhook
    webhook_token = Column(String(255), unique=True)
    webhook_url = Column(String(500))
    
    # Statistics
    messages_received = Column(Integer, default=0)
    messages_sent = Column(Integer, default=0)
    last_activity_at = Column(DateTime)
    
    # Metadata
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
    
    # Relationships
    company = relationship("Company", back_populates="channels")


class Session(Base):
    """Сессия диалога"""
    __tablename__ = "sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    
    # User Info
    user_id = Column(String(255), nullable=False)
    channel = Column(String(50), nullable=False)
    
    # State
    state = Column(String(50), default="INITIATED")
    context = Column(JSONB, default={})
    
    # CRM linkage
    crm_client_id = Column(String(255))
    crm_appointment_id = Column(String(255))
    
    # Timestamps
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
    last_activity_at = Column(DateTime, default=utcnow)
    expires_at = Column(DateTime)
    
    # Relationships
    company = relationship("Company", back_populates="sessions")
    messages = relationship("Message", back_populates="session")


class Message(Base):
    """Сообщение"""
    __tablename__ = "messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    
    # Message Info
    channel = Column(String(50), nullable=False)
    message_type = Column(String(50), default="text")
    
    # Content
    text = Column(Text)
    audio_url = Column(String(500))
    image_url = Column(String(500))
    file_url = Column(String(500))
    
    # Sender
    is_from_bot = Column(Boolean, default=False)
    from_user_id = Column(String(255))
    from_user_name = Column(String(255))
    
    # Metadata
    metadata = Column(JSONB, default={})
    created_at = Column(DateTime, default=utcnow)
    
    # Relationships
    session = relationship("Session", back_populates="messages")
