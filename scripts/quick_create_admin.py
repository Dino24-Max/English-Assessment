#!/usr/bin/env python3
"""
Quick Admin Creation - Non-interactive version
Creates admin@carnival.com with password: admin123
"""

import asyncio
import sys
from pathlib import Path

# Add src/main/python to path
project_root = Path(__file__).parent.parent
src_path = project_root / "src" / "main" / "python"
sys.path.insert(0, str(src_path))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from core.database import engine
from models.assessment import User, DivisionType
from utils.auth import hash_password


async def create_default_admin():
    """Create default admin user: admin@carnival.com / admin123"""
    
    email = "admin@carnival.com"
    password = "admin123"
    
    try:
        async with AsyncSession(engine) as db:
            # Check if admin already exists
            result = await db.execute(
                select(User).where(User.email == email)
            )
            existing_user = result.scalar_one_or_none()
            
            if existing_user:
                # Update existing user to admin
                existing_user.is_admin = True
                existing_user.password_hash = hash_password(password)
                await db.commit()
                print(f"[OK] Updated existing user {email} to admin")
            else:
                # Create new admin user
                admin_user = User(
                    first_name="Admin",
                    last_name="User",
                    email=email,
                    password_hash=hash_password(password),
                    nationality="Admin",
                    division=DivisionType.HOTEL,
                    department="Admin",
                    is_active=True,
                    is_admin=True
                )
                
                db.add(admin_user)
                await db.commit()
                print(f"[OK] Created admin user {email}")
            
            print("\n" + "=" * 70)
            print("Admin Account Ready!")
            print("=" * 70)
            print(f"Email: {email}")
            print(f"Password: {password}")
            print("\nLogin at: http://127.0.0.1:8000/login")
            print("Note: Admin login checkbox has been removed. Admin status is detected automatically.")
            print("=" * 70)
            
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(create_default_admin())

