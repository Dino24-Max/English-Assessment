#!/usr/bin/env python3
"""
Database Migration: Add is_admin column to users table
"""

import asyncio
import sys
from pathlib import Path

# Add src/main/python to path
project_root = Path(__file__).parent.parent
src_path = project_root / "src" / "main" / "python"
sys.path.insert(0, str(src_path))

from sqlalchemy.ext.asyncio import AsyncSession
from core.database import engine


async def add_is_admin_column():
    """Add is_admin column to users table"""
    
    print("=" * 70)
    print("Database Migration: Adding is_admin column")
    print("=" * 70)
    
    try:
        async with engine.begin() as conn:
            # Add is_admin column with default value False
            await conn.execute(
                text("ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT 0")
            )
            
            print("✅ Successfully added is_admin column to users table")
            print("   Default value: False (0)")
            
            # Create index
            try:
                await conn.execute(
                    text("CREATE INDEX ix_users_admin ON users (is_admin, is_active)")
                )
                print("✅ Created index: ix_users_admin")
            except Exception as e:
                print(f"⚠️  Index creation skipped (may already exist): {e}")
        
        print("\n" + "=" * 70)
        print("Migration Complete!")
        print("=" * 70)
        print("\nNext step: Run python scripts/quick_create_admin.py")
        
    except Exception as e:
        if "duplicate column name" in str(e).lower():
            print("✅ Column is_admin already exists, no migration needed")
        else:
            print(f"❌ Error during migration: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    from sqlalchemy import text
    asyncio.run(add_is_admin_column())

