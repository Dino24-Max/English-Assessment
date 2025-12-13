#!/usr/bin/env python3
"""
Check database status - see what data exists
"""

import sqlite3
from pathlib import Path

db_path = Path(__file__).parent.parent / "data" / "assessment.db"

if not db_path.exists():
    print(f"Database not found at: {db_path}")
    exit(1)

conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

print("=" * 70)
print("Database Status Check")
print("=" * 70)

# Get all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [t[0] for t in cursor.fetchall()]

print(f"\nTables found: {len(tables)}")
for table in tables:
    cursor.execute(f"SELECT COUNT(*) FROM {table}")
    count = cursor.fetchone()[0]
    print(f"  {table}: {count} records")

# Check users
print("\n" + "=" * 70)
print("Users:")
print("=" * 70)
cursor.execute("SELECT id, email, first_name, last_name, is_admin, created_at FROM users ORDER BY id")
users = cursor.fetchall()
if users:
    for u in users:
        print(f"  ID: {u[0]}, Email: {u[1]}, Name: {u[2]} {u[3]}, Admin: {u[4]}, Created: {u[5]}")
else:
    print("  No users found")

# Check assessments
print("\n" + "=" * 70)
print("Assessments:")
print("=" * 70)
cursor.execute("SELECT id, user_id, status, total_score, completed_at FROM assessments ORDER BY id")
assessments = cursor.fetchall()
if assessments:
    for a in assessments:
        print(f"  ID: {a[0]}, User: {a[1]}, Status: {a[2]}, Score: {a[3]}, Completed: {a[4]}")
else:
    print("  No assessments found")

# Check invitation codes
print("\n" + "=" * 70)
print("Invitation Codes:")
print("=" * 70)
cursor.execute("SELECT id, code, email, is_used, assessment_completed, created_at FROM invitation_codes ORDER BY id")
invitations = cursor.fetchall()
if invitations:
    for inv in invitations:
        print(f"  ID: {inv[0]}, Code: {inv[1][:8]}..., Email: {inv[2]}, Used: {inv[3]}, Completed: {inv[4]}, Created: {inv[5]}")
else:
    print("  No invitation codes found")

conn.close()

print("\n" + "=" * 70)

