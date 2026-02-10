"""
Transaction management utilities for atomic database operations.
Ensures data consistency for multi-step operations.
"""

import logging
from typing import TypeVar, Callable, Any, Optional
from functools import wraps
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)

T = TypeVar('T')


class TransactionError(Exception):
    """Custom exception for transaction failures."""
    
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        self.message = message
        self.original_error = original_error
        super().__init__(self.message)


@asynccontextmanager
async def atomic_transaction(db: AsyncSession):
    """
    Context manager for atomic database transactions.
    
    Ensures all operations within the context are committed together
    or rolled back if any operation fails.
    
    Usage:
        async with atomic_transaction(db):
            db.add(user)
            db.add(assessment)
            # Both are committed together or rolled back
    
    Args:
        db: AsyncSession database session
        
    Yields:
        The database session
        
    Raises:
        TransactionError: If transaction fails
    """
    try:
        yield db
        await db.commit()
        logger.debug("Transaction committed successfully")
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Transaction rolled back due to database error: {e}", exc_info=True)
        raise TransactionError(f"Database transaction failed: {str(e)}", original_error=e)
    except Exception as e:
        await db.rollback()
        logger.error(f"Transaction rolled back due to error: {e}", exc_info=True)
        raise TransactionError(f"Transaction failed: {str(e)}", original_error=e)


@asynccontextmanager
async def nested_transaction(db: AsyncSession):
    """
    Context manager for nested transactions using savepoints.
    
    Allows partial rollback within a larger transaction.
    
    Usage:
        async with atomic_transaction(db):
            db.add(user)
            
            async with nested_transaction(db):
                db.add(assessment)
                # If this fails, only assessment is rolled back
                # user is still pending
    
    Args:
        db: AsyncSession database session
        
    Yields:
        The database session
    """
    try:
        # Create a savepoint
        async with db.begin_nested():
            yield db
        logger.debug("Nested transaction committed")
    except SQLAlchemyError as e:
        logger.warning(f"Nested transaction rolled back: {e}")
        raise TransactionError(f"Nested transaction failed: {str(e)}", original_error=e)


def transactional(func: Callable[..., T]) -> Callable[..., T]:
    """
    Decorator to wrap a function in a transaction.
    
    The decorated function must have a 'db' parameter that is an AsyncSession.
    
    Usage:
        @transactional
        async def create_user_with_assessment(db: AsyncSession, user_data: dict):
            user = User(**user_data)
            db.add(user)
            assessment = Assessment(user_id=user.id)
            db.add(assessment)
            return user, assessment
    
    Args:
        func: Async function to wrap
        
    Returns:
        Wrapped function with transaction management
    """
    @wraps(func)
    async def wrapper(*args, **kwargs) -> T:
        # Find the db session in arguments
        db = kwargs.get('db')
        if db is None:
            # Check positional arguments
            for arg in args:
                if isinstance(arg, AsyncSession):
                    db = arg
                    break
        
        if db is None:
            raise ValueError("No database session found in function arguments")
        
        try:
            result = await func(*args, **kwargs)
            await db.commit()
            logger.debug(f"Transaction committed for {func.__name__}")
            return result
        except SQLAlchemyError as e:
            await db.rollback()
            logger.error(f"Transaction rolled back for {func.__name__}: {e}", exc_info=True)
            raise TransactionError(f"Transaction failed in {func.__name__}: {str(e)}", original_error=e)
        except Exception as e:
            await db.rollback()
            logger.error(f"Transaction rolled back for {func.__name__}: {e}", exc_info=True)
            raise
    
    return wrapper


class TransactionManager:
    """
    Transaction manager for complex multi-step operations.
    
    Provides methods for managing transactions with retry logic
    and compensation actions.
    """
    
    def __init__(self, db: AsyncSession, max_retries: int = 3):
        """
        Initialize transaction manager.
        
        Args:
            db: AsyncSession database session
            max_retries: Maximum retry attempts for transient failures
        """
        self.db = db
        self.max_retries = max_retries
        self._compensation_actions: list[Callable] = []
    
    def add_compensation(self, action: Callable):
        """
        Add a compensation action to be executed on rollback.
        
        Compensation actions are executed in reverse order.
        
        Args:
            action: Async callable to execute on rollback
        """
        self._compensation_actions.append(action)
    
    async def _execute_compensations(self):
        """Execute all compensation actions in reverse order."""
        for action in reversed(self._compensation_actions):
            try:
                if callable(action):
                    result = action()
                    if hasattr(result, '__await__'):
                        await result
            except Exception as e:
                logger.error(f"Compensation action failed: {e}", exc_info=True)
    
    async def execute(
        self,
        operation: Callable[..., T],
        *args,
        **kwargs
    ) -> T:
        """
        Execute an operation with transaction management and retry logic.
        
        Args:
            operation: Async callable to execute
            *args: Positional arguments for operation
            **kwargs: Keyword arguments for operation
            
        Returns:
            Result of the operation
            
        Raises:
            TransactionError: If operation fails after all retries
        """
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                result = await operation(*args, **kwargs)
                await self.db.commit()
                logger.debug(f"Operation succeeded on attempt {attempt + 1}")
                return result
            except SQLAlchemyError as e:
                last_error = e
                await self.db.rollback()
                
                # Check if error is transient (can be retried)
                if self._is_transient_error(e) and attempt < self.max_retries - 1:
                    logger.warning(f"Transient error on attempt {attempt + 1}, retrying: {e}")
                    continue
                else:
                    logger.error(f"Non-transient error or max retries reached: {e}")
                    break
            except Exception as e:
                last_error = e
                await self.db.rollback()
                logger.error(f"Operation failed: {e}", exc_info=True)
                break
        
        # Execute compensations on failure
        await self._execute_compensations()
        
        raise TransactionError(
            f"Operation failed after {self.max_retries} attempts",
            original_error=last_error
        )
    
    def _is_transient_error(self, error: SQLAlchemyError) -> bool:
        """
        Check if an error is transient and can be retried.
        
        Args:
            error: SQLAlchemy error
            
        Returns:
            True if error is transient
        """
        # Common transient error indicators
        transient_indicators = [
            "deadlock",
            "lock wait timeout",
            "connection",
            "timeout",
            "temporarily unavailable",
        ]
        
        error_str = str(error).lower()
        return any(indicator in error_str for indicator in transient_indicators)


