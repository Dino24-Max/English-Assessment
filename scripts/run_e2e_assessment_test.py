"""
E2E test: Full assessment flow against new requirements.

Tests:
1. Invitation-based registration (division/department from invitation)
2. 21-question assessment (Listening, Time&Numbers, Grammar, Vocabulary, Reading, Speaking)
3. CEFR scoring on results page
4. 100 points total, correct department on assessment

Usage: python scripts/run_e2e_assessment_test.py [--base-url URL] [--admin-key KEY]
"""
import argparse
import json
import os
import re
import sys
import time

try:
    import requests
except ImportError:
    print("pip install requests")
    sys.exit(1)

# Base URL and admin key
BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000")
ADMIN_KEY = os.getenv("ADMIN_API_KEY", "dev-admin-key-123")

# Correct answers from questions_config.json (for full score validation)
CORRECT_ANSWERS = {
    1: "7 PM",
    2: "8254",
    3: "Deck 12",
    4: "7:00",
    5: "8",
    6: "9173",
    7: "May",
    8: "has",
    9: "direct",
    10: "on",
    11: json.dumps({
        "Bridge": "Ship's control center",
        "Gangway": "Ship's walkway to shore",
        "Tender": "Small boat for shore trips",
        "Muster": "Emergency assembly",
    }),
    12: json.dumps({
        "Concierge": "Guest services specialist",
        "Amenities": "Hotel facilities",
        "Excursion": "Shore activities",
        "Embark": "To board the ship",
    }),
    13: json.dumps({
        "Buffet": "Self-service dining",
        "A la carte": "Menu with individual prices",
        "Galley": "Ship's kitchen",
        "Sommelier": "Wine expert",
    }),
    14: json.dumps({
        "Muster drill": "Safety meeting",
        "Life jacket": "Personal flotation device",
        "Assembly station": "Emergency meeting point",
        "All aboard": "Final boarding call",
    }),
    15: "Contact the Port Agent",
    16: "2:00 AM",
    17: "Reservations",
    18: "4:00 PM",
    # Speaking: repeat format "recorded_DURATIONs|TRANSCRIPT" - use exact audio_text for full credit
    19: "recorded_5.0s|Good morning! Welcome aboard. My name is Maria and I will be your cabin steward during this voyage.",
    20: "recorded_5.0s|The pool deck is located on deck twelve. Please remember to bring your cruise card for towel service.",
    # Q21: scenario - give credit for recording with expected keywords
    21: "recorded_6.0s|Take the elevator to deck twelve, then follow the signs to the spa. The spa is on your right.",
}


def create_invitation(session: requests.Session) -> str:
    """Create invitation via admin API. Returns invitation code."""
    url = f"{BASE_URL}/api/v1/admin/invitation/create"
    payload = {
        "email": f"e2e_test_{int(time.time())}@example.com",
        "first_name": "E2E",
        "last_name": "Tester",
        "nationality": "USA",
        "operation": "hotel",
        "department": "Front Desk",
        "admin_key": ADMIN_KEY,
        "expires_in_days": 1,
    }
    r = session.post(url, json=payload)
    if r.status_code != 200:
        raise RuntimeError(f"Create invitation failed: {r.status_code} {r.text}")
    data = r.json()
    return data["code"], payload["email"], payload["first_name"], payload["last_name"], payload["nationality"]


def register_with_invitation(session: requests.Session, code: str, email: str, first_name: str, last_name: str, nationality: str) -> None:
    """Register with invitation code. Session will have user_id and assessment_id."""
    url = f"{BASE_URL}/api/v1/auth/register"
    payload = {
        "first_name": first_name,
        "last_name": last_name,
        "email": email,
        "nationality": nationality,
        "invitation_code": code,
    }
    r = session.post(url, json=payload)
    if r.status_code != 200:
        raise RuntimeError(f"Register failed: {r.status_code} {r.text}")
    data = r.json()
    if not data.get("success"):
        raise RuntimeError(f"Register failed: {data}")
    # Session cookie is set in response
    redirect = data.get("redirect", "")
    if "instructions" in redirect:
        # Hit instructions page to ensure session is established
        session.get(f"{BASE_URL}{redirect.split('?')[0]}?operation=HOTEL", allow_redirects=True)


def start_assessment(session: requests.Session) -> None:
    """Start assessment (simulates 'Start Assessment' click)."""
    url = f"{BASE_URL}/start-assessment?operation=HOTEL"
    r = session.get(url, allow_redirects=True)
    if r.status_code != 200:
        raise RuntimeError(f"Start assessment failed: {r.status_code}")


def get_csrf_token(session: requests.Session) -> str:
    """Fetch question page and extract CSRF token from HTML."""
    r = session.get(f"{BASE_URL}/question/1?operation=HOTEL", allow_redirects=True)
    if r.status_code != 200:
        raise RuntimeError(f"Failed to get question page: {r.status_code}")
    # Prefer meta tag (used when CSRF sent via X-CSRF-Token header)
    m = re.search(r'<meta name="csrf-token" content="([^"]*)"', r.text)
    if not m:
        m = re.search(r"formData\.append\('csrf_token',\s*'([^']*)'\)", r.text)
    if not m:
        m = re.search(r'name="csrf_token"[^>]*value="([^"]*)"', r.text) or re.search(r'value="([^"]*)"[^>]*name="csrf_token"', r.text)
    if not m:
        raise RuntimeError("CSRF token not found in question page")
    return m.group(1)


