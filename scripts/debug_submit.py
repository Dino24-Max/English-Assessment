"""
Debug script: isolate POST /submit vs redirected GET.
Run with server running: python scripts/debug_submit.py
"""
import asyncio
import re
import sqlite3
import string
import secrets
from pathlib import Path
from datetime import datetime, timedelta

import httpx

BASE_URL = "http://127.0.0.1:8000"
PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH = PROJECT_ROOT / "data" / "assessment.db"


def create_invitation():
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DB_PATH}")
    alphabet = string.ascii_uppercase + string.digits
    code = "".join(secrets.choice(alphabet) for _ in range(16))
    email = f"debug-{secrets.token_hex(4)}@example.com"
    expires = (datetime.now() + timedelta(days=7)).isoformat()
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO invitation_codes (
            code, email, first_name, last_name, nationality,
            operation, department, created_by, expires_at,
            is_used, assessment_completed
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0)""",
        (code, email, "Debug", "User", "Philippines", "hotel", "HOUSEKEEPING", "admin", expires),
    )
    conn.commit()
    conn.close()
    return code, email


async def main():
    code, email = create_invitation()
    print(f"Invitation: code={code[:8]}..., email={email}")

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        # NO follow_redirects - we want to see exact responses
        r = await client.get(f"/register?code={code}")
        r.raise_for_status()

        r = await client.post("/api/v1/auth/register", json={
            "first_name": "Debug", "last_name": "User", "email": email,
            "nationality": "Philippines", "invitation_code": code,
        })
        r.raise_for_status()

        r = await client.get("/instructions?operation=HOTEL")
        r.raise_for_status()

        r = await client.get("/pre-test?operation=HOTEL")
        r.raise_for_status()

        r = await client.get("/question/1?operation=HOTEL")
        r.raise_for_status()
        html = r.text
        csrf_match = re.search(r'<meta name="csrf-token" content="([^"]*)"', html)
        csrf_token = csrf_match.group(1) if csrf_match else ""

        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        if csrf_token:
            headers["X-CSRF-Token"] = csrf_token

        # POST Q1 - do NOT follow redirects
        r = await client.post(
            "/submit",
            data={"question_num": 1, "answer": "A", "operation": "HOTEL", "time_spent": 10},
            headers=headers,
            follow_redirects=False,
        )
        print(f"\n=== POST /submit Q1 ===")
        print(f"Status: {r.status_code}")
        print(f"Headers: Location={r.headers.get('Location', 'N/A')}")
        print(f"Body (first 2000 chars):\n{r.text[:2000]}")

        if r.status_code == 500:
            print("\n>>> 500 on POST itself - error is in submit_answer handler")
            return

        if r.status_code in (302, 303) and "Location" in r.headers:
            next_url = r.headers["Location"]
            print(f"\n=== GET redirect {next_url} ===")
            r2 = await client.get(next_url)
            print(f"Status: {r2.status_code}")
            print(f"Body (full):\n{r2.text}")
            if r2.status_code == 500:
                print("\n>>> 500 on redirected GET - error is in question_page or that route")
                try:
                    js = r2.json()
                    print("\n--- Full JSON response ---")
                    for k, v in js.items():
                        print(f"\n{k}:\n{v}")
                    if "traceback" in js:
                        print("\n--- Traceback ---")
                        print(js["traceback"])
                except Exception as e:
                    print(f"Could not parse JSON: {e}")
                    print("Raw body:", r2.text[:2000])


if __name__ == "__main__":
    asyncio.run(main())
