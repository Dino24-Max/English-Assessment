"""
Ensure an admin user exists in the database. Creates one if none found.
"""
import sqlite3
from pathlib import Path

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

db_path = Path(__file__).parent.parent / "data" / "assessment.db"
conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

# Check for admin users
cursor.execute('SELECT id, email, is_admin FROM users WHERE is_admin = 1')
admins = cursor.fetchall()
print(f'Admin users: {admins if admins else "None"}')

# If no admin, create one
if not admins:
    print("Creating admin user...")
    password_hash = pwd_context.hash("admin123")
    cursor.execute('''
        INSERT INTO users (first_name, last_name, email, password_hash, nationality, division, is_active, is_admin)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', ('Admin', 'User', 'admin@test.com', password_hash, 'US', 'HOTEL', 1, 1))
    conn.commit()
    print("Admin user created: admin@test.com / admin123")

conn.close()
