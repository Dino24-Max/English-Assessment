"""
Base models and common database functionality
"""

from sqlalchemy import Column, Integer, DateTime, String
from sqlalchemy.sql import func
from core.database import Base
from datetime import datetime
from typing import Optional
import uuid


class TimestampMixin:
    """Mixin for created_at and updated_at timestamps"""
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class BaseModel(Base, TimestampMixin):
    """Base model with common fields"""
    __abstract__ = True

    id = Column(Integer, primary_key=True, index=True)


def generate_uuid() -> str:
    """Generate UUID string"""
    return str(uuid.uuid4())