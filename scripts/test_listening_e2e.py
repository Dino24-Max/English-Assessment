"""
E2E test: verify listening question shows new format (natural dialogue + no spoilers).
Run from project root: python scripts/test_listening_e2e.py
"""
import asyncio
import json
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src" / "main" / "python"))


async def main():
    from core.assessment_engine import AssessmentEngine
    from core.database import async_session_maker
    from models.assessment import Question, User, DivisionType
    from sqlalchemy import select

    # 1. Get or create user
    async with async_session_maker() as db:
        result = await db.execute(
            select(User).where(User.division == "hotel").limit(1)
        )
        user = result.scalar_one_or_none()
        if not user:
            user = User(
                email="test_listening@test.com",
                password_hash="x",
                division="hotel",
                department="FRONT_DESK",
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)

        # 2. Create NEW assessment and start it
        engine = AssessmentEngine(db)
        assessment = await engine.create_assessment(
            user_id=user.id,
            division=DivisionType.HOTEL,
            department="FRONT_DESK",
        )
        await engine.start_assessment(assessment.id)
        await db.refresh(assessment)
        aid = assessment.id
        q1_id = (assessment.question_order or [])[0] if assessment.question_order else None

    if not q1_id:
        print("FAIL: Assessment has no question_order")
        return 1

    # 3. Fetch Q1 from DB and verify format
    async with async_session_maker() as db:
        result = await db.execute(select(Question).where(Question.id == q1_id))
        q = result.scalar_one_or_none()
    if not q:
        print(f"FAIL: Question {q1_id} not found")
        return 1

    meta = q.question_metadata or {}
    if isinstance(meta, str):
        meta = json.loads(meta or "{}")
    audio = meta.get("audio_text") or meta.get("audio") or ""
    qt = q.question_text or ""

    spoiler_phrases = ["fifty", "50", "guest says", "they said", "answer is"]
    has_spoiler = any(p.lower() in qt.lower() for p in spoiler_phrases)
    has_dialogue = any(
        x in audio.lower() for x in ["how can i help", "yes, ", "let me", "i need", "?"]
    )

    print("--- Listening E2E verification ---")
    print(f"Assessment {aid}, Q1 id={q1_id}")
    print(f"Question: {qt[:100]}...")
    print(f"Audio: {audio[:200]}...")
    print()
    print(f"  No spoiler in question: {'PASS' if not has_spoiler else 'FAIL'}")
    print(f"  Natural dialogue:       {'PASS' if has_dialogue else 'FAIL'}")

    if has_spoiler or not has_dialogue:
        return 1
    print("\nPASS: Listening format updated correctly.")
    return 0


if __name__ == "__main__":
    exit(asyncio.run(main()))
