"""Check division/department values in questions table."""
import sqlite3
from pathlib import Path

db = Path(__file__).parent.parent / "data" / "assessment.db"
conn = sqlite3.connect(str(db))
c = conn.cursor()
c.execute("SELECT DISTINCT division FROM questions LIMIT 10")
print("Question divisions:", [r[0] for r in c.fetchall()])
c.execute("SELECT id, division, department FROM questions WHERE department = 'BEVERAGE GUEST SERV' LIMIT 2")
print("BEVERAGE sample:", c.fetchall())
c.execute("SELECT id, division, department FROM questions WHERE department = 'HOUSEKEEPING' LIMIT 2")
print("HOUSEKEEPING sample:", c.fetchall())
conn.close()