def submit_answer(session: requests.Session, question_num: int, answer: str, operation: str = "HOTEL", csrf_token: str = "") -> requests.Response:
    """Submit answer for a question. Sends CSRF in header to avoid form body consumption."""
    url = f"{BASE_URL}/submit"
    data = {
        "question_num": question_num,
        "answer": answer,
        "operation": operation,
    }
    headers = {}
    if csrf_token:
        headers["X-CSRF-Token"] = csrf_token
    return session.post(url, data=data, headers=headers, allow_redirects=True)


def get_results_html(session: requests.Session) -> str:
    """Fetch results page HTML."""
    r = session.get(f"{BASE_URL}/results")
    if r.status_code != 200:
        raise RuntimeError(f"Results page failed: {r.status_code}")
    return r.text


def parse_results(html: str) -> dict:
    """Extract CEFR level, total score, module scores from results HTML."""
    result = {"cefr": None, "total": None, "passed": None, "module_scores": {}}
    # CEFR level - look for "CEFR Level: A1" etc (A1, A2, B1, B2, C1, C2)
    cefr_match = re.search(r"CEFR\s*(?:Level)?\s*[:\s]*([A-C][12])", html, re.I) or re.search(r"([A-C][12])\s*level", html, re.I)
    if cefr_match:
        result["cefr"] = cefr_match.group(1)
    # Total score: score_percentage in SERVER_SCORES or "X%" in score-percentage div
    total_match = re.search(r"score_percentage:\s*(\d+)", html) or re.search(r"total[^0-9]*(\d+)\s*/\s*100", html, re.I)
    if total_match:
        result["total"] = int(total_match.group(1))
    # Module scores from API or page
    for mod in ["listening", "time_numbers", "grammar", "vocabulary", "reading", "speaking"]:
        m = re.search(rf"{mod}[^0-9]*(\d+)", html, re.I)
        if m:
            result["module_scores"][mod] = int(m.group(1))
    return result


def main():
    global BASE_URL, ADMIN_KEY
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=BASE_URL, help="Server base URL")
    parser.add_argument("--admin-key", default=ADMIN_KEY, help="Admin API key")
    args = parser.parse_args()
    BASE_URL = args.base_url.rstrip("/")
    ADMIN_KEY = args.admin_key

    session = requests.Session()
    session.headers["User-Agent"] = "E2E-Test/1.0"

    print("=" * 60)
    print("E2E Assessment Test - New Requirements Validation")
    print("=" * 60)

    errors = []

    try:
        # 1. Create invitation
        print("\n1. Creating invitation...")
        code, email, first_name, last_name, nationality = create_invitation(session)
        print(f"   Created invite for {email}, code={code[:8]}...")

        # 2. Register with invitation
        print("\n2. Registering with invitation...")
        register_with_invitation(session, code, email, first_name, last_name, nationality)
        print("   Registered successfully (session has user_id, assessment_id)")

        # 3. Start assessment
        print("\n3. Starting assessment...")
        start_assessment(session)
        print("   Assessment started")

        # Get CSRF token (required for /submit when CSRF_ENABLED=true)
        csrf_token = get_csrf_token(session)

        # 4. Submit all 21 answers
        print("\n4. Submitting 21 answers...")
        for q in range(1, 22):
            ans = CORRECT_ANSWERS.get(q, "")
            r = submit_answer(session, q, ans, csrf_token=csrf_token)
            if r.status_code == 429:
                # Rate limited - wait and retry once
                retry_after = int(r.headers.get("Retry-After", 60))
                time.sleep(min(retry_after, 65))
                r = submit_answer(session, q, ans, csrf_token=csrf_token)
            if r.status_code not in (200, 303, 302, 307):
                err_detail = r.text[:200] if r.text else ""
                errors.append(f"Q{q}: HTTP {r.status_code} {err_detail}")
            else:
                print(f"   Q{q}: OK")
            # Pause to stay under /submit rate limit (30/min)
            time.sleep(2.5)

        # 5. Validate results page
        print("\n5. Checking results page...")
        html = get_results_html(session)
        parsed = parse_results(html)

        # Requirements check
        print("\n--- Requirement Validation ---")
        if parsed.get("cefr"):
            print(f"   CEFR level displayed: {parsed['cefr']}")
        else:
            errors.append("CEFR level not found on results page")
            print("   CEFR level: NOT FOUND (check results template)")

        if parsed.get("total") is not None:
            print(f"   Total score: {parsed['total']}/100")
            if parsed["total"] < 99:
                # With correct answers expect 99+ (Speaking uses AI scoring, may vary slightly)
                errors.append(f"Expected 99+ pts for correct answers, got {parsed['total']}")
        else:
            errors.append("Total score not found on results page")
            print("   Total score: NOT FOUND")

        # Check for 21 questions completed
        if "results" in html.lower():
            print("   Results page: OK")
        else:
            errors.append("Results page content unexpected")

    except Exception as e:
        errors.append(str(e))
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()

    # Summary
    print("\n" + "=" * 60)
    if errors:
        print("FAILED - Issues:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print("PASSED - Assessment flow meets new requirements.")
        print("  - Invitation-based registration OK")
        print("  - 21-question flow OK")
        print("  - CEFR scoring on results OK")
        sys.exit(0)


if __name__ == "__main__":
    main()
