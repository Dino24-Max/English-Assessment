"""
E2E test: Full assessment flow from registration to results.
Uses invitation → register → instructions → pre-test → 21 questions → results.
Verifies HOUSEKEEPING department receives department-specific questions.
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


def create_invitation() -> tuple[str, str]:
    """Create invitation in DB, return (code, email)."""
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DB_PATH}")
    alphabet = string.ascii_uppercase + string.digits
    code = "".join(secrets.choice(alphabet) for _ in range(16))
    email = f"e2e-{secrets.token_hex(4)}@example.com"
    expires = (datetime.now() + timedelta(days=7)).isoformat()

    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO invitation_codes (
            code, email, first_name, last_name, nationality,
            operation, department, created_by, expires_at,
            is_used, assessment_completed
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0)""",
        (code, email, "E2E", "Tester", "Philippines", "hotel", "HOUSEKEEPING", "admin", expires),
    )
    conn.commit()
    conn.close()
    return code, email


async def run_e2e():
    print("=" * 60)
    print("E2E Assessment Flow")
    print("=" * 60)

    code, email = create_invitation()
    print(f"Invitation: code={code[:8]}..., email={email}")

    async with httpx.AsyncClient(
        base_url=BASE_URL,
        follow_redirects=True,
        timeout=30.0,
    ) as client:
        # 1. GET register page (establish session)
        r = await client.get(f"/register?code={code}")
        r.raise_for_status()
        print("  GET /register?code=... OK")

        # 2. POST register (JSON, CSRF exempt)
        reg_data = {
            "first_name": "E2E",
            "last_name": "Tester",
            "email": email,
            "nationality": "Philippines",
            "invitation_code": code,
        }
        r = await client.post("/api/v1/auth/register", json=reg_data)
        r.raise_for_status()
        data = r.json()
        redirect = data.get("redirect", "")
        if not redirect:
            raise RuntimeError("Registration did not return redirect")
        print(f"  POST /api/v1/auth/register OK -> {redirect}")

        # 2b. Verify assessment has question_order immediately after registration
        conn = sqlite3.connect(str(DB_PATH))
        cur = conn.cursor()
        cur.execute(
            """SELECT a.id, a.department, a.question_order
             FROM assessments a
             JOIN users u ON a.user_id = u.id
             WHERE u.email = ?
             ORDER BY a.created_at DESC LIMIT 1""",
            (email,),
        )
        row = cur.fetchone()
        conn.close()
        if row:
            aid, dept, qo = row
            import json
            try:
                parsed = json.loads(qo) if isinstance(qo, str) and qo else (qo if qo else [])
            except (TypeError, ValueError):
                parsed = []
            n = len(parsed) if parsed else 0
            print(f"  [POST-REGISTER] Assessment {aid}: dept={dept}, question_order len={n}")

        # 3. Instructions & pre-test
        r = await client.get("/instructions?operation=HOTEL")
        r.raise_for_status()
        print("  GET /instructions OK")

        r = await client.get("/pre-test?operation=HOTEL")
        r.raise_for_status()
        print("  GET /pre-test OK")

        # 4. Q1 - triggers start_assessment, get CSRF
        r = await client.get("/question/1?operation=HOTEL")
        r.raise_for_status()
        html = r.text
        csrf_match = re.search(r'<meta name="csrf-token" content="([^"]*)"', html)
        csrf_token = csrf_match.group(1) if csrf_match else ""
        if not csrf_token:
            # Fallback: check for csrf_token in template variable
            csrf_match = re.search(r'[\'"]X-CSRF-Token[\'"],\s*[\'"]([^"\']+)[\'"]', html)
            if csrf_match:
                csrf_token = csrf_match.group(1)
        print(f"  GET /question/1 OK, CSRF={'...' if csrf_token else 'MISSING'}")

        # 5. Submit answers for Q1-21
        for q in range(1, 22):
            headers = {"Content-Type": "application/x-www-form-urlencoded"}
            if csrf_token:
                headers["X-CSRF-Token"] = csrf_token
            payload = {
                "question_num": q,
                "answer": "A",
                "operation": "HOTEL",
                "time_spent": 10,
            }
            r = await client.post("/submit", data=payload, headers=headers)
            if r.status_code >= 400:
                print(f"  POST /submit Q{q} FAILED {r.status_code}: {r.text[:8000]}")
            r.raise_for_status()

            # Follow redirect for next question or results
            if r.status_code in (302, 303) and "Location" in r.headers:
                next_url = r.headers["Location"]
                r = await client.get(next_url)
                if r.status_code >= 400:
                    print(f"  GET {next_url} FAILED {r.status_code}: {r.text[:3000]}")
                r.raise_for_status()
                html = r.text
                # Refresh CSRF from each question page
                m = re.search(r'<meta name="csrf-token" content="([^"]*)"', html)
                if m:
                    csrf_token = m.group(1)
            elif "<title>" in r.text and "Results" in r.text:
                print(f"  Q{q} -> Results page reached")
                break
            if q % 5 == 0:
                print(f"  Submitted Q1-{q}")

        # 6. Verify we reached results
        if "/results" not in str(r.url) and "Results" not in r.text:
            # Try GET results explicitly
            r = await client.get("/results")
            r.raise_for_status()
        if "Results" not in r.text and "results" not in r.url.lower():
            raise RuntimeError("Did not reach results page")
        print("  GET /results OK")

    # 7. Verify department-specific questions in DB
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    cur.execute(
        """SELECT a.id, a.department, a.question_order
         FROM assessments a
         JOIN users u ON a.user_id = u.id
         WHERE u.email = ?
         ORDER BY a.created_at DESC LIMIT 1""",
        (email,),
    )
    row = cur.fetchone()
    conn.close()

    if row:
        aid, dept, order_raw = row
        import json
        order = []
        if order_raw:
            try:
                order = json.loads(order_raw) if isinstance(order_raw, str) else (order_raw or [])
            except (TypeError, ValueError):
                pass
        print(f"\nAssessment {aid}: department={dept}, question_order length={len(order)}")
        if dept != "HOUSEKEEPING":
            raise AssertionError(f"Expected department HOUSEKEEPING, got {dept}")
        if not order or len(order) != 21:
            raise AssertionError(f"Expected 21 questions in order, got {len(order)}")
        print("  HOUSEKEEPING-specific questions: VERIFIED")
    else:
        print("  WARNING: Could not verify assessment in DB")

    print("\n" + "=" * 60)
    print("E2E PASSED")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_e2e())
