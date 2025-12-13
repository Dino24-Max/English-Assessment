#!/usr/bin/env python3
"""
Check english_assessment.db - the database with actual data
"""

import sqlite3
from pathlib import Path

db_path = Path(__file__).parent.parent / "src" / "main" / "python" / "english_assessment.db"

if not db_path.exists():
    print(f"Database not found at: {db_path}")
    exit(1)

conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

print("=" * 70)
print("Checking english_assessment.db")
print("=" * 70)

# Check users
print("\nUsers:")
cursor.execute("SELECT id, email, first_name, last_name, is_admin FROM users ORDER BY id")
users = cursor.fetchall()
for u in users:
    print(f"  ID: {u[0]}, Email: {u[1]}, Name: {u[2]} {u[3]}, Admin: {u[4]}")

# Check assessments
print("\nAssessments (ordered by ID):")
cursor.execute("SELECT id, user_id, status, total_score, completed_at FROM assessments ORDER BY id")
assessments = cursor.fetchall()
for a in assessments:
    print(f"  ID: {a[0]}, User: {a[1]}, Status: {a[2]}, Score: {a[3]}, Completed: {a[4]}")

if len(assessments) > 0:
    print(f"\nTotal assessments: {len(assessments)}")
    print(f"First ID: {assessments[0][0]}")
    if len(assessments) >= 2:
        print(f"Last two IDs: {assessments[-2][0]}, {assessments[-1][0]}")
        print(f"\nShould keep: ID {assessments[0][0]} (first) and IDs {assessments[-2][0]}, {assessments[-1][0]} (last two)")
        delete_ids = [a[0] for a in assessments[1:-2]] if len(assessments) > 3 else []
        if delete_ids:
            print(f"Should delete: {delete_ids}")

conn.close()

