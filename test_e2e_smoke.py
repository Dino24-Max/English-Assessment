"""End-to-end smoke test for the running Cruise Assessment server.

Uses requests.Session to persist cookies (session + CSRF).
The app uses session-based auth and CSRF tokens stored in the session.
A GET request seeds the CSRF token; we then read it from the session
cookie or debug endpoint and include it in X-CSRF-Token for POSTs.
"""
import requests, json, sys

BASE = "http://127.0.0.1:8000"
s = requests.Session()

def p(label, r):
    print(f"\n{'='*60}")
    print(f"{label}  ->  HTTP {r.status_code}")
    try:
        print(json.dumps(r.json(), indent=2, default=str)[:2000])
    except Exception:
        print(r.text[:500])

results = {}

# 1. Health — also seeds the session with a CSRF token via GET
r = s.get(f"{BASE}/health")
p("GET /health", r)
results["health"] = r.status_code == 200

# 2. API root
r = s.get(f"{BASE}/api")
p("GET /api", r)
results["api_root"] = r.status_code == 200

# 3. Read the CSRF token from the debug/session endpoint
r = s.get(f"{BASE}/debug/session")
p("GET /debug/session (pre-login)", r)
csrf_token = None
if r.status_code == 200:
    csrf_token = r.json().get("csrf_token")
    print(f"  csrf_token from session: {csrf_token}")

if not csrf_token:
    csrf_cookie = s.cookies.get("csrf_token")
    if csrf_cookie:
        csrf_token = csrf_cookie
        print(f"  csrf_token from cookie: {csrf_token}")

# 4. Login (exempt from CSRF by EXEMPT_PATHS)
r = s.post(f"{BASE}/api/v1/auth/login",
           json={"email": "admin@carnival.com", "password": "admin123"})
p("POST /api/v1/auth/login", r)
results["login"] = r.status_code == 200 and r.json().get("success")

# Re-read session after login to get any updated CSRF token
r = s.get(f"{BASE}/debug/session")
p("GET /debug/session (post-login)", r)
if r.status_code == 200:
    body = r.json()
    t = body.get("csrf_token")
    if t:
        csrf_token = t
        print(f"  Updated csrf_token: {csrf_token}")
    print(f"  authenticated: {body.get('authenticated')}")
    print(f"  user_id:       {body.get('user_id')}")

csrf_headers = {"X-CSRF-Token": csrf_token} if csrf_token else {}

# 5. Assessment create (needs CSRF) — user_id & division are query params
r = s.post(f"{BASE}/api/v1/assessment/create",
           params={"user_id": 1, "division": "HOTEL", "department": "Front Desk"},
           headers=csrf_headers)
p("POST /api/v1/assessment/create", r)
results["assessment_create"] = r.status_code in (200, 201)

assessment_id = None
if results["assessment_create"]:
    data = r.json()
    assessment_id = data.get("assessment_id") or data.get("id")
    print(f"  assessment_id: {assessment_id}")

# 6. Start assessment
if assessment_id:
    r = s.post(f"{BASE}/api/v1/assessment/{assessment_id}/start",
               headers=csrf_headers)
    p(f"POST /api/v1/assessment/{assessment_id}/start", r)
    results["assessment_start"] = r.status_code == 200
    if r.status_code == 200:
        body = r.json()
        questions = body.get("questions", [])
        modules = sorted(set(q.get("module_type", "?") for q in questions))
        print(f"\n  Questions drawn: {len(questions)}")
        print(f"  Modules:         {modules}")
else:
    results["assessment_start"] = False
    print("\n*** Skipped start — no assessment_id ***")

# 7. Status check (GET — no CSRF needed)
if assessment_id:
    r = s.get(f"{BASE}/api/v1/assessment/{assessment_id}/status")
    p(f"GET /api/v1/assessment/{assessment_id}/status", r)
    results["assessment_status"] = r.status_code == 200

# Summary
print("\n" + "="*60)
print("SMOKE TEST SUMMARY")
print("="*60)
all_pass = True
for k, v in results.items():
    icon = "PASS" if v else "FAIL"
    if not v:
        all_pass = False
    print(f"  {k:25s} : {icon}")
print("="*60)
if all_pass:
    print("RESULT: ALL CHECKS PASSED")
else:
    print("RESULT: SOME CHECKS FAILED - see details above")
    sys.exit(1)
