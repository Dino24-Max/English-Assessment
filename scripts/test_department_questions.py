"""
Verify that department-specific question sets differ (Housekeeping vs Guest Services).
Run from project root: python scripts/test_department_questions.py
"""
import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src" / "main" / "python"))


async def main():
    from sqlalchemy import select
    from core.database import async_session_maker
    from core.assessment_engine import AssessmentEngine
    import models.assessment as _ma

    async with async_session_maker() as db:
        engine = AssessmentEngine(db)
        division = _ma.DivisionType.HOTEL

        for dept_name, department in [("Housekeeping", "HOUSEKEEPING"), ("Guest Services", "GUEST SERVICES")]:
            questions = await engine._generate_question_set(division, department=department)
            listening = questions.get("listening", [])
            first = listening[0] if listening else None
            if first:
                qtext = (first.get("question_text") or "")[:120]
                print(f"{dept_name} (department={department}): first listening question_id={first.get('id')}, text_prefix={qtext!r}...")
            else:
                print(f"{dept_name} (department={department}): no listening questions")

        # Compare: fetch first question IDs from two fresh "assessments" by generating sets again
        set_h = await engine._generate_question_set(division, department="HOUSEKEEPING")
        set_g = await engine._generate_question_set(division, department="GUEST SERVICES")
        ids_h = [q["id"] for m in ["listening", "time_numbers", "grammar", "vocabulary", "reading", "speaking"] for q in set_h.get(m, [])]
        ids_g = [q["id"] for m in ["listening", "time_numbers", "grammar", "vocabulary", "reading", "speaking"] for q in set_g.get(m, [])]
        same_first = ids_h and ids_g and ids_h[0] == ids_g[0]
        print(f"\nFirst question ID Housekeeping: {ids_h[0] if ids_h else None}, Guest Services: {ids_g[0] if ids_g else None}")
        print("PASS: Departments get different first questions" if not same_first else "FAIL: Both departments got the same first question (check DB has department-specific questions)")


if __name__ == "__main__":
    asyncio.run(main())
