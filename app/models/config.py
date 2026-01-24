"""Configuration and conversation models."""
from datetime import datetime
from sqlalchemy import (
    Boolean, Column, Integer, String, DateTime,
    ForeignKey, Text, JSON, Enum as SQLEnum, Float
)
from sqlalchemy.orm import relationship

from app.db.database import Base
from app.models.enums import ExternalProvider, IngestionRunStatus


class HeuristicConfig(Base):
    """Versioned heuristic configurations."""
    __tablename__ = "heuristic_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Config identity
    name = Column(String(100), nullable=False, index=True)
    version = Column(Integer, nullable=False)
    
    # Config data
    json_blob = Column(JSON, nullable=False)
    description = Column(Text, nullable=True)
    
    # Status
    active = Column(Boolean, default=False, index=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<HeuristicConfig(name='{self.name}', version={self.version}, active={self.active})>"


class ConversationThread(Base):
    """Conversation thread for adaptation chat."""
    __tablename__ = "conversation_threads"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Thread context
    context_type = Column(String(50), nullable=False)  # e.g., "daily_adaptation", "program_setup"
    context_date = Column(DateTime, nullable=True)  # For daily adaptation, the target date
    context_session_id = Column(Integer, ForeignKey("sessions.id"), nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    final_plan_accepted = Column(Boolean, default=False)
    
    # Final accepted plan (JSON snapshot)
    accepted_plan_json = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="conversation_threads")
    turns = relationship("ConversationTurn", back_populates="thread", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ConversationThread(id={self.id}, type='{self.context_type}')>"


class ConversationTurn(Base):
    """Individual turn in a conversation thread."""
    __tablename__ = "conversation_turns"

    id = Column(Integer, primary_key=True, autoincrement=True)
    thread_id = Column(Integer, ForeignKey("conversation_threads.id"), nullable=False, index=True)
    
    # Turn data
    turn_number = Column(Integer, nullable=False)
    role = Column(String(20), nullable=False)  # "user" or "assistant"
    content = Column(Text, nullable=False)
    
    # For assistant turns, the structured response
    structured_response_json = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    thread = relationship("ConversationThread", back_populates="turns")

    def __repr__(self):
        return f"<ConversationTurn(id={self.id}, turn={self.turn_number}, role='{self.role}')>"


class ExternalProviderAccount(Base):
    __tablename__ = "external_provider_accounts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    provider = Column(SQLEnum(ExternalProvider), nullable=False, index=True)
    external_user_id = Column(String(255), nullable=True)
    scopes = Column(JSON, nullable=True)

    access_token_encrypted = Column(Text, nullable=True)
    refresh_token_encrypted = Column(Text, nullable=True)
    token_expires_at = Column(DateTime, nullable=True)

    status = Column(String(50), nullable=False, default="active", index=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ExternalIngestionRun(Base):
    __tablename__ = "external_ingestion_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    provider = Column(SQLEnum(ExternalProvider), nullable=False, index=True)

    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)
    status = Column(SQLEnum(IngestionRunStatus), nullable=False, default=IngestionRunStatus.RUNNING, index=True)

    error = Column(Text, nullable=True)
    cursor_json = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)


class ExternalActivityRecord(Base):
    __tablename__ = "external_activity_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    provider = Column(SQLEnum(ExternalProvider), nullable=False, index=True)
    external_id = Column(String(255), nullable=False, index=True)

    activity_type_raw = Column(String(255), nullable=True)
    start_time = Column(DateTime, nullable=True, index=True)
    end_time = Column(DateTime, nullable=True)
    timezone = Column(String(64), nullable=True)
    
    # Queryable metrics (denormalized from payload)
    distance_meters = Column(Float, nullable=True)
    elevation_gain_meters = Column(Float, nullable=True)
    calories = Column(Integer, nullable=True)
    average_hr = Column(Integer, nullable=True)
    max_hr = Column(Integer, nullable=True)
    average_watts = Column(Integer, nullable=True)
    device_name = Column(String(100), nullable=True)

    raw_payload_json = Column(JSON, nullable=True)
    ingestion_run_id = Column(Integer, ForeignKey("external_ingestion_runs.id"), nullable=True, index=True)

    created_at = Column(DateTime, default=datetime.utcnow)


class ExternalMetricStream(Base):
    __tablename__ = "external_metric_streams"

    id = Column(Integer, primary_key=True, autoincrement=True)
    external_activity_record_id = Column(Integer, ForeignKey("external_activity_records.id"), nullable=False, index=True)
    stream_type = Column(String(100), nullable=False, index=True)
    raw_stream_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
