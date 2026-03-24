"""
Test: (1) Auto-load question bank when empty, (2) Questions match link department.
Run from project root: python scripts/test_auto_load_and_department.py
       With full bank load: python scripts/test_auto_load_and_department.py --force-load
"""
import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
python_src = project_root / "src" / "main" / "python"
sys.path.insert(0, str(python_src))

FORCE_LOAD = "--force-load" in sys.argv


async def main():
    from sqlalchemy import select, func
    from core.database import async_session_maker
    from models.assessment import Question, Assessment, DivisionType
    from data.question_bank_loader import QuestionBankLoader
    from core.assessment_engine import AssessmentEngine
    import models.assessment as _ma

    print("=== 1. Check question count and auto-load if empty ===")
    async with async_session_maker() as db:
        r = await db.execute(select(func.count()).select_from(Question))
        question_count = r.scalar() or 0
        print(f"   Current question count: {question_count}")

        if question_count == 0 or FORCE_LOAD:
            data_dir = Path(__file__).resolve().parent.parent / "src" / "main" / "python" / "data"
            full_path = data_dir / "question_bank_full.json"
            sample_path = data_dir / "question_bank_sample.json"
            json_path = full_path if full_path.exists() else (sample_path if sample_path.exists() else None)
            if json_path:
                loader = QuestionBankLoader(db)
                n = await loader.load_full_question_bank(json_file_path=str(json_path), clear_first=True)
                print(f"   Loaded {n} questions from {json_path.name}" + (" (force-load)" if FORCE_LOAD else " (auto-load)"))
                question_count = n
            else:
                print("   SKIP: No question_bank_full.json or question_bank_sample.json found.")
                return
        else:
            print("   Skipping load (bank already present).")

    if question_count == 0:
        print("   FAIL: No questions in DB after load.")
        return

    print("\n=== 2. Department consistency: assessment questions match link department ===")
    async with async_session_maker() as db:
        engine = AssessmentEngine(db)
        department = "INFOTAINMENT"
        division = DivisionType.HOTEL

        # Create assessment with department (as when generating invitation link)
        assessment = await engine.create_assessment(
            user_id=1,
            division=division,
            department=department,
            auto_commit=False,
        )
        await db.flush()
        await engine.start_assessment(assessment.id)
        await db.refresh(assessment)

        order = assessment.question_order or []
        if not order:
            print(f"   FAIL: assessment has no question_order (department={department})")
            return

        # Verify every question in question_order belongs to this department
        result = await db.execute(select(Question).where(Question.id.in_(order)))
        questions = result.scalars().all()
        by_id = {q.id: q for q in questions}
        bad = []
        for qid in order:
            q = by_id.get(qid)
            if not q:
                bad.append((qid, "not_found"))
            elif (q.department or "").strip().upper() != department.upper():
                bad.append((qid, f"department={q.department!r}"))

        if bad:
            print(f"   FAIL: {len(bad)} questions do not match department {department!r}: {bad[:5]}{'...' if len(bad) > 5 else ''}")
        else:
            print(f"   PASS: All {len(order)} questions belong to department {department!r}.")

    print("\n=== Done ===")


if __name__ == "__main__":
    asyncio.run(main())
