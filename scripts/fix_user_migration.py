#!/usr/bin/env python3
"""
Fix user migration - add missing szhang@carnival.com user
and update assessment user_id references
"""

import sqlite3
from pathlib import Path

source_db = Path(__file__).parent.parent / "src" / "main" / "python" / "english_assessment.db"
target_db = Path(__file__).parent.parent / "data" / "assessment.db"

source_conn = sqlite3.connect(str(source_db))
target_conn = sqlite3.connect(str(target_db))

source_cursor = source_conn.cursor()
target_cursor = target_conn.cursor()

print("=" * 70)
print("Fixing User Migration")
print("=" * 70)

try:
    # Get szhang@carnival.com from source
    source_cursor.execute("SELECT * FROM users WHERE email = ?", ('szhang@carnival.com',))
    source_user = source_cursor.fetchone()
    
    if not source_user:
        print("User szhang@carnival.com not found in source database")
        exit(1)
    
    # Check if already exists in target
    target_cursor.execute("SELECT id FROM users WHERE email = ?", ('szhang@carnival.com',))
    existing = target_cursor.fetchone()
    
    if existing:
        print(f"User szhang@carnival.com already exists with ID: {existing[0]}")
        new_user_id = existing[0]
    else:
        # Get column names
        source_cursor.execute("PRAGMA table_info(users)")
        columns = [col[1] for col in source_cursor.fetchall()]
        
        # Get next available ID
        target_cursor.execute("SELECT MAX(id) FROM users")
        max_id = target_cursor.fetchone()[0] or 0
        new_user_id = max_id + 1
        
        # Create new user record with new ID
        # Build INSERT statement excluding id (let it auto-increment or use new_id)
        id_idx = columns.index('id')
        columns_no_id = [c for c in columns if c != 'id']
        placeholders = ','.join(['?' for _ in columns_no_id])
        columns_str = ','.join(columns_no_id)
        
        # Get values excluding id
        values = list(source_user)
        values.pop(id_idx)
        
        # Insert with explicit ID
        columns_with_id = ['id'] + columns_no_id
        placeholders_with_id = '?,' + placeholders
        values_with_id = [new_user_id] + values
        
        target_cursor.execute(
            f"INSERT INTO users ({','.join(columns_with_id)}) VALUES ({placeholders_with_id})",
            values_with_id
        )
        print(f"Added user szhang@carnival.com with new ID: {new_user_id}")
    
    # Update assessment user_id references
    # Assessment ID 1 should belong to szhang@carnival.com (not admin)
    target_cursor.execute("SELECT id, user_id FROM assessments WHERE id = 1")
    assess_1 = target_cursor.fetchone()
    
    if assess_1 and assess_1[1] == 1:  # Currently points to admin (ID 1)
        target_cursor.execute("UPDATE assessments SET user_id = ? WHERE id = 1", (new_user_id,))
        print(f"Updated assessment ID 1 to point to user {new_user_id} (szhang@carnival.com)")
    
    # Assessment ID 10 also belongs to szhang@carnival.com
    target_cursor.execute("SELECT id, user_id FROM assessments WHERE id = 10")
    assess_10 = target_cursor.fetchone()
    
    if assess_10 and assess_10[1] == 1:  # Currently points to admin (ID 1)
        target_cursor.execute("UPDATE assessments SET user_id = ? WHERE id = 10", (new_user_id,))
        print(f"Updated assessment ID 10 to point to user {new_user_id} (szhang@carnival.com)")
    
    target_conn.commit()
    
    print("\n" + "=" * 70)
    print("Migration fix completed!")
    print("=" * 70)
    
    # Verify
    target_cursor.execute("SELECT id, email, first_name, last_name FROM users ORDER BY id")
    users = target_cursor.fetchall()
    print(f"\nUsers ({len(users)}):")
    for u in users:
        print(f"  ID: {u[0]}, Email: {u[1]}, Name: {u[2]} {u[3]}")
    
    target_cursor.execute("SELECT id, user_id, status, total_score FROM assessments ORDER BY id")
    assessments = target_cursor.fetchall()
    print(f"\nAssessments ({len(assessments)}):")
    for a in assessments:
        target_cursor.execute("SELECT email FROM users WHERE id = ?", (a[1],))
        user_result = target_cursor.fetchone()
        user_email = user_result[0] if user_result else "Unknown"
        print(f"  ID: {a[0]}, User: {a[1]} ({user_email}), Status: {a[2]}, Score: {a[3]}")

except Exception as e:
    target_conn.rollback()
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    source_conn.close()
    target_conn.close()

