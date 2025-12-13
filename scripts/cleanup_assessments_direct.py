#!/usr/bin/env python3
"""
Direct cleanup using raw SQL - matches API query exactly
"""

import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src" / "main" / "python"))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text
from core.config import settings


async def cleanup_direct():
    """Direct cleanup using raw SQL"""
    
    engine = create_async_engine(settings.DATABASE_URL, echo=True)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        try:
            # Query completed assessments using raw SQL (matching API)
            result = await session.execute(
                text("SELECT id, user_id, status, total_score, completed_at FROM assessments WHERE status = 'completed' ORDER BY id")
            )
            rows = result.fetchall()
            
            print(f"Found {len(rows)} completed assessments:")
            for row in rows:
                print(f"  ID: {row[0]}, User: {row[1]}, Status: {row[2]}, Score: {row[3]}, Completed: {row[4]}")
            
            if len(rows) == 0:
                print("No completed assessments found")
                return
            
            if len(rows) <= 3:
                print(f"Only {len(rows)} records, keeping all")
                return
            
            # Get IDs
            ids = [row[0] for row in rows]
            first_id = ids[0]
            last_two_ids = [ids[-2], ids[-1]]
            keep_ids = [first_id] + last_two_ids
            delete_ids = [id for id in ids if id not in keep_ids]
            
            print(f"\nKeeping IDs: {keep_ids}")
            print(f"  First: {first_id}")
            print(f"  Last two: {last_two_ids}")
            print(f"\nDeleting IDs: {delete_ids}")
            
            # Delete using raw SQL
            for aid in delete_ids:
                await session.execute(text(f"DELETE FROM assessments WHERE id = {aid}"))
            
            await session.commit()
            
            print(f"\nSuccessfully deleted {len(delete_ids)} records")
            
            # Verify
            result = await session.execute(
                text("SELECT id, user_id, total_score FROM assessments WHERE status = 'completed' ORDER BY id")
            )
            remaining = result.fetchall()
            
            print(f"\nRemaining {len(remaining)} records:")
            for row in remaining:
                print(f"  ID: {row[0]}, User: {row[1]}, Score: {row[2]}")
            
        except Exception as e:
            await session.rollback()
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await engine.dispose()


if __name__ == "__main__":
    print("=" * 60)
    print("Direct Cleanup - Raw SQL")
    print("=" * 60)
    asyncio.run(cleanup_direct())
    print("=" * 60)

