#!/usr/bin/env python3
"""Check assessment records in database"""

import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src" / "main" / "python"))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select
from models.assessment import Assessment
from core.config import settings


async def check_assessments():
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        result = await session.execute(
            select(Assessment).order_by(Assessment.id)
        )
        assessments = result.scalars().all()
        
        print(f"Total assessments: {len(assessments)}")
        for a in assessments:
            print(f"ID: {a.id}, User: {a.user_id}, Score: {a.total_score}, Completed: {a.completed_at}")
    
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(check_assessments())

