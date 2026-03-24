"""Check question bank contents. Run with --fix to migrate division to lowercase."""
import sqlite3
import sys

conn = sqlite3.connect("data/assessment.db")
cur = conn.cursor()

cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
print("Tables:", cur.fetchall())

cur.execute("PRAGMA table_info(questions)")
print("Questions schema:", cur.fetchall())

cur.execute("SELECT COUNT(*) FROM questions")
print("Total questions:", cur.fetchone())

cur.execute("SELECT DISTINCT division FROM questions")
print("Divisions:", cur.fetchall())

cur.execute("SELECT DISTINCT department FROM questions")
print("Departments:", cur.fetchall())

cur.execute("SELECT id, module_type, division, department FROM questions LIMIT 5")
print("Sample rows:", cur.fetchall())

cur.execute("SELECT COUNT(*) FROM questions WHERE division = 'hotel' AND department = 'HOUSEKEEPING'")
print("hotel+HOUSEKEEPING count:", cur.fetchone())

cur.execute("SELECT COUNT(*) FROM questions WHERE division = 'HOTEL' AND department = 'HOUSEKEEPING'")
print("HOTEL+HOUSEKEEPING count:", cur.fetchone())

cur.execute("SELECT COUNT(*) FROM questions WHERE department = 'HOUSEKEEPING'")
print("HOUSEKEEPING (any division):", cur.fetchone())

cur.execute("SELECT module_type, COUNT(*) FROM questions WHERE division = 'hotel' AND department = 'HOUSEKEEPING' GROUP BY module_type")
print("HOUSEKEEPING by module:", cur.fetchall())

MODULE_MAP = {
    "GRAMMAR": "grammar",
    "LISTENING": "listening",
    "READING": "reading",
    "SPEAKING": "speaking",
    "TIME_NUMBERS": "time_numbers",
    "VOCABULARY": "vocabulary",
}

QUESTION_TYPE_MAP = {
    "MULTIPLE_CHOICE": "multiple_choice",
    "FILL_BLANK": "fill_blank",
    "CATEGORY_MATCH": "category_match",
    "TITLE_SELECTION": "title_selection",
    "SPEAKING_RESPONSE": "speaking_response",
}

if "--fix" in sys.argv:
    cur.execute("UPDATE questions SET division = LOWER(division) WHERE division IN ('HOTEL', 'MARINE', 'CASINO')")
    print("Fixed divisions, rows updated:", cur.rowcount)
    for old, new in MODULE_MAP.items():
        cur.execute("UPDATE questions SET module_type = ? WHERE module_type = ?", (new, old))
        if cur.rowcount:
            print(f"  module_type {old} -> {new}: {cur.rowcount} rows")
    for old, new in QUESTION_TYPE_MAP.items():
        cur.execute("UPDATE questions SET question_type = ? WHERE question_type = ?", (new, old))
        if cur.rowcount:
            print(f"  question_type {old} -> {new}: {cur.rowcount} rows")
    conn.commit()
    cur.execute("SELECT DISTINCT division FROM questions")
    print("Divisions after fix:", cur.fetchall())
    cur.execute("SELECT DISTINCT module_type FROM questions")
    print("Module types after fix:", cur.fetchall())

    # invitation_codes.operation: HOTEL/MARINE/CASINO -> hotel/marine/casino
    op_map = {"HOTEL": "hotel", "MARINE": "marine", "CASINO": "casino"}
    for old, new in op_map.items():
        cur.execute("UPDATE invitation_codes SET operation = ? WHERE operation = ?", (new, old))
        if cur.rowcount:
            print(f"  invitation_codes.operation {old} -> {new}: {cur.rowcount} rows")
    conn.commit()

conn.close()
