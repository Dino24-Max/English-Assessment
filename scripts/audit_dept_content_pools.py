"""One-off audit: department -> content pool coverage and samples. Run from repo root:
   python scripts/audit_dept_content_pools.py
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src" / "main" / "python"))

from config.departments import DEPARTMENT_TO_CONTENT_POOL  # noqa: E402

JSON_PATH = ROOT / "src" / "main" / "python" / "data" / "question_bank_full.json"


def main() -> None:
    rev: dict[str, list[str]] = defaultdict(list)
    for dept, key in DEPARTMENT_TO_CONTENT_POOL.items():
        rev[key].append(dept)

    print("=== Departments sharing the same content pool ===")
    for k in sorted(rev.keys()):
        depts = rev[k]
        if len(depts) > 1:
            print(f'  "{k}" <- {len(depts)} departments: {", ".join(depts)}')

    print("\n=== Grammar module note ===")
    print("  Grammar uses one universal pool for all departments (cruise-hospitality English).")
    print("  It is not job-role-specific in the generator.")

    if not JSON_PATH.exists():
        print(f"\n(JSON not found: {JSON_PATH})")
        return

    data = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    qs = data.get("questions", [])

    def sample(dept: str, mod: str):
        for q in qs:
            if q.get("department") == dept and (q.get("module_type") or "").lower() == mod:
                return q
        return None

    print("\n=== Listening audio prefix samples (by department) ===")
    for dept in [
        "DECK",
        "ENGINE",
        "SPA",
        "CULINARY ARTS",
        "REST. SERVICE",
        "HOTEL",
        "INFO TECHNOLOGY",
    ]:
        q = sample(dept, "listening")
        pool = DEPARTMENT_TO_CONTENT_POOL[dept]
        if not q:
            print(f"  {dept}: NO QUESTION FOUND")
            continue
        aud = (q.get("audio_text") or q.get("audio") or "").strip()[:160]
        print(f"  {dept}  [content_pool={pool}]")
        print(f"    {aud!r}")


if __name__ == "__main__":
    main()
