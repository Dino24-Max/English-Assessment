"""
Assessment-related database models
"""

from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey, JSON, Enum, Index, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from models.base import BaseModel
from enum import Enum as PyEnum
from typing import Dict, Any, Optional
from datetime import datetime


class DivisionType(str, PyEnum):
    """Division types for cruise operations"""
    HOTEL = "hotel"
    MARINE = "marine"
    CASINO = "casino"


class ModuleType(str, PyEnum):
    """Assessment module types"""
    LISTENING = "listening"
    TIME_NUMBERS = "time_numbers"
    GRAMMAR = "grammar"
    VOCABULARY = "vocabulary"
    READING = "reading"
    SPEAKING = "speaking"


class QuestionType(str, PyEnum):
    """Question types"""
    MULTIPLE_CHOICE = "multiple_choice"
    FILL_BLANK = "fill_blank"
    CATEGORY_MATCH = "category_match"
    TITLE_SELECTION = "title_selection"
    SPEAKING_RESPONSE = "speaking_response"


class AssessmentStatus(str, PyEnum):
    """Assessment status types"""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    EXPIRED = "expired"


class User(BaseModel):
    """User/Candidate model"""
    __tablename__ = "users"

    # Personal Information
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)  # Bcrypt hashed password
    nationality = Column(String(100), nullable=False)

    # Assessment Information
    division = Column(Enum(DivisionType), nullable=True, index=True)  # Will be set during operation selection
    department = Column(String(100), nullable=True)  # Will be set during operation selection

    # Status
    is_active = Column(Boolean, default=True, index=True)

    # Relationships
    assessments = relationship("Assessment", back_populates="user")

    # Composite indexes for common query patterns
    __table_args__ = (
        Index('ix_users_active_division', 'is_active', 'division'),
    )


class Question(BaseModel):
    """Question bank model"""
    __tablename__ = "questions"

    # Question Details
    module_type = Column(Enum(ModuleType), nullable=False, index=True)
    division = Column(Enum(DivisionType), nullable=False, index=True)
    question_type = Column(Enum(QuestionType), nullable=False)

    # Content
    question_text = Column(Text, nullable=False)
    options = Column(JSON, nullable=True)  # For multiple choice questions
    correct_answer = Column(Text, nullable=False)
    audio_file_path = Column(String(500), nullable=True)  # For listening questions

    # Metadata
    difficulty_level = Column(Integer, default=1)  # 1-5 scale
    is_safety_related = Column(Boolean, default=False, index=True)
    points = Column(Integer, nullable=False)

    # Question specific data
    question_metadata = Column(JSON, nullable=True)  # Additional question-specific data (renamed from 'metadata' to avoid SQLAlchemy reserved word)

    # Composite indexes for question selection queries
    __table_args__ = (
        Index('ix_questions_module_division', 'module_type', 'division'),
        Index('ix_questions_division_difficulty', 'division', 'difficulty_level'),
        Index('ix_questions_safety', 'is_safety_related'),
    )


class Assessment(BaseModel):
    """Assessment session model"""
    __tablename__ = "assessments"

    # User and Session Info
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id = Column(String(100), unique=True, nullable=False, index=True)

    # Assessment Details
    division = Column(Enum(DivisionType), nullable=False, index=True)
    status = Column(Enum(AssessmentStatus), default=AssessmentStatus.NOT_STARTED, index=True)

    # Timing
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    # Scoring
    total_score = Column(Float, default=0.0)
    max_possible_score = Column(Float, default=100.0)

    # Module Scores
    listening_score = Column(Float, default=0.0)
    time_numbers_score = Column(Float, default=0.0)
    grammar_score = Column(Float, default=0.0)
    vocabulary_score = Column(Float, default=0.0)
    reading_score = Column(Float, default=0.0)
    speaking_score = Column(Float, default=0.0)

    # Pass/Fail Status
    passed = Column(Boolean, default=False)
    safety_questions_passed = Column(Boolean, default=False)
    speaking_threshold_passed = Column(Boolean, default=False)

    # Anti-cheating
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)

    # Additional Data
    feedback = Column(JSON, nullable=True)
    analytics_data = Column(JSON, nullable=True)

    # Relationships
    user = relationship("User", back_populates="assessments")
    responses = relationship("AssessmentResponse", back_populates="assessment", cascade="all, delete-orphan")

    # Composite indexes and constraints
    __table_args__ = (
        Index('ix_assessments_user_status', 'user_id', 'status'),
        Index('ix_assessments_division_status', 'division', 'status'),
        Index('ix_assessments_completed', 'completed_at', 'passed'),
        CheckConstraint('total_score >= 0', name='check_total_score_positive'),
        CheckConstraint('total_score <= max_possible_score', name='check_score_range'),
        CheckConstraint('max_possible_score > 0', name='check_max_score_positive'),
    )


class AssessmentResponse(BaseModel):
    """Individual question responses"""
    __tablename__ = "assessment_responses"

    # References
    assessment_id = Column(Integer, ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False, index=True)

    # Response Data
    user_answer = Column(Text, nullable=True)
    is_correct = Column(Boolean, nullable=False)
    points_earned = Column(Float, nullable=False)
    points_possible = Column(Float, nullable=False)

    # Timing
    time_spent_seconds = Column(Integer, nullable=True)
    answered_at = Column(DateTime(timezone=True), server_default=func.now())

    # Speaking Module Specific
    audio_file_path = Column(String(500), nullable=True)
    speech_analysis = Column(JSON, nullable=True)  # AI analysis results

    # Relationships
    assessment = relationship("Assessment", back_populates="responses")
    question = relationship("Question")

    # Composite indexes for common queries
    __table_args__ = (
        Index('ix_response_assessment_question', 'assessment_id', 'question_id'),
        Index('ix_response_answered_at', 'answered_at'),
        CheckConstraint('points_earned >= 0', name='check_points_earned_positive'),
        CheckConstraint('points_earned <= points_possible', name='check_points_earned_range'),
        CheckConstraint('points_possible > 0', name='check_points_possible_positive'),
    )


class DivisionDepartment(BaseModel):
    """Division and department mapping"""
    __tablename__ = "division_departments"

    division = Column(Enum(DivisionType), nullable=False, index=True)
    department_name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)


class AssessmentConfig(BaseModel):
    """Assessment configuration settings"""
    __tablename__ = "assessment_config"

    config_key = Column(String(100), unique=True, nullable=False)
    config_value = Column(JSON, nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)