"""
Assessment-related database models
"""

from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey, JSON, Enum, Index, CheckConstraint, UniqueConstraint

# DivisionType: Use DivisionTypeEnumType for all columns - DB stores lowercase values (hotel/marine/casino)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.types import TypeDecorator
from models.base import BaseModel
from enum import Enum as PyEnum
from typing import Dict, Any, Optional
from datetime import datetime


class DivisionType(str, PyEnum):
    """Division types for cruise operations"""
    HOTEL = "hotel"
    MARINE = "marine"
    CASINO = "casino"


class DivisionTypeEnumType(TypeDecorator):
    """Stores DivisionType as lowercase value string. Bypasses SQLAlchemy Enum validation."""

    impl = String(20)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, DivisionType):
            return value.value
        return str(value).lower() if value else None

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        try:
            return DivisionType(value.lower())
        except (ValueError, TypeError):
            return None


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


class AssessmentStatusEnumType(TypeDecorator):
    """Stores AssessmentStatus as lowercase value string. Tolerates legacy uppercase DB values on load."""

    impl = String(20)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, AssessmentStatus):
            return value.value
        return str(value).lower() if value else None

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        try:
            return AssessmentStatus(str(value).lower())
        except (ValueError, TypeError):
            return None


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
    division = Column(DivisionTypeEnumType, nullable=True, index=True)
    department = Column(String(100), nullable=True)  # Will be set during operation selection

    # Status
    is_active = Column(Boolean, default=True, index=True)
    is_admin = Column(Boolean, default=False, index=True)  # Admin role flag

    # Relationships
    assessments = relationship("Assessment", back_populates="user")

    # Composite indexes for common query patterns
    __table_args__ = (
        Index('ix_users_active_division', 'is_active', 'division'),
        Index('ix_users_admin', 'is_admin', 'is_active'),
    )


class Question(BaseModel):
    """Question bank model"""
    __tablename__ = "questions"

    # Question Details
    module_type = Column(Enum(ModuleType, values_callable=lambda x: [e.value for e in x], native_enum=False), nullable=False, index=True)
    division = Column(DivisionTypeEnumType, nullable=False, index=True)
    question_type = Column(Enum(QuestionType, values_callable=lambda x: [e.value for e in x], native_enum=False), nullable=False)

    # Content
    question_text = Column(Text, nullable=False)
    options = Column(JSON, nullable=True)  # For multiple choice questions
    correct_answer = Column(Text, nullable=False)
    audio_file_path = Column(String(500), nullable=True)  # For listening questions

    # Metadata
    difficulty_level = Column(Integer, default=1)  # 1-5 scale
    is_safety_related = Column(Boolean, default=False, index=True)
    points = Column(Integer, nullable=False)
    
    # Department & Scenario Info (for 1600-question bank)
    department = Column(String(100), nullable=True)  # e.g., "HOUSEKEEPING", "Deck", "Table Games" (indexed via composite indexes)
    scenario_id = Column(Integer, nullable=True)  # 1-10 for each department (indexed via composite indexes)
    scenario_description = Column(Text, nullable=True)  # Description of the scenario
    cefr_level = Column(String(2), nullable=True)  # A1, A2, B1, B2, C1, C2 per Council of Europe

    # Question specific data
    question_metadata = Column(JSON, nullable=True)  # Additional question-specific data (renamed from 'metadata' to avoid SQLAlchemy reserved word)

    # Semantic deduplication (nullable until backfilled on legacy DBs; unique when set)
    semantic_hash = Column(String(64), nullable=True, index=True)
    # Grammar classification (Grammar module only)
    grammar_type = Column(String(50), nullable=True, index=True)  # "Core" or "RoleContext"
    grammar_topic = Column(String(100), nullable=True, index=True)

    # Composite indexes for question selection queries
    __table_args__ = (
        Index('ix_questions_module_division', 'module_type', 'division'),
        Index('ix_questions_division_difficulty', 'division', 'difficulty_level'),
        Index('ix_questions_safety', 'is_safety_related'),
        # New indexes for 1600-question bank
        Index('ix_questions_department', 'department', 'module_type'),
        Index('ix_questions_scenario', 'department', 'scenario_id'),
        Index('ix_questions_division_dept', 'division', 'department'),
        Index('ix_questions_dept_cefr', 'department', 'cefr_level'),
        Index('ix_questions_dept_module_cefr', 'department', 'module_type', 'cefr_level'),
        UniqueConstraint('semantic_hash', name='uq_questions_semantic_hash'),
        Index('ix_questions_grammar_classification', 'grammar_type', 'grammar_topic', 'cefr_level'),
    )


