#!/usr/bin/env python3
"""
Migrate data from english_assessment.db to assessment.db
Then cleanup assessments keeping only first and last two
"""

import sqlite3
import shutil
from pathlib import Path

source_db = Path(__file__).parent.parent / "src" / "main" / "python" / "english_assessment.db"
target_db = Path(__file__).parent.parent / "data" / "assessment.db"

if not source_db.exists():
    print(f"Source database not found: {source_db}")
    exit(1)

print("=" * 70)
print("Migrating and Cleaning Up Assessment Data")
print("=" * 70)

# Backup target database first
if target_db.exists():
    backup_path = target_db.parent / f"assessment_backup_{Path(target_db).stat().st_mtime}.db"
    shutil.copy2(target_db, backup_path)
    print(f"Backed up target database to: {backup_path}")

# Connect to both databases
source_conn = sqlite3.connect(str(source_db))
target_conn = sqlite3.connect(str(target_db))

source_cursor = source_conn.cursor()
target_cursor = target_conn.cursor()

try:
    # Step 1: Copy all users from source to target
    print("\nStep 1: Copying users...")
    source_cursor.execute("SELECT * FROM users")
    users = source_cursor.fetchall()
    
    # Get column names
    source_cursor.execute("PRAGMA table_info(users)")
    user_columns = [col[1] for col in source_cursor.fetchall()]
    placeholders = ','.join(['?' for _ in user_columns])
    columns = ','.join(user_columns)
    
    for user in users:
        # Check if user already exists by email
        email_idx = user_columns.index('email')
        target_cursor.execute("SELECT id FROM users WHERE email = ?", (user[email_idx],))
        existing = target_cursor.fetchone()
        
        if existing:
            print(f"  User {user[email_idx]} already exists (ID: {existing[0]}), skipping")
            continue
        
        # Use INSERT OR IGNORE to handle ID conflicts
        target_cursor.execute(f"INSERT OR IGNORE INTO users ({columns}) VALUES ({placeholders})", user)
    
    target_conn.commit()
    print(f"  Copied {len(users)} users")

    # Step 2: Get assessments from source, keep only first and last two
    print("\nStep 2: Copying assessments (keeping first and last two)...")
    source_cursor.execute("SELECT * FROM assessments ORDER BY id")
    assessments = source_cursor.fetchall()
    
    if len(assessments) == 0:
        print("  No assessments to copy")
    elif len(assessments) <= 3:
        print(f"  Only {len(assessments)} assessments, copying all")
        # Copy all
        source_cursor.execute("PRAGMA table_info(assessments)")
        assess_columns = [col[1] for col in source_cursor.fetchall()]
        placeholders = ','.join(['?' for _ in assess_columns])
        columns = ','.join(assess_columns)
        
        for assess in assessments:
            target_cursor.execute(f"INSERT INTO assessments ({columns}) VALUES ({placeholders})", assess)
    else:
        # Keep first and last two
        keep_assessments = [assessments[0], assessments[-2], assessments[-1]]
        print(f"  Keeping {len(keep_assessments)} assessments: IDs {assessments[0][0]}, {assessments[-2][0]}, {assessments[-1][0]}")
        
        source_cursor.execute("PRAGMA table_info(assessments)")
        assess_columns = [col[1] for col in source_cursor.fetchall()]
        placeholders = ','.join(['?' for _ in assess_columns])
        columns = ','.join(assess_columns)
        
        for assess in keep_assessments:
            target_cursor.execute(f"INSERT INTO assessments ({columns}) VALUES ({placeholders})", assess)
    
    target_conn.commit()
    print(f"  Copied {min(len(assessments), 3) if len(assessments) > 3 else len(assessments)} assessments")

    # Step 3: Copy assessment responses for kept assessments
    if len(assessments) > 0:
        print("\nStep 3: Copying assessment responses...")
        # Get ID column index
        source_cursor.execute("PRAGMA table_info(assessments)")
        assess_columns = [col[1] for col in source_cursor.fetchall()]
        id_idx = assess_columns.index('id')
        
        if len(assessments) <= 3:
            kept_ids = [a[id_idx] for a in assessments]
        else:
            kept_ids = [assessments[0][id_idx], assessments[-2][id_idx], assessments[-1][id_idx]]
        
        source_cursor.execute("PRAGMA table_info(assessment_responses)")
        response_columns = [col[1] for col in source_cursor.fetchall()]
        placeholders = ','.join(['?' for _ in response_columns])
        columns = ','.join(response_columns)
        
        response_count = 0
        for assess_id in kept_ids:
            source_cursor.execute(f"SELECT * FROM assessment_responses WHERE assessment_id = ?", (assess_id,))
            responses = source_cursor.fetchall()
            for resp in responses:
                target_cursor.execute(f"INSERT INTO assessment_responses ({columns}) VALUES ({placeholders})", resp)
                response_count += 1
        
        target_conn.commit()
        print(f"  Copied {response_count} assessment responses")

    # Step 4: Copy invitation codes
    print("\nStep 4: Copying invitation codes...")
    source_cursor.execute("SELECT * FROM invitation_codes")
    invitations = source_cursor.fetchall()
    
    if invitations:
        source_cursor.execute("PRAGMA table_info(invitation_codes)")
        inv_columns = [col[1] for col in source_cursor.fetchall()]
        placeholders = ','.join(['?' for _ in inv_columns])
        columns = ','.join(inv_columns)
        
        for inv in invitations:
            target_cursor.execute(f"INSERT OR IGNORE INTO invitation_codes ({columns}) VALUES ({placeholders})", inv)
        
        target_conn.commit()
        print(f"  Copied {len(invitations)} invitation codes")

    print("\n" + "=" * 70)
    print("Migration completed successfully!")
    print("=" * 70)
    
    # Verify
    target_cursor.execute("SELECT COUNT(*) FROM users")
    user_count = target_cursor.fetchone()[0]
    target_cursor.execute("SELECT COUNT(*) FROM assessments")
    assess_count = target_cursor.fetchone()[0]
    
    print(f"\nFinal counts in target database:")
    print(f"  Users: {user_count}")
    print(f"  Assessments: {assess_count}")

except Exception as e:
    target_conn.rollback()
    print(f"\nError: {e}")
    import traceback
    traceback.print_exc()
finally:
    source_conn.close()
    target_conn.close()

