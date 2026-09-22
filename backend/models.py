from __future__ import annotations

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, relationship
from flask_login import UserMixin

from .database import Base


class User(Base, UserMixin):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password = Column(String(255), nullable=False)
    created_at = Column(String(255), nullable=False)
    level = Column(String(50), default='A1')
    level_label = Column(String(50), default='Beginner')
    overall_score = Column(Integer, default=0)


class Conversation(Base):
    __tablename__ = 'conversations'

    id = Column(String(64), primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    title = Column(String(255), default='New Conversation')
    created_at = Column(String(255), nullable=False)
    updated_at = Column(String(255), nullable=False)
    deleted = Column(Boolean, default=False, nullable=False, index=True)
    turn_count = Column(Integer, default=0, nullable=False)


class Message(Base):
    __tablename__ = 'messages'

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(String(64), ForeignKey('conversations.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    timestamp = Column(String(255), nullable=False, index=True)


class LearningEvent(Base):
    __tablename__ = 'learning_events'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    conversation_id = Column(String(64), ForeignKey('conversations.id', ondelete='CASCADE'), nullable=False, index=True)
    message_id = Column(Integer, ForeignKey('messages.id', ondelete='CASCADE'), nullable=False, index=True)
    event_type = Column(String(50), nullable=False)
    category = Column(String(100), nullable=True)
    original = Column(Text, nullable=True)
    correction = Column(Text, nullable=True)
    explanation = Column(Text, nullable=True)
    severity = Column(String(50), nullable=True)
    confidence = Column(String(50), nullable=True)
    timestamp = Column(String(255), nullable=False, index=True)


class RecurringMistake(Base):
    __tablename__ = 'recurring_mistakes'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    category = Column(String(100), nullable=False)
    pattern = Column(String(255), nullable=True)
    pattern_key = Column(String(255), nullable=False, index=True)
    incorrect = Column(Text, nullable=False)
    correct = Column(Text, nullable=False)
    explanation = Column(Text, nullable=True)
    occurrence_count = Column(Integer, default=1, nullable=False)
    first_detected = Column(String(255), nullable=False)
    last_detected = Column(String(255), nullable=False)
    status = Column(String(50), default='new', nullable=False)
    example_sentences = Column(Text, nullable=True)
    learner_improved = Column(Boolean, default=False, nullable=False)
    needs_retesting = Column(Boolean, default=True, nullable=False)
    created_at = Column(String(255), nullable=False)
    updated_at = Column(String(255), nullable=False)


class LearningProfile(Base):
    __tablename__ = 'learning_profiles'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True, index=True)
    current_level = Column(String(50), default='Emerging', nullable=False)
    strengths = Column(Text, nullable=True)
    needs_practice = Column(Text, nullable=True)
    focus_areas = Column(Text, nullable=True)
    recurring_patterns = Column(Text, nullable=True)
    preferred_practice = Column(Text, nullable=True)
    profile_data = Column(Text, nullable=True)
    created_at = Column(String(255), nullable=False)
    updated_at = Column(String(255), nullable=False)


class DailyAnalysis(Base):
    __tablename__ = 'daily_analyses'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    analysis_date = Column(String(20), nullable=False)
    timezone = Column(String(100), nullable=False)
    conversation_ids = Column(Text, nullable=True)
    analysis_data = Column(Text, nullable=True)
    created_at = Column(String(255), nullable=False)

class UserProgress(Base):
    __tablename__ = 'user_progress'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True, index=True)
    turns = Column(Integer, default=0, nullable=False)
    updated_at = Column(String(255), nullable=False)


class PasswordResetToken(Base):
    __tablename__ = 'password_reset_tokens'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    token_hash = Column(String(64), unique=True, nullable=False, index=True)
    expires_at = Column(String(255), nullable=False, index=True)
    used_at = Column(String(255), nullable=True)
    created_at = Column(String(255), nullable=False)
