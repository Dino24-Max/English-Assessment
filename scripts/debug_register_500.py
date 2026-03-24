"""
Debug script: Reproduce 500 on GET /register and capture error details.
Run with server already running: python scripts/debug_register_500.py
"""
import sqlite3
import string
import secrets
from pathlib import Path
from datetime import datetime, timedelta

import httpx

BASE_URL = "http://127.0.0.1:8000"
PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH = PROJECT_ROOT / "data" / "assessment.db"


def create_invitation() -> str:
    """Create invitation in DB, return code."""
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DB_PATH}")
    alphabet = string.ascii_uppercase + string.digits
    code = "".join(secrets.choice(alphabet) for _ in range(16))
    expires = (datetime.now() + timedelta(days=7)).isoformat()

    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO invitation_codes (
            code, email, first_name, last_name, nationality,
            operation, department, created_by, expires_at,
            is_used, assessment_completed
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0)""",
        ("debug-" + code[:8], "debug@example.com", "Debug", "User", "Philippines", "hotel", "HOUSEKEEPING", "admin", expires),
    )
    conn.commit()
    conn.close()
    return "debug-" + code[:8]


def main():
    code = create_invitation()
    print(f"Created invitation: {code}")

    r = httpx.get(
        f"{BASE_URL}/register",
        params={"code": code},
        follow_redirects=True,
        timeout=10.0,
    )
    print(f"Status: {r.status_code}")
    print(f"Headers: {dict(r.headers)}")
    body = r.text
    if len(body) > 1000:
        print(f"Body (first 1000 chars): {body[:1000]}...")
    else:
        print(f"Body: {body}")

    if r.status_code == 500:
        # Try to parse JSON for detail
        try:
            j = r.json()
            print(f"JSON detail: {j}")
        except Exception:
            pass


if __name__ == "__main__":
    main()
