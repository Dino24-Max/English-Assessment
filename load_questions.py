"""
Load questions from questions_config.json into database
"""
import asyncio
import json
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from src.main.python.models.assessment import Question, QuestionType, ModuleType
from src.main.python.models.base import Base

DATABASE_URL = "sqlite+aiosqlite:///src/main/python/data/assessment.db"

async def load_questions():
    """Load questions from JSON into database"""

    # Create engine
    engine = create_async_engine(DATABASE_URL, echo=True)

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create session
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # Load questions from JSON
    with open("src/main/python/data/questions_config.json", "r", encoding="utf-8") as f:
        questions_data = json.load(f)

    async with async_session() as session:
        # Check if questions already loaded
        from sqlalchemy import select, func
        result = await session.execute(select(func.count(Question.id)))
        count = result.scalar()

        if count > 0:
            print(f"⚠️  Questions already loaded ({count} questions). Skipping...")
            return

        print(f"📝 Loading {len(questions_data)} questions into database...")

        # Map modules to types
        module_map = {
            "listening": ModuleType.LISTENING,
            "time_numbers": ModuleType.TIME_NUMBERS,
            "grammar": ModuleType.GRAMMAR,
            "vocabulary": ModuleType.VOCABULARY,
            "reading": ModuleType.READING,
            "speaking": ModuleType.SPEAKING
        }

        # Determine question types based on module
        type_map = {
            "listening": QuestionType.MULTIPLE_CHOICE,
            "time_numbers": QuestionType.FILL_BLANK,
            "grammar": QuestionType.MULTIPLE_CHOICE,
            "vocabulary": QuestionType.CATEGORY_MATCH,
            "reading": QuestionType.TITLE_SELECTION,
            "speaking": QuestionType.SPEAKING
        }

        # Load each question
        for q_num_str, q_data in questions_data.items():
            q_num = int(q_num_str)
            module = q_data["module"]

            # Create question object
            question = Question(
                id=q_num,  # Use question number as ID
                module_type=module_map[module],
                question_type=type_map[module],
                question_text=q_data["question"],
                audio_text=q_data.get("audio_text"),
                options=q_data.get("options", []),
                correct_answer=q_data["correct"],
                points=q_data["points"],
                is_safety_related=False  # Can be customized later
            )

            session.add(question)
            print(f"✅ Added Q{q_num}: {module} - {q_data['question'][:50]}...")

        await session.commit()
        print(f"\n🎉 Successfully loaded {len(questions_data)} questions!")

if __name__ == "__main__":
    asyncio.run(load_questions())
