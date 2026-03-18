# app/db/models.py
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Boolean, Integer, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, DeclarativeBase
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
    email = Column(String(320), nullable=False, unique=True, index=True)
    hashed_password = Column(String(200), nullable=False)
    tier = Column(String(20), nullable=False, default="free")
    preferred_stack = Column(String(200), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")


class Session(Base):
    __tablename__ = "sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    project_name = Column(String(200), nullable=False)
    prd_content = Column(Text, nullable=False)
    chosen_stack = Column(String(200), nullable=True)
    status = Column(String(50), nullable=False, default="active")
    pr_url = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="sessions")
    messages = relationship("MessageHistory", back_populates="session", cascade="all, delete-orphan")
    hitl_decisions = relationship("HitlDecision", back_populates="session", cascade="all, delete-orphan")
    reflexion_logs = relationship("ReflexionLog", back_populates="session", cascade="all, delete-orphan")


class MessageHistory(Base):
    __tablename__ = "message_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role = Column(String(20), nullable=False)  # user|assistant|system
    content = Column(Text, nullable=False)
    agent_name = Column(String(100), nullable=True)
    token_count = Column(Integer, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    session = relationship("Session", back_populates="messages")


class HitlDecision(Base):
    __tablename__ = "hitl_decisions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    checkpoint_name = Column(String(100), nullable=False)
    user_decision = Column(Boolean, nullable=False)
    user_feedback = Column(Text, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    session = relationship("Session", back_populates="hitl_decisions")


class ReflexionLog(Base):
    __tablename__ = "reflexion_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    retry_number = Column(Integer, nullable=False)
    error_type = Column(String(100), nullable=False)
    error_message = Column(Text, nullable=False)
    fix_applied = Column(Text, nullable=False)
    was_successful = Column(Boolean, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    session = relationship("Session", back_populates="reflexion_logs")