class Assessment(BaseModel):
    """Assessment session model"""
    __tablename__ = "assessments"

    # User and Session Info
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id = Column(String(100), unique=True, nullable=False, index=True)

    # Assessment Details
    division = Column(DivisionTypeEnumType, nullable=False, index=True)
    department = Column(String(100), nullable=True)  # Question pool used (from user/invitation)
    status = Column(AssessmentStatusEnumType, default=AssessmentStatus.NOT_STARTED, index=True)

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
    # Question order: list of 21 question IDs [id1, id2, ...] - persisted when assessment starts
    question_order = Column(JSON, nullable=True)

    # Relationships
    user = relationship("User", back_populates="assessments")
    responses = relationship("AssessmentResponse", back_populates="assessment", cascade="all, delete-orphan")

    # Composite indexes and constraints
    __table_args__ = (
        # Existing indexes
        Index('ix_assessments_user_status', 'user_id', 'status'),
        Index('ix_assessments_division_status', 'division', 'status'),
        Index('ix_assessments_completed', 'completed_at', 'passed'),
        # New performance indexes
        Index('ix_assessments_expires_at', 'expires_at'),  # For finding expired assessments
        Index('ix_assessments_status_created', 'status', 'created_at'),  # For sorting by status and time
        Index('ix_assessments_user_division', 'user_id', 'division'),  # For user division queries
        # Constraints
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
        # Existing indexes
        Index('ix_response_assessment_question', 'assessment_id', 'question_id'),
        Index('ix_response_answered_at', 'answered_at'),
        # New performance indexes
        Index('ix_response_assessment_correct', 'assessment_id', 'is_correct'),  # For accuracy statistics
        Index('ix_response_question_correct', 'question_id', 'is_correct'),  # For question difficulty analysis
        # Constraints
        CheckConstraint('points_earned >= 0', name='check_points_earned_positive'),
        CheckConstraint('points_earned <= points_possible', name='check_points_earned_range'),
        CheckConstraint('points_possible > 0', name='check_points_possible_positive'),
    )


class DivisionDepartment(BaseModel):
    """Division and department mapping"""
    __tablename__ = "division_departments"

    division = Column(DivisionTypeEnumType, nullable=False, index=True)
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


class PasswordResetToken(BaseModel):
    """Password reset token model"""
    __tablename__ = "password_reset_tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token = Column(String(64), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    used = Column(Boolean, default=False, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", backref="password_reset_tokens")
    
    __table_args__ = (
        Index('ix_reset_token_user_expires', 'user_id', 'expires_at'),
    )


class InvitationCode(BaseModel):
    """Invitation code for user registration"""
    __tablename__ = "invitation_codes"

    # Invitation Code
    code = Column(String(16), unique=True, nullable=False, index=True)
    
    # Target User
    email = Column(String(255), nullable=False, index=True)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    nationality = Column(String(100), nullable=True)
    
    # Assignment
    operation = Column(DivisionTypeEnumType, nullable=False, index=True)
    department = Column(String(100), nullable=True)  # Optional specific department
    
    # Creation Info
    created_by = Column(String(100), nullable=False)  # Admin identifier
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)  # Optional expiration
    
    # Usage Tracking
    is_used = Column(Boolean, default=False, nullable=False, index=True)
    used_at = Column(DateTime(timezone=True), nullable=True)
    used_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    assessment_completed = Column(Boolean, default=False, nullable=False, index=True)  # Track if assessment was fully completed
    
    # Relationships
    used_by_user = relationship("User", foreign_keys=[used_by_user_id])
    
    # Indexes for common queries
    __table_args__ = (
        Index('ix_invitation_code', 'code'),
        Index('ix_invitation_email', 'email'),
        Index('ix_invitation_used', 'is_used', 'created_at'),
        Index('ix_invitation_operation', 'operation', 'is_used'),
    )