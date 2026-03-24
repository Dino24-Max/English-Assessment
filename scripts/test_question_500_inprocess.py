"""
In-process test to capture full traceback for GET /question/2 500 error.
Does not require a running server - runs app in-process.
"""
import asyncio
import re
import sqlite3
import string
import secrets
from pathlib import Path
from datetime import datetime, timedelta

# Add src to path
import sys
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src" / "main" / "python"))

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
    from httpx import ASGITransport, AsyncClient
    from main import app

    code, email = create_invitation()
    print(f"Invitation: code={code[:8]}..., email={email}")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", timeout=30.0) as client:
        r = await client.get(f"/register?code={code}")
        r.raise_for_status()

        r = await client.post("/api/v1/auth/register", json={
            "first_name": "Debug", "last_name": "User", "email": email,
            "nationality": "Philippines", "invitation_code": code,
        })
        r.raise_for_status()

        await client.get("/instructions?operation=HOTEL")
        await client.get("/pre-test?operation=HOTEL")

        r = await client.get("/question/1?operation=HOTEL")
        r.raise_for_status()
        html = r.text
        csrf_match = re.search(r'<meta name="csrf-token" content="([^"]*)"', html)
        csrf_token = csrf_match.group(1) if csrf_match else ""

        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        if csrf_token:
            headers["X-CSRF-Token"] = csrf_token

        r = await client.post(
            "/submit",
            data={"question_num": 1, "answer": "A", "operation": "HOTEL", "time_spent": 10},
            headers=headers,
            follow_redirects=False,
        )
        print(f"POST /submit Q1: {r.status_code} -> {r.headers.get('Location', 'N/A')}")

        if r.status_code in (302, 303) and "Location" in r.headers:
            next_url = r.headers["Location"]
            print(f"GET {next_url}")
            r2 = await client.get(next_url)
            print(f"Status: {r2.status_code}")
            # Avoid UnicodeEncodeError on Windows console (cp1252)
            body = r2.text[:2000].encode("ascii", errors="replace").decode("ascii")
            print(f"Body:\n{body}")
            if r2.status_code == 500:
                try:
                    js = r2.json()
                    if js.get("traceback"):
                        print("\n" + "=" * 60 + "\nTRACEBACK:\n" + "=" * 60)
                        print(js["traceback"])
                except Exception:
                    pass


if __name__ == "__main__":
    asyncio.run(main())
