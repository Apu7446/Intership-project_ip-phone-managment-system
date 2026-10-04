"""
SBAC IP Phone Management System — Database Setup & Initialization Tool
Creates 'sbac_ipphone' database, creates all required tables, indexes, and default admin user.
"""

import sys
from config import DB_CONFIG
import db


def reset_database():
    """Drop all tables if reset is requested."""
    db_name = DB_CONFIG.get('database', 'sbac_ipphone')
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute(f"USE `{db_name}`")
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
        cursor.execute("DROP TABLE IF EXISTS ip_phones")
        cursor.execute("DROP TABLE IF EXISTS departments")
        cursor.execute("DROP TABLE IF EXISTS users")
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
        conn.commit()
        cursor.close()
        conn.close()
        print("[*] Database tables reset successfully.")
    except Exception as e:
        print(f"[!] Reset warning: {e}")


def create_database_and_tables(reset_all=False):
    """Ensure database, tables, indexes exist and seed initial data."""
    if reset_all:
        reset_database()

    print("[*] Ensuring database and tables exist...")
    if not db.ensure_database():
        print("[ERROR] Database initialization failed!")
        return False

    print("[*] Ensuring database indexes are configured...")
    db.ensure_indexes()

    print("[*] Seeding CSV data files...")
    db.seed_official_locations()

    print("[OK] Database setup complete!")
    return True


if __name__ == '__main__':
    reset = "--reset" in sys.argv
    create_database_and_tables(reset_all=reset)

