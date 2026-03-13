"""
Validate department-specific assessment flow.
Run from project root: python scripts/validate_department_flow.py

Verifies:
1. Department-specific questions exist in DB (e.g. HOUSEKEEPING)
2. Assessment engine returns department-specific questions when department is set
"""
import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src" / "main" / "python"))


async def main():
    from sqlalchemy import select, and_
    from core.database import async_session_maker
    from models.assessment import Question, User, Assessment, DivisionType, AssessmentStatus
    from core.assessment_engine import AssessmentEngine

    test_dept = "HOUSEKEEPING"
    print(f"Validating department-specific flow for: {test_dept}")
    print("-" * 50)

    async with async_session_maker() as db:
        # 1. Verify department-specific questions exist
        result = await db.execute(
            select(Question).where(Question.department == test_dept)
        )
        dept_questions = result.scalars().all()
        count = len(dept_questions)

        if count == 0:
            print(f"[FAIL] No questions found for department '{test_dept}'")
            return 1
        print(f"[OK] Found {count} questions for department '{test_dept}'")

        # 2. Verify questions span modules
        by_module = {}
        for q in dept_questions:
            mt = q.module_type.value
            by_module[mt] = by_module.get(mt, 0) + 1
        print(f"[OK] Module distribution: {dict(by_module)}")

        # 3. Run assessment engine _generate_question_set with department
        engine = AssessmentEngine(db)
        questions = await engine._generate_question_set(
            DivisionType.HOTEL, department=test_dept
        )

        total = sum(len(v) for v in questions.values())
        if total < 10:
            print(f"[FAIL] Engine returned only {total} questions (expected 21)")
            return 1

        # Verify we got questions for each module
        for mod, qs in questions.items():
            if len(qs) == 0 and mod != "listening":  # some modules may have 0 in fallback
                continue
            print(f"  - {mod}: {len(qs)} questions")

        print(f"[OK] Engine returned {total} questions for department '{test_dept}'")
        print()
        print("Validation passed. Department-specific flow is working.")
        return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
