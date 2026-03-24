"""
Delete all generic questions (department IS NULL) from the question bank.
Same effect as POST /api/v1/admin/questions/delete-generic.
Run from project root: python scripts/delete_generic_questions.py
"""
import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src" / "main" / "python"))


async def main():
    from sqlalchemy import delete
    from core.database import async_session_maker
    from models.assessment import Question

    async with async_session_maker() as db:
        result = await db.execute(delete(Question).where(Question.department.is_(None)))
        await db.commit()
        deleted = result.rowcount or 0
    print(f"Deleted {deleted} generic questions (department IS NULL).")


if __name__ == "__main__":
    asyncio.run(main())
