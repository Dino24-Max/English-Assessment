"""
Create invitation directly in DB (bypasses API / admin key).
Usage: python scripts/create_invitation_direct.py
"""
import sqlite3
import secrets
import string
from pathlib import Path
from datetime import datetime, timedelta

project_root = Path(__file__).parent.parent
db_path = project_root / "data" / "assessment.db"

def generate_code(length=16):
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))

if not db_path.exists():
    print(f"Database not found: {db_path}")
    exit(1)

conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

# Ensure unique code
while True:
    code = generate_code(16)
    cursor.execute("SELECT 1 FROM invitation_codes WHERE code = ?", (code,))
    if cursor.fetchone() is None:
        break

expires_at = (datetime.now() + timedelta(days=7)).isoformat()

cursor.execute(
    """INSERT INTO invitation_codes (
        code, email, first_name, last_name, nationality,
        operation, department, created_by, expires_at,
        is_used, assessment_completed
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0)""",
    (
        code,
        "test-housekeeping@example.com",
        "Test",
        "Housekeeping",
        "Philippines",
        "HOTEL",
        "HOUSEKEEPING",
        "admin",
        expires_at,
    ),
)
conn.commit()
conn.close()

link = f"http://127.0.0.1:8000/register?code={code}"
print(f"Invitation created: {link}")
