"""
Diagnostic: Verify department-specific questions exist in the database.
Run this to confirm each department has enough questions for assessment generation.
"""
import sqlite3
from pathlib import Path

db_path = Path(__file__).parent.parent / "data" / "assessment.db"
conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

# Check if questions table has department column
cursor.execute("PRAGMA table_info(questions)")
cols = [r[1] for r in cursor.fetchall()]
if "department" not in cols:
    print("WARNING: questions table has no 'department' column")
    conn.close()
    exit(1)

# Count questions per department
cursor.execute("""
    SELECT department, division, COUNT(*) as cnt
    FROM questions
    GROUP BY department, division
    ORDER BY division, department
""")
rows = cursor.fetchall()

print("Department question counts in DB:")
print("-" * 60)
total = 0
dept_null = 0
by_division = {}
for dept, div, cnt in rows:
    total += cnt
    if dept is None or dept == "":
        dept_null += cnt
    else:
        by_division.setdefault(div or "NULL", {})[dept] = cnt

for div, depts in sorted(by_division.items()):
    print(f"\n{div} division:")
    for dept, cnt in sorted(depts.items()):
        status = "OK" if cnt >= 21 else "LOW"  # 21 questions needed per assessment
        print(f"  {dept}: {cnt}")

if dept_null:
    print(f"\nQuestions with NULL/empty department: {dept_null}")

print(f"\nTotal questions: {total}")
print("-" * 60)

# Per-module check for one sample department
cursor.execute("""
    SELECT department, module_type, COUNT(*) as cnt
    FROM questions
    WHERE department IS NOT NULL AND department != ''
    GROUP BY department, module_type
    LIMIT 50
""")
sample = cursor.fetchall()
if sample:
    print("\nSample (first department, per module):")
    for dept, mod, cnt in sample[:6]:
        print(f"  {dept} / {mod}: {cnt}")

conn.close()
