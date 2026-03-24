"""
Core Assessment Engine
Handles assessment flow, scoring, and validation
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
import random
import json
import uuid
import re

import models.assessment as _ma  # Use module ref to avoid UnboundLocalError
from config.departments import normalize_department
from core.config import settings
from services.ai_service import AIService
from services.speaking_scorer import score_speaking_response
from utils.scoring import ScoringEngine, compute_overall_pass
from utils.cache import cache_result, CacheKeys, CacheTTL

# Stopwords for deriving keywords from reference/audio text when expected_keywords is missing
_SPEAKING_STOPWORDS = frozenset(
    {
        "the", "and", "for", "are", "but", "not", "you", "all", "can", "her", "was", "one", "our",
        "out", "day", "get", "has", "him", "his", "how", "its", "let", "may", "new", "now", "old",
        "see", "two", "way", "who", "did", "she", "too", "use", "from", "that", "this", "with",
        "have", "will", "your", "been", "said", "each", "which", "their", "time", "would", "there",
        "could", "other", "about", "into", "more", "than", "then", "them", "these", "please", "remember",
        "bring", "during", "name", "good", "morning", "what", "when", "where", "very",
    }
)


class AssessmentEngine:
    """Core assessment engine managing test flow and scoring"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.ai_service = AIService()
        self.scoring_engine = ScoringEngine(self.db)

    @cache_result(ttl=CacheTTL.HOUR, key_prefix=CacheKeys.QUESTIONS_BY_DIVISION)
    async def _get_cached_questions_by_division(self, division: _ma.DivisionType) -> List[_ma.Question]:
        """
        Get all questions for a division with caching
        Cache for 1 hour since question bank rarely changes
        """
        result = await self.db.execute(
            select(_ma.Question).where(_ma.Question.division == division)
        )
        questions = result.scalars().all()
        
        # Convert to list of dicts for JSON serialization
        return [
            {
                "id": q.id,
                "module_type": q.module_type.value,
                "division": q.division.value,
                "question_type": q.question_type.value,
                "question_text": q.question_text,
                "options": q.options,
                "correct_answer": q.correct_answer,
                "audio_file_path": q.audio_file_path,
                "difficulty_level": q.difficulty_level,
                "is_safety_related": q.is_safety_related,
                "points": q.points,
                "question_metadata": q.question_metadata
            }
            for q in questions
        ]

    async def create_assessment(
        self,
        user_id: int,
        division: _ma.DivisionType,
        department: Optional[str] = None,
        *,
        auto_commit: bool = True,
    ) -> _ma.Assessment:
        """Create new assessment session. Stores department to record which question pool was used.
        When auto_commit=False, only flushes (caller must commit) - use for atomic create+start flows."""
        import logging
        # Normalize so filter matches DB (e.g. "Guest Services" -> "GUEST SERVICES")
        department = normalize_department(department) if department else None
        logging.getLogger(__name__).info(
            f"create_assessment: user_id={user_id}, division={division.value}, department={department!r}"
        )

        # Generate unique session ID (timestamp + short uuid to avoid UNIQUE collision when creating twice in same second)
        session_id = f"assess_{user_id}_{int(datetime.now().timestamp())}_{uuid.uuid4().hex[:8]}"

        # Create assessment record
        assessment = _ma.Assessment(
            user_id=user_id,
            session_id=session_id,
            division=division,
            department=department,
            status=_ma.AssessmentStatus.NOT_STARTED,
            expires_at=datetime.now() + timedelta(hours=2),  # 2-hour time limit
            max_possible_score=100.0
        )

        self.db.add(assessment)
        await self.db.flush()
        if auto_commit:
            await self.db.commit()
            await self.db.refresh(assessment)

        return assessment

    async def start_assessment(self, assessment_id: int) -> Dict[str, Any]:
        """Start an assessment and generate questions"""

        # Get assessment
        result = await self.db.execute(select(_ma.Assessment).where(_ma.Assessment.id == assessment_id))
        assessment = result.scalar_one_or_none()

        if not assessment:
            raise ValueError("Assessment not found")

        if assessment.status != _ma.AssessmentStatus.NOT_STARTED:
            raise ValueError("Assessment already started or completed")

        # Use assessment.department only (no backfill from user). When None, question selection is division-only.
        department = assessment.department
        department = normalize_department(department) if department else None

        # Update status
        assessment.status = _ma.AssessmentStatus.IN_PROGRESS
        assessment.started_at = datetime.now()

        # Generate question set (department-specific when department is set)
        questions = await self._generate_question_set(assessment.division, department=department)

        # Persist question order for UI: flatten to [q1_id, q2_id, ..., q21_id]
        module_order = [
            _ma.ModuleType.LISTENING, _ma.ModuleType.TIME_NUMBERS, _ma.ModuleType.GRAMMAR,
            _ma.ModuleType.VOCABULARY, _ma.ModuleType.READING, _ma.ModuleType.SPEAKING
        ]
        question_order = []
        for mt in module_order:
            for q in questions.get(mt.value, []):
                question_order.append(q["id"])
        # When assessment is department-based, never allow empty question set (would trigger generic fallback in UI)
        if department and len(question_order) == 0:
            raise ValueError(
                f"No questions available for department '{department}'. "
                "Please load the full question bank (30 departments × 100 questions) via Admin and try again."
            )
        assessment.question_order = question_order
        # #region agent log
        try:
            import json
            _p = __import__("pathlib").Path(__file__).resolve().parents[4] / "debug-ccd1fc.log"
            _listening = questions.get("listening", [])
            _first = _listening[0] if _listening else None
            _d = {"assessment_id": assessment_id, "department": department, "first_3_ids": question_order[:3], "first_listening_id": _first["id"] if _first else None, "first_listening_text": (_first.get("question_text") or "")[:80] if _first else None}
            with open(_p, "a", encoding="utf-8") as _f:
                _f.write(json.dumps({"sessionId":"ccd1fc","location":"assessment_engine.py:132","message":"start_assessment question_order built","data":_d,"hypothesisId":"H4","timestamp":int(__import__("time").time()*1000)}) + "\n")
        except Exception:
            pass
        # #endregion

        await self.db.flush()
        await self.db.commit()

        return {
            "assessment_id": assessment.id,
            "session_id": assessment.session_id,
            "status": assessment.status,
            "questions": questions,
            "expires_at": assessment.expires_at,
            "total_questions": len(questions)
        }

    async def _generate_question_set(
        self, division: _ma.DivisionType, department: Optional[str] = None
    ) -> Dict[str, List[Dict]]:
        """Generate randomized question set for assessment - Optimized with single query.

        When department is set (from invitation), selects department-specific questions.
        Falls back to division-only if not enough department-specific questions exist.
        """

        questions = {
            "listening": [],
            "time_numbers": [],
            "grammar": [],
            "vocabulary": [],
            "reading": [],
            "speaking": []
        }

        # Questions per module (21 questions total = 100 points)
        questions_per_module = {
            _ma.ModuleType.LISTENING: 3,      # 3 questions: 5+5+6 = 16 points
            _ma.ModuleType.TIME_NUMBERS: 3,   # 3 questions: 5+5+6 = 16 points
            _ma.ModuleType.GRAMMAR: 4,        # 4 questions: 4+4+4+4 = 16 points
            _ma.ModuleType.VOCABULARY: 4,     # 4 questions: 4+4+4+4 = 16 points
            _ma.ModuleType.READING: 4,        # 4 questions: 4+4+4+4 = 16 points
            _ma.ModuleType.SPEAKING: 3        # 3 questions: 7+7+6 = 20 points
        }
        
        # Build filter: division always required.
        # When department is set: use ONLY department-specific questions; do not add generic (department IS NULL)
        # to the main pool. We will add generic only per-module when department-specific count is insufficient.
        base_filter = _ma.Question.division == division
        if department:
            q_filter = and_(base_filter, _ma.Question.department == department)
        else:
            q_filter = base_filter

        # Fetch questions: department-specific only when department set, else all division
        result = await self.db.execute(select(_ma.Question).where(q_filter))
        all_questions = result.scalars().all()

        # Group questions by module type in memory (much faster than multiple DB queries)
        questions_by_module = {}
        for question in all_questions:
            if question.module_type not in questions_by_module:
                questions_by_module[question.module_type] = []
            questions_by_module[question.module_type].append(question)

        # Track content keys already used so we never show the same question (or same prompt+content) twice
        used_content_keys = set()

        def _dedupe_and_filter(questions: list) -> list:
            """Deduplicate by content key and exclude already-used keys."""
            seen_key = {}
            for q in questions:
                k = self._question_content_key(q)
                if k and k not in seen_key:
                    seen_key[k] = q
            deduped = list(seen_key.values())
            return [q for q in deduped if self._question_content_key(q) not in used_content_keys]

        # Now select questions for each module
        for module_type, count in questions_per_module.items():
            available_questions = list(questions_by_module.get(module_type, []))

            if department:
                # Department set: by default prefer department-specific, then generic (department NULL),
                # then any division question, then sample creation.
                # STRICT_DEPARTMENT_QUESTION_BANK: only questions for this department (no fillers).
                available_questions = _dedupe_and_filter(available_questions)
                if not settings.STRICT_DEPARTMENT_QUESTION_BANK:
                    if len(available_questions) < count:
                        fallback_result = await self.db.execute(
                            select(_ma.Question).where(
                                and_(
                                    _ma.Question.module_type == module_type,
                                    _ma.Question.division == division,
                                    _ma.Question.department.is_(None),
                                )
                            )
                        )
                        generic = fallback_result.scalars().all()
                        available_questions = _dedupe_and_filter(available_questions + list(generic))

                    if len(available_questions) < count:
                        result = await self.db.execute(
                            select(_ma.Question).where(
                                and_(
                                    _ma.Question.module_type == module_type,
                                    _ma.Question.division == division,
                                )
                            )
                        )
                        available_questions = _dedupe_and_filter(list(result.scalars().all()))

                    if len(available_questions) < count:
                        await self._create_sample_questions(module_type, division)
                        result = await self.db.execute(
                            select(_ma.Question).where(
                                and_(
                                    _ma.Question.module_type == module_type,
                                    _ma.Question.division == division,
                                )
                            )
                        )
                        available_questions = _dedupe_and_filter(list(result.scalars().all()))

                if module_type == _ma.ModuleType.SPEAKING and available_questions:
                    selected_questions = self._select_speaking_questions(available_questions, count)
                else:
                    n_select = min(count, len(available_questions))
                    selected_questions = (
                        random.sample(available_questions, n_select) if n_select else []
                    )
            else:
                # No department: allow generic, division fallback, sample creation
                available_questions = _dedupe_and_filter(available_questions)
                if len(available_questions) < count:
                    fallback_result = await self.db.execute(
                        select(_ma.Question).where(
                            and_(
                                _ma.Question.module_type == module_type,
                                _ma.Question.division == division,
                                _ma.Question.department.is_(None),
                            )
                        )
                    )
                    generic = fallback_result.scalars().all()
                    available_questions = _dedupe_and_filter(available_questions + list(generic))

                if len(available_questions) < count:
                    result = await self.db.execute(
                        select(_ma.Question).where(
                            and_(
                                _ma.Question.module_type == module_type,
                                _ma.Question.division == division
                            )
                        )
                    )
                    available_questions = _dedupe_and_filter(list(result.scalars().all()))

                if len(available_questions) < count:
                    await self._create_sample_questions(module_type, division)
                    result = await self.db.execute(
                        select(_ma.Question).where(
                            and_(
                                _ma.Question.module_type == module_type,
                                _ma.Question.division == division
                            )
                        )
                    )
                    available_questions = _dedupe_and_filter(list(result.scalars().all()))

                if module_type == _ma.ModuleType.SPEAKING and available_questions:
                    selected_questions = self._select_speaking_questions(available_questions, count)
                else:
                    n_select = min(count, len(available_questions))
                    selected_questions = (
                        random.sample(available_questions, n_select) if n_select else []
                    )

            # Mark selected content keys as used so they are not repeated in later modules
            for q in selected_questions:
                k = self._question_content_key(q)
                if k:
                    used_content_keys.add(k)

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
                    "metadata": q.question_metadata
                }
                for q in selected_questions
            ]

        return questions

    async def submit_response(self, assessment_id: int, question_id: int,
                            user_answer: str, time_spent: int = None) -> Dict[str, Any]:
        """Submit answer for a question - Optimized with parallel queries"""
        
        import asyncio
        
        # Parallel query execution - Reduce 3 sequential queries to 1 parallel batch
        assessment_query = select(_ma.Assessment).where(_ma.Assessment.id == assessment_id)
        question_query = select(_ma.Question).where(_ma.Question.id == question_id)
        existing_query = select(_ma.AssessmentResponse).where(
                and_(
                _ma.AssessmentResponse.assessment_id == assessment_id,
                _ma.AssessmentResponse.question_id == question_id
            )
        )
        
        # Execute all queries in parallel
        assessment_result, question_result, existing_result = await asyncio.gather(
            self.db.execute(assessment_query),
            self.db.execute(question_query),
            self.db.execute(existing_query)
        )
        
        assessment = assessment_result.scalar_one_or_none()
        question = question_result.scalar_one_or_none()
        existing = existing_result.scalar_one_or_none()

        # Validation
        if not assessment or not question:
            raise ValueError("Assessment or question not found")

        if assessment.status != _ma.AssessmentStatus.IN_PROGRESS:
            raise ValueError("Assessment is not in progress")

        if existing:
            raise ValueError("Question already answered")

        # Score the response
        is_correct, points_earned = await self._score_response(question, user_answer)

        # Create response record
        response = _ma.AssessmentResponse(
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

    async def _score_response(self, question: _ma.Question, user_answer: str) -> Tuple[bool, float]:
        """
        Score a user's response to a question

        Now handles all question types properly including:
        - CATEGORY_MATCH (vocabulary module)
        - TITLE_SELECTION (reading module)
        """

        if question.question_type == _ma.QuestionType.MULTIPLE_CHOICE:
            is_correct = user_answer.strip().lower() == question.correct_answer.strip().lower()
            points = question.points if is_correct else 0

        elif question.question_type == _ma.QuestionType.FILL_BLANK:
            # More flexible matching for fill-in-the-blank (time & numbers)
            is_correct = self._flexible_text_match(user_answer, question.correct_answer)
            points = question.points if is_correct else 0

        elif question.question_type == _ma.QuestionType.CATEGORY_MATCH:
            # Vocabulary module - match category terms
            is_correct = self._score_category_match(user_answer, question.correct_answer)
            points = question.points if is_correct else 0

        elif question.question_type == _ma.QuestionType.TITLE_SELECTION:
            # Reading module - select best title
            is_correct = user_answer.strip().lower() == question.correct_answer.strip().lower()
            points = question.points if is_correct else 0

        elif question.question_type == _ma.QuestionType.SPEAKING_RESPONSE:
            # Default: deterministic keyword + fluency scoring (listen-repeat and scenario with expected_keywords).
            # Opt-in LLM: set question_metadata.use_llm_scoring to true.
            transcript, recording_duration = self._parse_speaking_user_answer(user_answer)
            if self._transcript_is_invalid_speaking(transcript):
                return False, 0.0

            meta = question.question_metadata or {}
            if self._speaking_use_deterministic(question):
                keywords = self._speaking_expected_keywords(question)
                if not keywords:
                    keywords = self._keywords_from_reference_text(question.question_text or "")
                if not keywords:
                    return False, 0.0
                sr = score_speaking_response(
                    transcript=transcript,
                    expected_keywords=keywords,
                    question_context=question.question_text or "",
                    recording_duration=recording_duration,
                    base_points=float(question.points),
                )
                points = round(min(float(question.points), max(0.0, sr.total_points)), 2)
                is_correct = sr.percentage >= 60.0
            else:
                # Legacy LLM path (explicit opt-in only)
                if user_answer and "|" in user_answer and user_answer.strip().startswith("recorded_"):
                    parts = user_answer.split("|", 1)
                    tr = parts[1].strip() if len(parts) > 1 else ""
                    analysis = await self.ai_service.analyze_speech_from_transcript(
                        tr, question.correct_answer or "", question.question_text or ""
                    )
                elif self._looks_like_audio_file_path(user_answer):
                    analysis = await self.ai_service.analyze_speech_response(
                        user_answer, question.correct_answer or "", question.question_text or ""
                    )
                else:
                    analysis = await self.ai_service.analyze_speech_from_transcript(
                        transcript, question.correct_answer or "", question.question_text or ""
                    )
                is_correct = analysis["overall_score"] >= 0.6
                raw_points = float(analysis.get("total_points", 0))
                points = round((raw_points / 20.0) * question.points, 2)
                points = min(question.points, max(0, points))

        else:
            # Default exact match for any other type
            is_correct = user_answer.strip().lower() == question.correct_answer.strip().lower()
            points = question.points if is_correct else 0

        return is_correct, points

    @staticmethod
    def _parse_speaking_user_answer(user_answer: str) -> Tuple[str, float]:
        """Parse unified `recorded_XXs|transcript` or plain transcript; return (transcript, duration_sec)."""
        s = (user_answer or "").strip()
        if not s:
            return "", 0.0
        if s.startswith("recorded_") and "|" in s:
            head, rest = s.split("|", 1)
            m = re.match(r"recorded_(\d+(?:\.\d+)?)s?", head.strip(), re.I)
            duration = float(m.group(1)) if m else 0.0
            return rest.strip(), duration
        return s, 0.0

    @staticmethod
    def _looks_like_audio_file_path(user_answer: str) -> bool:
        s = (user_answer or "").strip()
        if not s or "|" in s:
            return False
        low = s.lower()
        return low.endswith((".wav", ".webm", ".mp3", ".m4a", ".ogg", ".flac"))

    @staticmethod
    def _transcript_is_invalid_speaking(transcript: str) -> bool:
        t = (transcript or "").strip().lower()
        if not t:
            return True
        if t.startswith("[no transcription") or t.startswith("[no speech"):
            return True
        if t == "analysis unavailable":
            return True
        # UI test bypass used to send a long placeholder transcript that scored as real speech
        if "automated testing bypass" in t or "recording bypassed" in t:
            return True
        if "test mode" in t and "bypass" in t:
            return True
        return False

    @staticmethod
    def _speaking_use_deterministic(question: _ma.Question) -> bool:
        meta = question.question_metadata or {}
        return not bool(meta.get("use_llm_scoring"))

    @staticmethod
    def _keywords_from_reference_text(text: str) -> List[str]:
        words = re.findall(r"[A-Za-z]{3,}", (text or "").lower())
        out: List[str] = []
        seen = set()
        for w in words:
            if w in _SPEAKING_STOPWORDS or w in seen:
                continue
            seen.add(w)
            out.append(w)
        return out[:15]

    @staticmethod
    def _speaking_expected_keywords(question: _ma.Question) -> List[str]:
        """Resolve expected keywords from metadata, audio_text, reference_text, or correct_answer."""
        meta = question.question_metadata or {}
        raw = meta.get("expected_keywords")
        keywords: List[str] = []

        if isinstance(raw, list):
            keywords = [str(k).strip() for k in raw if str(k).strip()]
        elif isinstance(raw, str):
            rs = raw.strip()
            if rs.startswith("["):
                try:
                    parsed = json.loads(rs)
                    if isinstance(parsed, list):
                        keywords = [str(k).strip() for k in parsed if str(k).strip()]
                except (json.JSONDecodeError, TypeError):
                    pass
            if not keywords:
                keywords = [k.strip() for k in rs.split(",") if k.strip()]

        if not keywords and meta.get("audio_text"):
            keywords = AssessmentEngine._keywords_from_reference_text(str(meta["audio_text"]))
        if not keywords and meta.get("reference_text"):
            keywords = AssessmentEngine._keywords_from_reference_text(str(meta["reference_text"]))

        if not keywords and (question.correct_answer or "").strip():
            ca = question.correct_answer.strip()
            if ca.startswith("["):
                try:
                    parsed = json.loads(ca)
                    if isinstance(parsed, list):
                        keywords = [str(k).strip() for k in parsed if str(k).strip()]
                except (json.JSONDecodeError, TypeError):
                    pass
            if not keywords:
                keywords = [k.strip() for k in ca.split(",") if k.strip()]

        return keywords[:20]

    @staticmethod
    def _normalized_question_stem(text: str) -> str:
        """Lowercase + collapse whitespace so the same stem is not reused across modules (e.g. Grammar vs Listening)."""
        return " ".join((text or "").strip().lower().split())

    @staticmethod
    def _select_speaking_questions(available: List[Any], count: int) -> List[Any]:
        """Prefer listen-and-repeat items with audio, then repeat without audio, then scenario."""
        tier0, tier1, tier2 = [], [], []
        for q in available:
            meta = getattr(q, "question_metadata", None) or {}
            st = str(meta.get("speaking_type") or "").lower()
            has_audio = bool(
                meta.get("audio_text")
                or meta.get("audio")
                or getattr(q, "audio_file_path", None)
                or meta.get("audio_file_path")
            )
            if st == "repeat" and has_audio:
                tier0.append(q)
            elif st == "repeat":
                tier1.append(q)
            else:
                tier2.append(q)
        selected: List[Any] = []
        for pool in (tier0, tier1, tier2):
            random.shuffle(pool)
            for item in pool:
                if len(selected) >= count:
                    break
                selected.append(item)
            if len(selected) >= count:
                break
        if len(selected) < count:
            remainder = [q for q in available if q not in selected]
            random.shuffle(remainder)
            for item in remainder:
                if len(selected) >= count:
                    break
                selected.append(item)
        return selected[:count]

    def _question_content_key(self, q) -> str:
        """
        Unique key for deduplication: same prompt + same content (terms/passage) = same question.
        Vocabulary: question_text + sorted terms; Reading: question_text + passage;
        others: normalized question stem (case/spacing insensitive).
        """
        text = (q.question_text or "").strip()
        meta = getattr(q, "question_metadata", None) or {}
        if q.module_type == _ma.ModuleType.VOCABULARY:
            terms = meta.get("terms") or []
            return self._normalized_question_stem(text) + "|" + "|".join(sorted(str(t) for t in terms))
        if q.module_type == _ma.ModuleType.READING:
            passage = (meta.get("passage") or "").strip()
            return self._normalized_question_stem(text) + "|" + passage
        return self._normalized_question_stem(text)

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

        # User number with unit suffix in correct (e.g. "25" matches "25 knots")
        try:
            user_num = int(user_clean.replace(" ", ""))
            if correct_clean.startswith(str(user_num) + " ") or correct_clean.startswith(str(user_num) + "\t"):
                return True
        except ValueError:
            pass

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
            # Strict format: do not match word form with digit form (e.g. "seven" vs "7")
            user_is_digit = user.strip().replace(" ", "").replace(",", "").replace(".", "").isdigit()
            correct_is_digit = correct.strip().replace(" ", "").replace(",", "").replace(".", "").isdigit()
            if user_is_digit != correct_is_digit:
                return False
            return user_num == correct_num

        return False

    async def complete_assessment(self, assessment_id: int) -> Dict[str, Any]:
        """Complete assessment and calculate final scores"""

        # Get assessment with responses
        assessment_result = await self.db.execute(
            select(_ma.Assessment).where(_ma.Assessment.id == assessment_id)
        )
        assessment = assessment_result.scalar_one_or_none()

        if not assessment:
            raise ValueError("Assessment not found")

        # Get all responses
        responses_result = await self.db.execute(
            select(_ma.AssessmentResponse).where(_ma.AssessmentResponse.assessment_id == assessment_id)
        )
        responses = responses_result.scalars().all()

        # Calculate scores using scoring engine
        scores = await self.scoring_engine.calculate_final_scores(responses)

        # Update assessment
        assessment.status = _ma.AssessmentStatus.COMPLETED
        assessment.completed_at = datetime.now()
        assessment.total_score = scores["total_score"]

        # Module scores
        assessment.listening_score = scores.get("listening", 0)
        assessment.time_numbers_score = scores.get("time_numbers", 0)
        assessment.grammar_score = scores.get("grammar", 0)
        assessment.vocabulary_score = scores.get("vocabulary", 0)
        assessment.reading_score = scores.get("reading", 0)
        assessment.speaking_score = scores.get("speaking", 0)

        # Pass/fail — persisted `passed` must match API `passed` (total + safety + speaking)
        _, safety_ok, speaking_ok, final_pass = compute_overall_pass(
            float(scores["total_score"]),
            float(scores.get("speaking", 0)),
            float(scores["safety_pass_rate"]),
        )
        assessment.passed = final_pass
        assessment.safety_questions_passed = safety_ok
        assessment.speaking_threshold_passed = speaking_ok

        # Generate feedback
        feedback = await self._generate_assessment_feedback(scores, final_pass)
        assessment.feedback = feedback
        
        # Mark invitation code as completed if this assessment was from an invitation
        from sqlalchemy import select

        inv_result = await self.db.execute(
            select(_ma.InvitationCode).where(
                _ma.InvitationCode.used_by_user_id == assessment.user_id,
                _ma.InvitationCode.is_used == True,
                _ma.InvitationCode.assessment_completed == False
            )
        )
        invitation = inv_result.scalar_one_or_none()
        
        if invitation:
            invitation.assessment_completed = True

        await self.db.commit()

        return {
            "assessment_id": assessment.id,
            "total_score": assessment.total_score,
            "passed": final_pass,
            "scores": scores,
            "feedback": feedback,
            "completed_at": assessment.completed_at
        }

    async def _generate_feedback(self, question: _ma.Question, user_answer: str, is_correct: bool) -> str:
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

    def _get_sample_questions_for_module(
        self, module_type: _ma.ModuleType, division: _ma.DivisionType, need_count: int
    ) -> List[Dict[str, Any]]:
        """Return sample question dicts for a module/division so we always have enough per-division questions."""
        div_val = division.value
        # Division-agnostic samples (same content for all divisions; can be extended to division-specific later)
        if module_type == _ma.ModuleType.LISTENING:
            # Listening: question_text = prompt; question_metadata.audio_text = dialogue for TTS
            samples = [
                {
                    "question_text": "What time is the reservation?",
                    "question_type": _ma.QuestionType.MULTIPLE_CHOICE,
                    "options": ["6 PM", "7 PM", "8 PM", "4 PM"],
                    "correct_answer": "7 PM",
                    "points": 5,
                    "question_metadata": {
                        "audio_text": "Hello, I would like to book a table for four people at seven PM tonight, please."
                    },
                },
                {
                    "question_text": "What is the room number?",
                    "question_type": _ma.QuestionType.MULTIPLE_CHOICE,
                    "options": ["8245", "8254", "8524", "2548"],
                    "correct_answer": "8254",
                    "points": 5,
                    "question_metadata": {
                        "audio_text": "Excuse me, the air conditioning is way too cold in room eight-two-five-four. Could you please send someone to fix it?"
                    },
                },
                {
                    "question_text": "What deck is the buffet restaurant on?",
                    "question_type": _ma.QuestionType.MULTIPLE_CHOICE,
                    "options": ["Deck 10", "Deck 12", "Deck 14", "Deck 16"],
                    "correct_answer": "Deck 12",
                    "points": 6,
                    "question_metadata": {
                        "audio_text": "Excuse me, I am trying to find the buffet restaurant. Is it on deck twelve or deck fourteen? Yes sir, the buffet restaurant is on deck twelve."
                    },
                },
            ]
        elif module_type == _ma.ModuleType.TIME_NUMBERS:
            samples = [
                {"question_text": "What time does breakfast start? (e.g. 7:00)", "question_type": _ma.QuestionType.FILL_BLANK, "options": None, "correct_answer": "7:00", "points": 5, "question_metadata": {"audio_text": "Good morning! Breakfast is served from seven AM to ten-thirty AM daily in the main dining room."}},
                {"question_text": "How many guests are in the reservation?", "question_type": _ma.QuestionType.FILL_BLANK, "options": None, "correct_answer": "8", "points": 5, "question_metadata": {"audio_text": "We need a table for eight people at six-thirty tonight. Can you accommodate us?"}},
                {"question_text": "What is the cabin number?", "question_type": _ma.QuestionType.FILL_BLANK, "options": None, "correct_answer": "9173", "points": 6, "question_metadata": {"audio_text": "I am in cabin nine one seven three and my safe is not working properly. Could you send maintenance?"}},
            ]
        elif module_type == _ma.ModuleType.GRAMMAR:
            samples = [
                {"question_text": "___ I help you with your luggage?", "question_type": _ma.QuestionType.MULTIPLE_CHOICE, "options": ["May", "Do", "Will", "Am"], "correct_answer": "May", "points": 4, "question_metadata": None},
                {"question_text": "The guest ___ arrived at the port this morning.", "question_type": _ma.QuestionType.MULTIPLE_CHOICE, "options": ["have", "has", "had", "having"], "correct_answer": "has", "points": 4, "question_metadata": None},
                {"question_text": "Could you please ___ me to the spa?", "question_type": _ma.QuestionType.MULTIPLE_CHOICE, "options": ["direct", "directing", "directed", "direction"], "correct_answer": "direct", "points": 4, "question_metadata": None},
                {"question_text": "The restaurant is ___ the third deck.", "question_type": _ma.QuestionType.MULTIPLE_CHOICE, "options": ["in", "on", "at", "by"], "correct_answer": "on", "points": 4, "question_metadata": None},
            ]
        elif module_type == _ma.ModuleType.VOCABULARY:
            samples = [
                {"question_text": "Match the cruise ship terms with their meanings:", "question_type": _ma.QuestionType.CATEGORY_MATCH, "options": None, "correct_answer": "{}", "points": 4, "question_metadata": {"terms": ["Bridge", "Gangway", "Tender", "Muster"], "definitions": ["Ship's walkway to shore", "Emergency assembly", "Small boat for shore trips", "Ship's control center"], "correct_matches": {"Bridge": "Ship's control center", "Gangway": "Ship's walkway to shore", "Tender": "Small boat for shore trips", "Muster": "Emergency assembly"}}},
                {"question_text": "Match the hospitality terms:", "question_type": _ma.QuestionType.CATEGORY_MATCH, "options": None, "correct_answer": "{}", "points": 4, "question_metadata": {"terms": ["Concierge", "Amenities", "Excursion", "Embark"], "definitions": ["To board the ship", "Guest services specialist", "Shore activities", "Hotel facilities"], "correct_matches": {"Concierge": "Guest services specialist", "Amenities": "Hotel facilities", "Excursion": "Shore activities", "Embark": "To board the ship"}}},
                {"question_text": "Match the dining terms:", "question_type": _ma.QuestionType.CATEGORY_MATCH, "options": None, "correct_answer": "{}", "points": 4, "question_metadata": {"terms": ["Buffet", "A la carte", "Galley", "Sommelier"], "definitions": ["Wine expert", "Self-service dining", "Ship's kitchen", "Menu with individual prices"], "correct_matches": {"Buffet": "Self-service dining", "A la carte": "Menu with individual prices", "Galley": "Ship's kitchen", "Sommelier": "Wine expert"}}},
                {"question_text": "Match the safety terms:", "question_type": _ma.QuestionType.CATEGORY_MATCH, "options": None, "correct_answer": "{}", "points": 4, "question_metadata": {"terms": ["Muster drill", "Life jacket", "Assembly station", "All aboard"], "definitions": ["Final boarding call", "Safety meeting", "Personal flotation device", "Emergency meeting point"], "correct_matches": {"Muster drill": "Safety meeting", "Life jacket": "Personal flotation device", "Assembly station": "Emergency meeting point", "All aboard": "Final boarding call"}}},
            ]
        elif module_type == _ma.ModuleType.READING:
            samples = [
                {"question_text": "What should guests do if they miss the ship's departure?", "question_type": _ma.QuestionType.MULTIPLE_CHOICE, "options": ["Wait at the port", "Contact the Port Agent", "Call the cruise line", "Take a taxi to catch up"], "correct_answer": "Contact the Port Agent", "points": 4, "question_metadata": {"passage": "IMPORTANT NOTICE: Ship departures are strictly scheduled. Guests who miss departure must contact the Port Agent immediately."}},
                {"question_text": "What time does the casino close?", "question_type": _ma.QuestionType.MULTIPLE_CHOICE, "options": ["12:00 AM", "1:00 AM", "2:00 AM", "3:00 AM"], "correct_answer": "2:00 AM", "points": 4, "question_metadata": {"passage": "CASINO HOURS: Sea Days: 8:00 AM - 2:00 AM | Port Days: 6:00 PM - 2:00 AM. Guests must be 21+ to gamble."}},
                {"question_text": "What is required for the specialty restaurant?", "question_type": _ma.QuestionType.MULTIPLE_CHOICE, "options": ["Formal attire", "Reservations", "Advance payment", "Group booking"], "correct_answer": "Reservations", "points": 4, "question_metadata": {"passage": "SPECIALTY DINING: Reservations required for all specialty restaurants. Cover charges apply. Dress code: Smart casual after 6 PM."}},
                {"question_text": "When is the muster drill scheduled?", "question_type": _ma.QuestionType.MULTIPLE_CHOICE, "options": ["3:00 PM", "4:00 PM", "5:00 PM", "6:00 PM"], "correct_answer": "4:00 PM", "points": 4, "question_metadata": {"passage": "SAFETY FIRST: All guests must participate in the mandatory muster drill. Drill times: Embarkation Day at 4:00 PM."}},
            ]
        elif module_type == _ma.ModuleType.SPEAKING:
            samples = [
                {"question_text": "Listen to the audio and repeat exactly what you hear.", "question_type": _ma.QuestionType.SPEAKING_RESPONSE, "options": None, "correct_answer": "", "points": 7, "question_metadata": {"speaking_type": "repeat", "audio_text": "Good morning! Welcome aboard. My name is Maria and I will be your cabin steward during this voyage.", "min_duration": 3, "expected_keywords": ["welcome", "aboard", "cabin", "steward", "voyage"]}},
                {"question_text": "Listen to the audio and repeat exactly what you hear.", "question_type": _ma.QuestionType.SPEAKING_RESPONSE, "options": None, "correct_answer": "", "points": 7, "question_metadata": {"speaking_type": "repeat", "audio_text": "The pool deck is located on deck twelve. Please remember to bring your cruise card for towel service.", "min_duration": 3, "expected_keywords": ["pool", "deck", "twelve", "cruise", "card", "towel"]}},
                {"question_text": "Listen to the audio and repeat exactly what you hear.", "question_type": _ma.QuestionType.SPEAKING_RESPONSE, "options": None, "correct_answer": "", "points": 6, "question_metadata": {"speaking_type": "repeat", "audio_text": "The spa is on deck twelve, forward. Take the midship elevators up two levels, then follow the signs to the wellness center.", "min_duration": 3, "expected_keywords": ["spa", "deck", "twelve", "forward", "elevators", "signs", "wellness"]}},
            ]
        else:
            return []
        return samples[:need_count] if need_count <= len(samples) else samples

    async def _create_sample_questions(self, module_type: _ma.ModuleType, division: _ma.DivisionType):
        """Create sample questions when question bank is empty. Ensures enough questions per module per division."""
        questions_per_module = {
            _ma.ModuleType.LISTENING: 3,
            _ma.ModuleType.TIME_NUMBERS: 3,
            _ma.ModuleType.GRAMMAR: 4,
            _ma.ModuleType.VOCABULARY: 4,
            _ma.ModuleType.READING: 4,
            _ma.ModuleType.SPEAKING: 3,
        }
        need_count = questions_per_module.get(module_type, 0)
        if need_count <= 0:
            return
        sample_questions = self._get_sample_questions_for_module(module_type, division, need_count)
        for q_data in sample_questions:
            meta = q_data.get("question_metadata")
            question = _ma.Question(
                module_type=module_type,
                division=division,
                question_type=q_data.get("question_type", _ma.QuestionType.MULTIPLE_CHOICE),
                question_text=q_data["question_text"],
                options=q_data.get("options"),
                correct_answer=q_data["correct_answer"],
                points=q_data["points"],
                question_metadata=meta,
            )
            self.db.add(question)
        await self.db.flush()
        await self.db.commit()