#!/usr/bin/env python3
"""
Reset database to fresh state. Backs up current DB and removes it so app creates a new one on next start.
"""
import shutil
from pathlib import Path

project_root = Path(__file__).parent.parent
db_path = project_root / "data" / "assessment.db"
backup_path = project_root / "data" / "assessment_84users_backup.db"

if not db_path.exists():
    print(f"No database found at {db_path}. Nothing to reset.")
    exit(0)

print("=" * 60)
print("Resetting Database")
print("=" * 60)
print(f"Backing up: {db_path}")
print(f"         to: {backup_path}")
shutil.copy2(db_path, backup_path)
print("Backup created.")

db_path.unlink()
print("Original database removed.")
print()
print("Done. Next steps:")
print("  1. Restart the server: python run_server.py")
print("  2. Load question bank: POST http://127.0.0.1:8000/api/v1/admin/load-full-question-bank?admin_key=dev-admin-key-123")
print("  3. Create invitations: http://127.0.0.1:8000/admin/invitations")
print("=" * 60)
