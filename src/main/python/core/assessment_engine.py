"""
Core Assessment Engine
Handles assessment flow, scoring, and validation
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
import random
import json

from models.assessment import (
    Assessment, AssessmentResponse, Question, User,
    AssessmentStatus, ModuleType, DivisionType, QuestionType
)
from core.config import settings
from services.ai_service import AIService
from utils.scoring import ScoringEngine


class AssessmentEngine:
    """Core assessment engine managing test flow and scoring"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.ai_service = AIService()
        self.scoring_engine = ScoringEngine(self.db)

    async def create_assessment(self, user_id: int, division: DivisionType) -> Assessment:
        """Create new assessment session"""

        # Generate unique session ID
        session_id = f"assess_{user_id}_{int(datetime.now().timestamp())}"

        # Create assessment record
        assessment = Assessment(
            user_id=user_id,
            session_id=session_id,
            division=division,
            status=AssessmentStatus.NOT_STARTED,
            expires_at=datetime.now() + timedelta(hours=2),  # 2-hour time limit
            max_possible_score=100.0
        )

        self.db.add(assessment)
        await self.db.commit()
        await self.db.refresh(assessment)

        return assessment

    async def start_assessment(self, assessment_id: int) -> Dict[str, Any]:
        """Start an assessment and generate questions"""

        # Get assessment
        result = await self.db.execute(select(Assessment).where(Assessment.id == assessment_id))
        assessment = result.scalar_one_or_none()

        if not assessment:
            raise ValueError("Assessment not found")

        if assessment.status != AssessmentStatus.NOT_STARTED:
            raise ValueError("Assessment already started or completed")

        # Update status
        assessment.status = AssessmentStatus.IN_PROGRESS
        assessment.started_at = datetime.now()

        # Generate question set
        questions = await self._generate_question_set(assessment.division)

        await self.db.commit()

        return {
            "assessment_id": assessment.id,
            "session_id": assessment.session_id,
            "status": assessment.status,
            "questions": questions,
            "expires_at": assessment.expires_at,
            "total_questions": len(questions)
        }

    async def _generate_question_set(self, division: DivisionType) -> Dict[str, List[Dict]]:
        """Generate randomized question set for assessment"""

        questions = {
            "listening": [],
            "time_numbers": [],
            "grammar": [],
            "vocabulary": [],
            "reading": [],
            "speaking": []
        }

        # Questions per module (total 84 points + 20 speaking = 104 points, but max 100)
        questions_per_module = {
            ModuleType.LISTENING: 4,      # 4 questions × 4 points = 16 points
            ModuleType.TIME_NUMBERS: 4,   # 4 questions × 4 points = 16 points
            ModuleType.GRAMMAR: 4,        # 4 questions × 4 points = 16 points
            ModuleType.VOCABULARY: 4,     # 4 questions × 4 points = 16 points
            ModuleType.READING: 4,        # 4 questions × 4 points = 16 points
            ModuleType.SPEAKING: 1        # 1 scenario × 20 points = 20 points
        }

        for module_type, count in questions_per_module.items():
            # Get questions for this module and division
            result = await self.db.execute(
                select(Question).where(
                    and_(
                        Question.module_type == module_type,
                        Question.division == division
                    )
                )
            )

            available_questions = result.scalars().all()

            if len(available_questions) < count:
                # If not enough questions, create sample questions
                await self._create_sample_questions(module_type, division)

                # Re-fetch questions
                result = await self.db.execute(
                    select(Question).where(
                        and_(
                            Question.module_type == module_type,
                            Question.division == division
                        )
                    )
                )
                available_questions = result.scalars().all()

            # Randomly select questions
            selected_questions = random.sample(available_questions, min(count, len(available_questions)))

            # Format questions for frontend
            module_key = module_type.value
            questions[module_key] = [
                {
                    "id": q.id,
                    "question_text": q.question_text,
                    "options": q.options,
                    "question_type": q.question_type.value,
                    "points": q.points,
                    "audio_file": q.audio_file_path,
                    "is_safety_related": q.is_safety_related,
                    "metadata": q.metadata
                }
                for q in selected_questions
            ]

        return questions

    async def submit_response(self, assessment_id: int, question_id: int,
                            user_answer: str, time_spent: int = None) -> Dict[str, Any]:
        """Submit answer for a question"""

        # Get assessment and question
        assessment_result = await self.db.execute(select(Assessment).where(Assessment.id == assessment_id))
        assessment = assessment_result.scalar_one_or_none()

        question_result = await self.db.execute(select(Question).where(Question.id == question_id))
        question = question_result.scalar_one_or_none()

        if not assessment or not question:
            raise ValueError("Assessment or question not found")

        if assessment.status != AssessmentStatus.IN_PROGRESS:
            raise ValueError("Assessment is not in progress")

        # Check if already answered
        existing_result = await self.db.execute(
            select(AssessmentResponse).where(
                and_(
                    AssessmentResponse.assessment_id == assessment_id,
                    AssessmentResponse.question_id == question_id
                )
            )
        )

        if existing_result.scalar_one_or_none():
            raise ValueError("Question already answered")

        # Score the response
        is_correct, points_earned = await self._score_response(question, user_answer)

        # Create response record
        response = AssessmentResponse(
            assessment_id=assessment_id,
            question_id=question_id,
            user_answer=user_answer,
            is_correct=is_correct,
            points_earned=points_earned,
            points_possible=question.points,
            time_spent_seconds=time_spent
        )

        self.db.add(response)
        await self.db.commit()

        return {
            "is_correct": is_correct,
            "points_earned": points_earned,
            "points_possible": question.points,
            "feedback": await self._generate_feedback(question, user_answer, is_correct)
        }

    async def _score_response(self, question: Question, user_answer: str) -> Tuple[bool, float]:
        """
        Score a user's response to a question

        Now handles all question types properly including:
        - CATEGORY_MATCH (vocabulary module)
        - TITLE_SELECTION (reading module)
        """

        if question.question_type == QuestionType.MULTIPLE_CHOICE:
            is_correct = user_answer.strip().lower() == question.correct_answer.strip().lower()
            points = question.points if is_correct else 0

        elif question.question_type == QuestionType.FILL_BLANK:
            # More flexible matching for fill-in-the-blank (time & numbers)
            is_correct = self._flexible_text_match(user_answer, question.correct_answer)
            points = question.points if is_correct else 0

        elif question.question_type == QuestionType.CATEGORY_MATCH:
            # Vocabulary module - match category terms
            is_correct = self._score_category_match(user_answer, question.correct_answer)
            points = question.points if is_correct else 0

        elif question.question_type == QuestionType.TITLE_SELECTION:
            # Reading module - select best title
            is_correct = user_answer.strip().lower() == question.correct_answer.strip().lower()
            points = question.points if is_correct else 0

        elif question.question_type == QuestionType.SPEAKING_RESPONSE:
            # AI-powered scoring for speaking
            analysis = await self.ai_service.analyze_speech_response(
                user_answer, question.correct_answer, question.question_text
            )
            is_correct = analysis["overall_score"] >= 0.6  # 60% threshold
            points = analysis["total_points"]

        else:
            # Default exact match for any other type
            is_correct = user_answer.strip().lower() == question.correct_answer.strip().lower()
            points = question.points if is_correct else 0

        return is_correct, points

    def _score_category_match(self, user_answer: str, correct_answer: str) -> bool:
        """
        Score category matching questions (vocabulary module)

        Format expected:
        - user_answer: "A,B,C" or "category1:term1,term2"
        - correct_answer: "A,B,C" or "category1:term1,term2"
        """
        import json

        # Try JSON format first (more structured)
        try:
            user_data = json.loads(user_answer)
            correct_data = json.loads(correct_answer)

            if isinstance(user_data, dict) and isinstance(correct_data, dict):
                # Compare category assignments
                return user_data == correct_data
        except (json.JSONDecodeError, TypeError):
            pass

        # Fall back to comma-separated list
        user_items = {item.strip().lower() for item in user_answer.split(",")}
        correct_items = {item.strip().lower() for item in correct_answer.split(",")}

        # Allow partial credit: at least 75% correct
        if len(correct_items) == 0:
            return False

        matches = len(user_items & correct_items)
        accuracy = matches / len(correct_items)

        return accuracy >= 0.75  # 75% threshold for partial credit

    def _flexible_text_match(self, user_answer: str, correct_answer: str) -> bool:
        """
        Flexible text matching for fill-in-the-blank questions

        FIXED: Previous implementation was too lenient:
        - "7" matched "7:00" and "270"
        - "nine" matched "nine hundred"

        Now uses strict matching with allowed variations for common formats
        """
        user_clean = user_answer.strip().lower().replace(".", "").replace(",", "")
        correct_clean = correct_answer.strip().lower().replace(".", "").replace(",", "")

        # Exact match (most common case)
        if user_clean == correct_clean:
            return True

        # Handle time formats: 7:00, 7am, 0700, seven o'clock
        if self._is_time_match(user_clean, correct_clean):
            return True

        # Handle number formats: 100, one hundred, a hundred
        if self._is_number_match(user_clean, correct_clean):
            return True

        # No substring matching - must be exact or recognized variation
        return False

    def _is_time_match(self, user: str, correct: str) -> bool:
        """Check if user answer matches time in different formats"""
        import re

        # Extract hours and minutes from various time formats
        def parse_time(text: str) -> tuple:
            """Extract (hour, minute, am/pm) from text"""
            # 7:00, 07:00
            m = re.match(r'(\d{1,2}):(\d{2})\s*(am|pm)?', text)
            if m:
                return (int(m.group(1)), int(m.group(2)), m.group(3))

            # 7am, 7 am
            m = re.match(r'(\d{1,2})\s*(am|pm)', text)
            if m:
                return (int(m.group(1)), 0, m.group(2))

            # 0700 (military time)
            m = re.match(r'(\d{2})(\d{2})$', text)
            if m and len(text) == 4:
                return (int(m.group(1)), int(m.group(2)), None)

            return None

        user_time = parse_time(user)
        correct_time = parse_time(correct)

        if user_time and correct_time:
            # Compare normalized times
            u_hour, u_min, u_meridiem = user_time
            c_hour, c_min, c_meridiem = correct_time

            # Normalize hours to 24-hour format
            if u_meridiem == 'pm' and u_hour != 12:
                u_hour += 12
            elif u_meridiem == 'am' and u_hour == 12:
                u_hour = 0

            if c_meridiem == 'pm' and c_hour != 12:
                c_hour += 12
            elif c_meridiem == 'am' and c_hour == 12:
                c_hour = 0

            return u_hour == c_hour and u_min == c_min

        return False

    def _is_number_match(self, user: str, correct: str) -> bool:
        """Check if user answer matches number in different formats"""
        # Word to number mappings
        word_to_num = {
            'zero': 0, 'one': 1, 'two': 2, 'three': 3, 'four': 4,
            'five': 5, 'six': 6, 'seven': 7, 'eight': 8, 'nine': 9,
            'ten': 10, 'eleven': 11, 'twelve': 12, 'thirteen': 13,
            'fourteen': 14, 'fifteen': 15, 'sixteen': 16, 'seventeen': 17,
            'eighteen': 18, 'nineteen': 19, 'twenty': 20, 'thirty': 30,
            'forty': 40, 'fifty': 50, 'sixty': 60, 'seventy': 70,
            'eighty': 80, 'ninety': 90, 'hundred': 100, 'thousand': 1000
        }

        def text_to_number(text: str) -> int:
            """Convert text to number if possible"""
            # Remove common prefixes
            text = text.replace('a ', '1 ').replace('an ', '1 ')

            # Try direct digit parsing
            try:
                return int(text.replace(' ', ''))
            except ValueError:
                pass

            # Try word mapping
            if text in word_to_num:
                return word_to_num[text]

            # Handle compound numbers: "one hundred fifty"
            words = text.split()
            if len(words) > 1:
                try:
                    total = 0
                    current = 0
                    for word in words:
                        if word in word_to_num:
                            val = word_to_num[word]
                            if val >= 100:
                                current = (current or 1) * val
                                total += current
                                current = 0
                            else:
                                current += val
                    return total + current
                except:
                    pass

            return None

        user_num = text_to_number(user)
        correct_num = text_to_number(correct)

        if user_num is not None and correct_num is not None:
            return user_num == correct_num

        return False

    async def complete_assessment(self, assessment_id: int) -> Dict[str, Any]:
        """Complete assessment and calculate final scores"""

        # Get assessment with responses
        assessment_result = await self.db.execute(
            select(Assessment).where(Assessment.id == assessment_id)
        )
        assessment = assessment_result.scalar_one_or_none()

        if not assessment:
            raise ValueError("Assessment not found")

        # Get all responses
        responses_result = await self.db.execute(
            select(AssessmentResponse).where(AssessmentResponse.assessment_id == assessment_id)
        )
        responses = responses_result.scalars().all()

        # Calculate scores using scoring engine
        scores = await self.scoring_engine.calculate_final_scores(responses)

        # Update assessment
        assessment.status = AssessmentStatus.COMPLETED
        assessment.completed_at = datetime.now()
        assessment.total_score = scores["total_score"]

        # Module scores
        assessment.listening_score = scores.get("listening", 0)
        assessment.time_numbers_score = scores.get("time_numbers", 0)
        assessment.grammar_score = scores.get("grammar", 0)
        assessment.vocabulary_score = scores.get("vocabulary", 0)
        assessment.reading_score = scores.get("reading", 0)
        assessment.speaking_score = scores.get("speaking", 0)

        # Pass/fail determination
        assessment.passed = scores["total_score"] >= settings.PASS_THRESHOLD_TOTAL
        assessment.safety_questions_passed = scores["safety_pass_rate"] >= settings.PASS_THRESHOLD_SAFETY
        assessment.speaking_threshold_passed = scores.get("speaking", 0) >= settings.PASS_THRESHOLD_SPEAKING

        # Final pass requires all conditions
        final_pass = (
            assessment.passed and
            assessment.safety_questions_passed and
            assessment.speaking_threshold_passed
        )

        # Generate feedback
        feedback = await self._generate_assessment_feedback(scores, final_pass)
        assessment.feedback = feedback

        await self.db.commit()

        return {
            "assessment_id": assessment.id,
            "total_score": assessment.total_score,
            "passed": final_pass,
            "scores": scores,
            "feedback": feedback,
            "completed_at": assessment.completed_at
        }

    async def _generate_feedback(self, question: Question, user_answer: str, is_correct: bool) -> str:
        """Generate feedback for individual question"""
        if is_correct:
            return "Correct! Well done."
        else:
            return f"Incorrect. The correct answer is: {question.correct_answer}"

    async def _generate_assessment_feedback(self, scores: Dict[str, Any], passed: bool) -> Dict[str, Any]:
        """Generate comprehensive assessment feedback"""

        feedback = {
            "overall_result": "PASS" if passed else "FAIL",
            "total_score": scores["total_score"],
            "breakdown": scores,
            "recommendations": []
        }

        # Add specific recommendations based on performance
        if scores.get("listening", 0) < 12:
            feedback["recommendations"].append(
                "Focus on improving listening skills with maritime/hospitality audio materials"
            )

        if scores.get("speaking", 0) < 12:
            feedback["recommendations"].append(
                "Practice speaking in work-related scenarios with clear pronunciation"
            )

        if scores.get("grammar", 0) < 12:
            feedback["recommendations"].append(
                "Review service industry grammar patterns and polite expressions"
            )

        return feedback

    async def _create_sample_questions(self, module_type: ModuleType, division: DivisionType):
        """Create sample questions when question bank is empty"""

        # This would typically be populated from a comprehensive question bank
        # For now, create a few sample questions

        sample_questions = []

        if module_type == ModuleType.LISTENING and division == DivisionType.HOTEL:
            sample_questions = [
                {
                    "question_text": "Listen to the guest request and choose the best response.",
                    "options": ["Certainly, sir", "Maybe later", "I don't know", "Ask someone else"],
                    "correct_answer": "Certainly, sir",
                    "points": 4
                }
            ]

        # Add more sample questions as needed...

        for q_data in sample_questions:
            question = Question(
                module_type=module_type,
                division=division,
                question_type=QuestionType.MULTIPLE_CHOICE,
                question_text=q_data["question_text"],
                options=q_data["options"],
                correct_answer=q_data["correct_answer"],
                points=q_data["points"]
            )
            self.db.add(question)

        await self.db.commit()