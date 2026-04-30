"""Temporary debug script to inspect assessment DB for speaking scoring issues."""
import sqlite3
import json
from pathlib import Path

db_path = Path(__file__).parent / "data" / "assessment.db"
print(f"DB path: {db_path}")
print(f"Exists: {db_path.exists()}")

if not db_path.exists():
    print("DATABASE FILE NOT FOUND!")
    exit(1)

conn = sqlite3.connect(str(db_path))
conn.row_factory = sqlite3.Row
c = conn.cursor()

# List tables
c.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in c.fetchall()]
print(f"\nTables: {tables}")

# Find assessment table
for t in tables:
    if "assess" in t.lower() or "answer" in t.lower() or "response" in t.lower():
        c.execute(f"SELECT sql FROM sqlite_master WHERE name='{t}'")
        schema = c.fetchone()
        print(f"\n--- Schema for {t} ---")
        print(schema[0] if schema else "N/A")

# Try to find latest assessment
for t in tables:
    if "assess" in t.lower():
        try:
            c.execute(f"SELECT * FROM {t} ORDER BY rowid DESC LIMIT 3")
            rows = c.fetchall()
            print(f"\n--- Latest 3 rows from {t} ---")
            for r in rows:
                print(dict(r))
        except Exception as e:
            print(f"Error querying {t}: {e}")

# Try to find speaking answers/responses
for t in tables:
    if "answer" in t.lower() or "response" in t.lower():
        try:
            c.execute(f"SELECT * FROM {t} ORDER BY rowid DESC LIMIT 10")
            rows = c.fetchall()
            print(f"\n--- Latest 10 rows from {t} ---")
            for r in rows:
                d = dict(r)
                # Truncate long values for display
                for k, v in d.items():
                    if isinstance(v, str) and len(v) > 200:
                        d[k] = v[:200] + "..."
                print(d)
        except Exception as e:
            print(f"Error querying {t}: {e}")

# Look for questions table
for t in tables:
    if "question" in t.lower():
        try:
            c.execute(f"SELECT COUNT(*) FROM {t}")
            count = c.fetchone()[0]
            print(f"\n--- {t}: {count} rows ---")
            # Find speaking questions
            c.execute(f"PRAGMA table_info({t})")
            cols = [r[1] for r in c.fetchall()]
            print(f"Columns: {cols}")
            if "question_type" in cols:
                c.execute(f"SELECT * FROM {t} WHERE question_type LIKE '%speak%' LIMIT 3")
                rows = c.fetchall()
                print(f"\nSpeaking questions sample:")
                for r in rows:
                    d = dict(r)
                    for k, v in d.items():
                        if isinstance(v, str) and len(v) > 200:
                            d[k] = v[:200] + "..."
                    print(d)
        except Exception as e:
            print(f"Error querying {t}: {e}")

conn.close()
