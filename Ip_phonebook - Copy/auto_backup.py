"""
SBAC IP Phone Management System — Automated Scheduled Backup Worker
Executed silently by Windows Task Scheduler or background batch.
"""

import sys
import os

# Set cwd to script dir
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

from backup_manager import create_backup

if __name__ == "__main__":
    success, msg = create_backup(tag="scheduled")
    if success:
        print(f"[{success}] Backup created: {msg}")
        sys.exit(0)
    else:
        print(f"[{success}] Backup error: {msg}", file=sys.stderr)
        sys.exit(1)
