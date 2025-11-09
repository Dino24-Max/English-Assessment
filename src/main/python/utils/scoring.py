"""
Scoring engine for assessments
Handles point calculations and pass/fail determination
"""

from typing import Dict, List, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.assessment import AssessmentResponse, Question, ModuleType
from core.config import settings


class ScoringEngine:
    """Handles assessment scoring logic"""

    def __init__(self, db: AsyncSession):
        """
        Initialize scoring engine with database session

        Args:
            db: Required database session for querying question details
        """
        if db is None:
            raise ValueError("Database session is required for ScoringEngine")
        self.db = db
        self.module_max_points = {
            "listening": 16,
            "time_numbers": 16,
            "grammar": 16,
            "vocabulary": 16,
            "reading": 16,
            "speaking": 20
        }

    async def calculate_final_scores(self, responses: List[AssessmentResponse]) -> Dict[str, Any]:
        """
        Calculate final scores from all responses

        This method now eagerly loads question data to avoid N+1 queries
        and properly tracks safety questions
        """

        scores = {
            "listening": 0,
            "time_numbers": 0,
            "grammar": 0,
            "vocabulary": 0,
            "reading": 0,
            "speaking": 0,
            "total_score": 0,
            "safety_questions_correct": 0,
            "safety_questions_total": 0,
            "safety_pass_rate": 0.0
        }

        if not responses:
            return scores

        # Eagerly fetch all question details in one query to avoid N+1
        question_ids = [r.question_id for r in responses]
        stmt = select(Question).where(Question.id.in_(question_ids))
        result = await self.db.execute(stmt)
        questions_map = {q.id: q for q in result.scalars().all()}

        # Group responses by module
        module_responses = {}
        safety_responses = {"correct": 0, "total": 0}

        for response in responses:
            # Get question from our pre-fetched map
            question = questions_map.get(response.question_id)
            if not question:
                continue  # Skip if question not found

            module_key = question.module_type.value

            if module_key not in module_responses:
                module_responses[module_key] = []

            module_responses[module_key].append(response)

            # Track safety questions properly
            if question.is_safety_related:
                safety_responses["total"] += 1
                if response.is_correct:
                    safety_responses["correct"] += 1

        # Calculate module scores
        for module, module_responses_list in module_responses.items():
            if module in self.module_max_points:
                total_points = sum(r.points_earned for r in module_responses_list)
                scores[module] = min(total_points, self.module_max_points[module])

        # Calculate total score (cap at 100.0)
        scores["total_score"] = min(100.0, sum(scores[module] for module in self.module_max_points.keys()))

        # Safety questions pass rate
        if safety_responses["total"] > 0:
            scores["safety_pass_rate"] = safety_responses["correct"] / safety_responses["total"]
            scores["safety_questions_correct"] = safety_responses["correct"]
            scores["safety_questions_total"] = safety_responses["total"]
        else:
            # No safety questions: default to passing (or set policy as needed)
            scores["safety_pass_rate"] = 1.0

        return scores

    async def _get_module_from_question_id(self, question_id: int) -> ModuleType:
        """Get module type from question ID by querying database"""
        if not self.db:
            # Fallback if no database session provided
            return ModuleType.LISTENING

        try:
            # Query database for question's module type
            stmt = select(Question.module_type).where(Question.id == question_id)
            result = await self.db.execute(stmt)
            module_type = result.scalar_one_or_none()

            if module_type:
                return module_type
            else:
                # Default if question not found
                return ModuleType.LISTENING
        except Exception:
            # Fallback on error
            return ModuleType.LISTENING

    def calculate_module_score(self, responses: List[AssessmentResponse], module: str) -> float:
        """Calculate score for specific module"""
        total_points = sum(r.points_earned for r in responses)
        max_points = self.module_max_points.get(module, 20)
        return min(total_points, max_points)

    def determine_pass_fail(self, scores: Dict[str, Any]) -> Dict[str, bool]:
        """Determine pass/fail status based on all criteria"""

        criteria = {
            "total_score_pass": scores["total_score"] >= settings.PASS_THRESHOLD_TOTAL,
            "safety_questions_pass": scores["safety_pass_rate"] >= settings.PASS_THRESHOLD_SAFETY,
            "speaking_pass": scores.get("speaking", 0) >= settings.PASS_THRESHOLD_SPEAKING,
            "overall_pass": False
        }

        # Overall pass requires all individual criteria
        criteria["overall_pass"] = all([
            criteria["total_score_pass"],
            criteria["safety_questions_pass"],
            criteria["speaking_pass"]
        ])

        return criteria

    def generate_performance_report(self, scores: Dict[str, Any]) -> Dict[str, Any]:
        """Generate detailed performance report"""

        report = {
            "scores": scores,
            "pass_fail": self.determine_pass_fail(scores),
            "strengths": [],
            "weaknesses": [],
            "recommendations": []
        }

        # Identify strengths and weaknesses
        for module, score in scores.items():
            if module in self.module_max_points:
                percentage = (score / self.module_max_points[module]) * 100

                if percentage >= 80:
                    report["strengths"].append(f"Strong performance in {module.replace('_', ' ').title()}")
                elif percentage < 60:
                    report["weaknesses"].append(f"Needs improvement in {module.replace('_', ' ').title()}")

        # Generate recommendations
        if not report["pass_fail"]["speaking_pass"]:
            report["recommendations"].append(
                "Focus on improving speaking skills through practice scenarios"
            )

        if not report["pass_fail"]["safety_questions_pass"]:
            report["recommendations"].append(
                "Review safety procedures and emergency protocols"
            )

        return report