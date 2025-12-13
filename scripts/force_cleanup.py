#!/usr/bin/env python3
"""
Force cleanup - directly query and delete from database
This script will find ALL assessments and keep only first and last two
"""

import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src" / "main" / "python"))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select, delete, text
from models.assessment import Assessment, AssessmentStatus
from core.config import settings


async def force_cleanup():
    """Force cleanup - query all assessments regardless of status"""
    
    engine = create_async_engine(settings.DATABASE_URL, echo=True)  # Enable echo to see SQL
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        try:
            # Try raw SQL first to see what's actually in the database
            result = await session.execute(text("SELECT id, user_id, status, total_score FROM assessments ORDER BY id"))
            raw_rows = result.fetchall()
            print(f"Raw SQL query found {len(raw_rows)} records:")
            for row in raw_rows:
                print(f"  ID: {row[0]}, User: {row[1]}, Status: {row[2]}, Score: {row[3]}")
            
            # Now use ORM query
            result = await session.execute(
                select(Assessment).order_by(Assessment.id)
            )
            all_assessments = result.scalars().all()
            
            print(f"\nORM query found {len(all_assessments)} records")
            
            if len(all_assessments) == 0:
                print("\nNo assessments found. Checking if table exists...")
                result = await session.execute(text("SELECT COUNT(*) FROM assessments"))
                count = result.scalar()
                print(f"Direct COUNT query: {count} records")
                
                if count > 0:
                    print("Records exist but ORM query returns 0. This might be a status enum issue.")
                    # Try querying with raw SQL
                    result = await session.execute(
                        text("SELECT id FROM assessments ORDER BY id")
                    )
                    ids = [row[0] for row in result.fetchall()]
                    print(f"Found IDs via raw SQL: {ids}")
                    
                    if len(ids) > 3:
                        # Keep first and last two
                        keep_ids = [ids[0], ids[-2], ids[-1]]
                        delete_ids = [id for id in ids if id not in keep_ids]
                        
                        print(f"\nKeeping IDs: {keep_ids}")
                        print(f"Deleting IDs: {delete_ids}")
                        
                        # Delete using raw SQL
                        for aid in delete_ids:
                            await session.execute(text(f"DELETE FROM assessments WHERE id = {aid}"))
                        
                        await session.commit()
                        print(f"Deleted {len(delete_ids)} records using raw SQL")
                return
            
            if len(all_assessments) <= 3:
                print(f"Only {len(all_assessments)} records, keeping all")
                return
            
            # Get first and last two
            first_id = all_assessments[0].id
            last_two_ids = [all_assessments[-2].id, all_assessments[-1].id]
            keep_ids = [first_id] + last_two_ids
            delete_ids = [a.id for a in all_assessments if a.id not in keep_ids]
            
            print(f"\nKeeping: {keep_ids}")
            print(f"Deleting: {delete_ids}")
            
            # Delete
            for aid in delete_ids:
                await session.execute(delete(Assessment).where(Assessment.id == aid))
            
            await session.commit()
            print(f"Successfully deleted {len(delete_ids)} records")
            
        except Exception as e:
            await session.rollback()
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await engine.dispose()


if __name__ == "__main__":
    print("=" * 60)
    print("FORCE CLEANUP - Direct Database Query")
    print("=" * 60)
    asyncio.run(force_cleanup())
    print("=" * 60)

