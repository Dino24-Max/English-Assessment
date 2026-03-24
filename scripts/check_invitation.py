"""
Check invitation, user, and assessment for a given code.
Usage: python scripts/check_invitation.py 40H0MSXUUSW06RQU
"""
import sqlite3
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
db_path = project_root / "data" / "assessment.db"

if len(sys.argv) < 2:
    print("Usage: python scripts/check_invitation.py <invitation_code>")
    sys.exit(1)

code = sys.argv[1].strip().upper()

if not db_path.exists():
    print(f"Database not found: {db_path}")
    sys.exit(1)

conn = sqlite3.connect(str(db_path))
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Invitation (code is case-insensitive in app, try both)
cursor.execute(
    "SELECT * FROM invitation_codes WHERE UPPER(code) = UPPER(?)",
    (code,)
)
inv = cursor.fetchone()
if not inv:
    print(f"Invitation code '{code}' NOT FOUND in database.")
    conn.close()
    sys.exit(1)

print("=== INVITATION ===")
print(dict(inv))
print()

# User who used it
user_id = inv["used_by_user_id"]
if user_id:
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    if user:
        print("=== USER (used this invitation) ===")
        print(dict(user))
        print()
else:
    print("Invitation not yet used (no user_id).")
    print()

# Assessments for this user
if user_id:
    cursor.execute(
        "SELECT * FROM assessments WHERE user_id = ? ORDER BY id DESC LIMIT 5",
        (user_id,)
    )
    assessments = cursor.fetchall()
    print(f"=== ASSESSMENTS (user_id={user_id}, last 5) ===")
    for a in assessments:
        print(dict(a))
        print()

    # Questions in the most recent assessment's question_order
    if assessments:
        a = assessments[0]
        q_order = a["question_order"]
        if q_order:
            import json
            try:
                ids = json.loads(q_order) if isinstance(q_order, str) else q_order
                if ids:
                    placeholders = ",".join("?" * len(ids))
                    cursor.execute(
                        f"SELECT id, module_type, question_text, department FROM questions WHERE id IN ({placeholders})",
                        ids
                    )
                    qs = cursor.fetchall()
                    print("=== SAMPLE QUESTIONS IN ASSESSMENT ===")
                    for q in qs[:5]:
                        print(f"  id={q['id']} module={q['module_type']} dept={q['department']} text={str(q['question_text'])[:60]}...")
                    depts = set(q["department"] for q in qs)
                    print(f"\n  Departments in this assessment: {depts}")
            except Exception as e:
                print(f"Could not parse question_order: {e}")

conn.close()
