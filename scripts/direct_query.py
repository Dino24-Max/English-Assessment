#!/usr/bin/env python3
"""Direct SQLite query to check assessments"""

import sqlite3
from pathlib import Path

db_path = Path(__file__).parent.parent / "data" / "assessment.db"

if not db_path.exists():
    print(f"Database not found at: {db_path}")
    exit(1)

conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

# Check tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print(f"Tables: {[t[0] for t in tables]}")

# Count assessments
cursor.execute("SELECT COUNT(*) FROM assessments")
count = cursor.fetchone()[0]
print(f"\nTotal assessments: {count}")

# Get all assessments
cursor.execute("SELECT id, user_id, status, total_score, completed_at FROM assessments ORDER BY id")
rows = cursor.fetchall()

print(f"\nAll assessment records ({len(rows)}):")
for row in rows:
    print(f"  ID={row[0]}, User={row[1]}, Status={row[2]}, Score={row[3]}, Completed={row[4]}")

conn.close()

