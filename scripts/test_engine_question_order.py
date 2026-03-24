"""Test that AssessmentEngine.start_assessment persists question_order."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "main" / "python"))
import json
import os
import sqlite3

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

_db_path = Path(__file__).parent.parent / "data" / "assessment.db"
DB_URL = os.getenv("DATABASE_URL", f"sqlite+aiosqlite:///{_db_path.resolve()}")


async def test():
    engine = create_async_engine(DB_URL)
    async with engine.begin() as conn:
        result = await conn.execute(
            text("SELECT id FROM users WHERE (division='hotel' OR division='HOTEL') AND department='HOUSEKEEPING' LIMIT 1")
        )
        row = result.fetchone()
    if not row:
        print("No user found")
        return
    user_id = row[0]
    print(f"Using user_id={user_id}")

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as db:
        from core.assessment_engine import AssessmentEngine

        engine_obj = AssessmentEngine(db)
        from models.assessment import DivisionType

        assessment = await engine_obj.create_assessment(
            user_id=user_id,
            division=DivisionType.HOTEL,
            department="HOUSEKEEPING",
        )
        print(f"Created assessment {assessment.id}")
        await engine_obj.start_assessment(assessment.id)
        print(f"After start: question_order len={len(assessment.question_order or [])}")
        aid = assessment.id

    # Verify in DB with raw sqlite
    c = sqlite3.connect("data/assessment.db")
    cur = c.execute("SELECT id, question_order FROM assessments WHERE id=?", (aid,))
    row = cur.fetchone()
    if row:
        qo = json.loads(row[1]) if row[1] else []
        print(f"DB check: assessment {row[0]}, question_order len={len(qo)}")
    c.close()
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(test())
