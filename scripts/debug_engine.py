"""Debug assessment engine - run with logging to see _generate_question_set output."""
import asyncio
import logging
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(name)s: %(message)s")

sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "main" / "python"))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text, select, and_

_db_path = Path(__file__).parent.parent / "data" / "assessment.db"
DB_URL = f"sqlite+aiosqlite:///{_db_path.resolve()}"


async def main():
    engine = create_async_engine(DB_URL)
    # Raw SQL sanity check
    async with engine.begin() as conn:
        r = await conn.execute(
            text("SELECT COUNT(*) FROM questions WHERE division='hotel' AND department='HOUSEKEEPING'")
        )
        print(f"Raw SQL count: {r.scalar()}")
        r = await conn.execute(text("SELECT id FROM users WHERE department='HOUSEKEEPING' LIMIT 1"))
        row = r.fetchone()
    user_id = row[0]

    # Direct ORM query - same as _generate_question_set
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as db:
        from models.assessment import Question, DivisionType
        base_filter = Question.division == DivisionType.HOTEL
        q_filter = and_(base_filter, Question.department == "HOUSEKEEPING")
        r = await db.execute(select(Question).where(q_filter))
        orm_questions = r.scalars().all()
        print(f"ORM query count: {len(orm_questions)}")
        if orm_questions:
            q0 = orm_questions[0]
            print(f"  First: id={q0.id}, division={q0.division!r}, dept={q0.department!r}")

    async with async_session() as db:
        from core.assessment_engine import AssessmentEngine
        from models.assessment import DivisionType
        e = AssessmentEngine(db)
        a = await e.create_assessment(
            user_id=user_id,
            division=DivisionType.HOTEL,
            department="HOUSEKEEPING",
        )
        await e.start_assessment(a.id)
        print(f"question_order len={len(a.question_order or [])}")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
