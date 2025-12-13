#!/usr/bin/env python3
"""Check database tables and columns"""

import sqlite3
from pathlib import Path

db_path = Path(__file__).parent.parent / "data" / "assessment.db"

conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

# Get all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [t[0] for t in cursor.fetchall()]
print(f"Tables: {tables}")

# Check password_reset_tokens
if 'password_reset_tokens' in tables:
    cursor.execute("PRAGMA table_info(password_reset_tokens)")
    cols = cursor.fetchall()
    print(f"password_reset_tokens columns: {[c[1] for c in cols]}")
else:
    print("password_reset_tokens table does not exist - needs to be created")

conn.close()

