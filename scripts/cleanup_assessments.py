#!/usr/bin/env python3
"""
Cleanup Assessment Data Script
删除所有评估数据，只保留第一条和最后两条
"""

import asyncio
import sys
from pathlib import Path

# Add src/main/python to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src" / "main" / "python"))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select, delete, func
from sqlalchemy.orm import selectinload
from models.assessment import Assessment, AssessmentResponse
from core.config import settings


async def cleanup_assessments():
    """Delete assessment data, keep only first and last two records"""
    
    # Create database engine
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False
    )
    
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        try:
            # Query completed assessments (matching API query exactly)
            # API uses: Assessment.status == "completed" (string comparison)
            from models.assessment import AssessmentStatus
            from sqlalchemy import and_
            
            # Try enum first
            result = await session.execute(
                select(Assessment)
                .where(Assessment.status == AssessmentStatus.COMPLETED)
                .order_by(Assessment.id)
            )
            all_assessments = result.scalars().all()
            
            # If that doesn't work, try string comparison (like API does)
            if len(all_assessments) == 0:
                from sqlalchemy import cast, String
                result = await session.execute(
                    select(Assessment)
                    .where(cast(Assessment.status, String) == "completed")
                    .order_by(Assessment.id)
                )
                all_assessments = result.scalars().all()
            
            # Also check all assessments
            result_all = await session.execute(
                select(Assessment)
                .order_by(Assessment.id)
            )
            all_status = result_all.scalars().all()
            
            print(f"All assessments (any status): {len(all_status)}")
            print(f"Completed assessments (enum): {len(all_assessments)}")
            
            # If still no results, use all assessments
            if len(all_assessments) == 0 and len(all_status) > 0:
                print("No completed assessments found, using all assessments")
                all_assessments = all_status
            
            total_count = len(all_assessments)
            print(f"Found {total_count} assessment records")
            
            if total_count == 0:
                print("No assessment records found in database")
                return
            
            if total_count <= 3:
                print(f"Assessment count ({total_count}) <= 3, no deletion needed")
                print("Current records:")
                for a in all_assessments:
                    print(f"  - ID: {a.id}, User ID: {a.user_id}, Status: {a.status}, Score: {a.total_score}")
                return
            
            # Get first and last two IDs
            first_id = all_assessments[0].id
            last_two_ids = [all_assessments[-2].id, all_assessments[-1].id]
            keep_ids = [first_id] + last_two_ids
            
            print(f"\nKeeping records with IDs: {keep_ids}")
            print(f"  First: ID {first_id}")
            print(f"  Last two: ID {last_two_ids[0]}, ID {last_two_ids[1]}")
            
            # Find IDs to delete
            delete_ids = [a.id for a in all_assessments if a.id not in keep_ids]
            
            if not delete_ids:
                print("No records to delete")
                return
            
            print(f"\nPreparing to delete {len(delete_ids)} records")
            print(f"IDs to delete: {delete_ids}")
            
            # Confirm deletion
            print("\nDeleting records...")
            
            # Delete assessment records (CASCADE will auto-delete related AssessmentResponse)
            delete_count = 0
            for assessment_id in delete_ids:
                result = await session.execute(
                    delete(Assessment).where(Assessment.id == assessment_id)
                )
                delete_count += result.rowcount
            
            await session.commit()
            
            print(f"\nSuccessfully deleted {delete_count} assessment records")
            print(f"Kept {len(keep_ids)} records")
            
            # Verify results
            result = await session.execute(
                select(Assessment)
                .order_by(Assessment.id)
            )
            remaining = result.scalars().all()
            
            print(f"\nRemaining assessment records: {len(remaining)}")
            print("\nDetails:")
            for assessment in remaining:
                print(f"  - ID: {assessment.id}, User ID: {assessment.user_id}, Status: {assessment.status.value}, Score: {assessment.total_score}, Completed: {assessment.completed_at}")
            
        except Exception as e:
            await session.rollback()
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
            raise
        finally:
            await engine.dispose()


if __name__ == "__main__":
    print("=" * 60)
    print("Cleanup Assessment Data - Keep First and Last Two")
    print("=" * 60)
    print()
    
    asyncio.run(cleanup_assessments())
    
    print()
    print("=" * 60)
    print("Cleanup completed!")
    print("=" * 60)

