"""
Check database file existence and basic stats (e.g. invitation code count).
"""
import sqlite3
from pathlib import Path

p = Path(__file__).parent.parent / "data" / "assessment.db"
print(f'Exists: {p.exists()}')
print(f'Abs path: {p.resolve()}')
if p.exists():
    print(f'Size: {p.stat().st_size} bytes')
else:
    print('File does not exist')
    exit(1)

conn = sqlite3.connect(str(p))
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM invitation_codes')
print(f'Invitation codes in DB: {cursor.fetchone()[0]}')
conn.close()
