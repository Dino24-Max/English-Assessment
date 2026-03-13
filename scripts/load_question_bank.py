"""
Load the full question bank into the database.
Run from project root: python scripts/load_question_bank.py
"""
import asyncio
import sqlite3
import sys
from pathlib import Path

# Add src/main/python to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src" / "main" / "python"))


def _truncate_questions(db_path: Path):
    """Clear questions table before load to avoid duplicates on re-run."""
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute("DELETE FROM questions")
    conn.commit()
    conn.close()
    print("Cleared existing questions (will reload from JSON).")


def _ensure_questions_schema(db_path: Path):
    """Add missing columns to questions table if needed (migration for existing DBs)."""
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(questions)")
    columns = [row[1] for row in cursor.fetchall()]
    for col_name, col_def in [
        ("cefr_level", "VARCHAR(2)"),
        ("scenario_id", "INTEGER"),
        ("scenario_description", "TEXT"),
        ("question_metadata", "TEXT"),  # SQLite stores JSON as TEXT
    ]:
        if col_name not in columns:
            cursor.execute(f"ALTER TABLE questions ADD COLUMN {col_name} {col_def}")
            print(f"Added column: {col_name}")
    conn.commit()
    conn.close()


async def main():
    from core.config import settings
    from core.database import async_session_maker
    from data.question_bank_loader import QuestionBankLoader

    # Resolve DB path (sqlite URL like sqlite+aiosqlite:///./data/assessment.db)
    url = settings.DATABASE_URL
    if "sqlite" in url:
        db_path = project_root / "data" / "assessment.db"
        if db_path.exists():
            _ensure_questions_schema(db_path)
            _truncate_questions(db_path)

    async with async_session_maker() as db:
        loader = QuestionBankLoader(db)
        count = await loader.load_full_question_bank()
        print(f"Done. Loaded {count} questions.")


if __name__ == "__main__":
    asyncio.run(main())
