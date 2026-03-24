"""Debug POST /submit 500 - print response body to see server error."""
import asyncio
import re
import secrets
import sqlite3
import string
from pathlib import Path
from datetime import datetime, timedelta

import httpx

ROOT = Path(__file__).parent.parent
DB_PATH = ROOT / "data" / "assessment.db"
BASE = "http://127.0.0.1:8000"


def create_invitation():
    alphabet = string.ascii_uppercase + string.digits
    code = "".join(secrets.choice(alphabet) for _ in range(16))
    email = f"debug-{secrets.token_hex(4)}@test.com"
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO invitation_codes (
            code, email, first_name, last_name, nationality,
            operation, department, created_by, expires_at,
            is_used, assessment_completed
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0)""",
        (code, email, "Debug", "User", "Philippines", "hotel", "HOUSEKEEPING", "admin",
         (datetime.now() + timedelta(days=7)).isoformat()),
    )
    conn.commit()
    conn.close()
    return code, email


async def main():
    code, email = create_invitation()
    async with httpx.AsyncClient(base_url=BASE, follow_redirects=False, timeout=30.0) as client:
        await client.get(f"/register?code={code}")
        await client.post("/api/v1/auth/register", json={
            "first_name": "Debug", "last_name": "User", "email": email,
            "nationality": "Philippines", "invitation_code": code,
        })
        await client.get("/instructions")
        r = await client.get("/pre-test")
        r = await client.get("/question/1")
        m = re.search(r'<meta name="csrf-token" content="([^"]*)"', r.text)
        csrf = m.group(1) if m else ""
        r = await client.post("/submit", data={
            "question_num": 1, "answer": "A", "operation": "HOTEL", "time_spent": 10
        }, headers={"Content-Type": "application/x-www-form-urlencoded", "X-CSRF-Token": csrf})
    print(f"Status: {r.status_code}")
    print(r.text[:5000])


if __name__ == "__main__":
    asyncio.run(main())
