"""
Diagnose question bank state: check if department-specific questions exist.
Run from project root: python scripts/check_question_bank.py
"""
import sqlite3
from pathlib import Path

project_root = Path(__file__).parent.parent
db_path = project_root / "data" / "assessment.db"

if not db_path.exists():
    print(f"Database not found: {db_path}")
    exit(1)

conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

# Total questions
cursor.execute("SELECT COUNT(*) FROM questions")
total = cursor.fetchone()[0]
print(f"Total questions in DB: {total}")

# Questions by department
cursor.execute("""
    SELECT department, COUNT(*) as cnt 
    FROM questions 
    GROUP BY department 
    ORDER BY cnt DESC
""")
rows = cursor.fetchall()
print("\nQuestions by department:")
for dept, cnt in rows:
    label = dept if dept else "(NULL - legacy/sample)"
    print(f"  {label}: {cnt}")

# Check BEVERAGE GUEST SERV specifically
cursor.execute(
    "SELECT COUNT(*) FROM questions WHERE department = 'BEVERAGE GUEST SERV'"
)
bev_count = cursor.fetchone()[0]
print(f"\nBEVERAGE GUEST SERV questions: {bev_count}")

if bev_count == 0 and total > 0:
    print("\n*** DIAGNOSIS: No department-specific questions loaded! ***")
    print("You must load the full question bank before department filtering works:")
    print("  1. API: POST http://127.0.0.1:8000/api/v1/admin/load-full-question-bank?admin_key=YOUR_ADMIN_KEY")
    print("  2. Or run: python scripts/load_question_bank.py")
elif total == 0:
    print("\n*** DIAGNOSIS: Database has no questions! ***")
    print("Load the question bank: python scripts/load_question_bank.py")
else:
    print("\nOK: Department-specific questions are loaded.")

conn.close()