# =============================================================================
# Specific Transaction Patterns
# =============================================================================

async def create_user_and_assessment(
    db: AsyncSession,
    user_data: dict,
    division: Any,
    invitation: Optional[Any] = None
) -> tuple[Any, Any]:
    """
    Atomically create a user and their assessment.
    
    This is a common pattern that needs transaction protection.
    
    Args:
        db: Database session
        user_data: User creation data
        division: Division type for assessment
        invitation: Optional invitation code object
        
    Returns:
        Tuple of (user, assessment)
        
    Raises:
        TransactionError: If creation fails
    """
    from models.assessment import User, Assessment, AssessmentStatus
    from core.assessment_engine import AssessmentEngine
    from datetime import datetime
    
    async with atomic_transaction(db):
        # Create user
        user = User(**user_data)
        db.add(user)
        await db.flush()  # Get user ID
        
        # Mark invitation as used if provided
        if invitation:
            invitation.is_used = True
            invitation.used_at = datetime.now()
            invitation.used_by_user_id = user.id
        
        # Create assessment
        engine = AssessmentEngine(db)
        assessment = await engine.create_assessment(
            user_id=user.id,
            division=division
        )
        
        logger.info(f"Created user {user.id} and assessment {assessment.id} atomically")
        
        return user, assessment


async def complete_assessment_atomically(
    db: AsyncSession,
    assessment_id: int,
    scores: dict
) -> Any:
    """
    Atomically complete an assessment with final scores.
    
    Args:
        db: Database session
        assessment_id: Assessment ID
        scores: Dictionary of module scores
        
    Returns:
        Updated assessment
        
    Raises:
        TransactionError: If completion fails
    """
    from models.assessment import Assessment, AssessmentStatus
    from sqlalchemy import select
    from datetime import datetime
    from core.config import settings
    
    async with atomic_transaction(db):
        # Fetch assessment
        result = await db.execute(
            select(Assessment).where(Assessment.id == assessment_id)
        )
        assessment = result.scalar_one_or_none()
        
        if not assessment:
            raise TransactionError(f"Assessment {assessment_id} not found")
        
        # Update all scores atomically
        assessment.status = AssessmentStatus.COMPLETED
        assessment.completed_at = datetime.now()
        assessment.listening_score = scores.get("listening", 0)
        assessment.time_numbers_score = scores.get("time_numbers", 0)
        assessment.grammar_score = scores.get("grammar", 0)
        assessment.vocabulary_score = scores.get("vocabulary", 0)
        assessment.reading_score = scores.get("reading", 0)
        assessment.speaking_score = scores.get("speaking", 0)
        
        # Calculate total
        assessment.total_score = sum([
            assessment.listening_score or 0,
            assessment.time_numbers_score or 0,
            assessment.grammar_score or 0,
            assessment.vocabulary_score or 0,
            assessment.reading_score or 0,
            assessment.speaking_score or 0,
        ])
        
        # Determine pass/fail
        assessment.passed = assessment.total_score >= settings.PASS_THRESHOLD_TOTAL
        
        logger.info(f"Assessment {assessment_id} completed atomically with score {assessment.total_score}")
        
        return assessment


async def update_invitation_status(
    db: AsyncSession,
    invitation_code: str,
    user_id: int,
    assessment_completed: bool = False
) -> Any:
    """
    Atomically update invitation code status.
    
    Args:
        db: Database session
        invitation_code: Invitation code string
        user_id: User ID who used the invitation
        assessment_completed: Whether assessment is completed
        
    Returns:
        Updated invitation
        
    Raises:
        TransactionError: If update fails
    """
    from models.assessment import InvitationCode
    from sqlalchemy import select
    from datetime import datetime
    
    async with atomic_transaction(db):
        result = await db.execute(
            select(InvitationCode).where(InvitationCode.code == invitation_code)
        )
        invitation = result.scalar_one_or_none()
        
        if not invitation:
            raise TransactionError(f"Invitation code {invitation_code} not found")
        
        invitation.is_used = True
        invitation.used_at = datetime.now()
        invitation.used_by_user_id = user_id
        invitation.assessment_completed = assessment_completed
        
        logger.info(f"Invitation {invitation_code} status updated atomically")
        
        return invitation
