"""Check BEVERAGE questions in DB - division and module coverage."""
import sqlite3
from pathlib import Path

db = Path(__file__).parent.parent / "data" / "assessment.db"
conn = sqlite3.connect(str(db))
c = conn.cursor()

c.execute("""
  SELECT division, department, module_type, COUNT(*) 
  FROM questions 
  WHERE department = 'BEVERAGE GUEST SERV'
  GROUP BY division, department, module_type
""")
print("BEVERAGE GUEST SERV by module:")
for r in c.fetchall():
    print(r)

c.execute("SELECT division, department, COUNT(*) FROM questions WHERE department IS NULL GROUP BY division, department")
print("\nNULL department (legacy/sample):")
for r in c.fetchall():
    print(r)

# What division does BEVERAGE have?
c.execute("SELECT DISTINCT division FROM questions WHERE department = 'BEVERAGE GUEST SERV'")
print("\nDivision(s) for BEVERAGE:", [r[0] for r in c.fetchall()])

conn.close()
