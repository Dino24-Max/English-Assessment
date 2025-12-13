#!/usr/bin/env python3
"""
Create Admin User Script
Creates an admin user account for accessing admin panel
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
from core.database import engine, get_db
from models.assessment import User, DivisionType
from utils.auth import hash_password


async def create_admin_user():
    """Create an admin user account"""
    
    print("=" * 70)
    print("Create Admin User Account")
    print("=" * 70)
    print()
    
    # Get admin details from user input
    print("Enter admin account details:")
    first_name = input("First Name: ").strip()
    last_name = input("Last Name: ").strip()
    email = input("Email: ").strip()
    password = input("Password (min 6 chars): ").strip()
    nationality = input("Nationality (optional, default=Admin): ").strip() or "Admin"
    
    if not all([first_name, last_name, email, password]):
        print("\n❌ Error: All fields except nationality are required")
        return
    
    if len(password) < 6:
        print("\n❌ Error: Password must be at least 6 characters")
        return
    
    # Confirm creation
    print("\n" + "-" * 70)
    print("Creating admin account with:")
    print(f"  Name: {first_name} {last_name}")
    print(f"  Email: {email}")
    print(f"  Nationality: {nationality}")
    print(f"  Admin: Yes ✅")
    print("-" * 70)
    
    confirm = input("\nProceed? (yes/no): ").strip().lower()
    if confirm not in ['yes', 'y']:
        print("❌ Cancelled")
        return
    
    # Create user in database
    try:
        async with AsyncSession(engine) as db:
            # Check if email already exists
            result = await db.execute(
                select(User).where(User.email == email)
            )
            existing_user = result.scalar_one_or_none()
            
            if existing_user:
                print(f"\n⚠️  User with email {email} already exists")
                update = input("Update this user to admin? (yes/no): ").strip().lower()
                
                if update in ['yes', 'y']:
                    existing_user.is_admin = True
                    existing_user.password_hash = hash_password(password)
                    await db.commit()
                    print(f"\n✅ User {email} updated to admin successfully!")
                else:
                    print("❌ Cancelled")
                return
            
            # Create new admin user
            admin_user = User(
                first_name=first_name,
                last_name=last_name,
                email=email,
                password_hash=hash_password(password),
                nationality=nationality,
                division=DivisionType.HOTEL,  # Default, not used for admin
                department="Admin",
                is_active=True,
                is_admin=True  # Admin flag
            )
            
            db.add(admin_user)
            await db.commit()
            await db.refresh(admin_user)
            
            print("\n" + "=" * 70)
            print("✅ Admin User Created Successfully!")
            print("=" * 70)
            print(f"User ID: {admin_user.id}")
            print(f"Email: {admin_user.email}")
            print(f"Name: {admin_user.first_name} {admin_user.last_name}")
            print(f"Admin: Yes ✅")
            print("\nYou can now login at: http://127.0.0.1:8000/login")
            print("Make sure to check the '🔐 Admin Login' checkbox when logging in!")
            print("=" * 70)
            
    except Exception as e:
        print(f"\n❌ Error creating admin user: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("\n🔐 Admin User Creation Tool\n")
    asyncio.run(create_admin_user())

