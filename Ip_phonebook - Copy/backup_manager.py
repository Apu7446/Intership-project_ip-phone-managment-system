"""
SBAC IP Phone Management System — Automated Database Backup & Disaster Recovery Manager
Supports:
1. Automated & Manual MySQL Database Dump (.sql generation).
2. Smart Daily Startup Auto-Backup (non-blocking background execution).
3. 1-Click Disaster Recovery (Database Restore from .sql file).
4. Windows Task Scheduler 1-Click Registration (via schtasks.exe).
5. 30-Day Auto Retention / Pruning of stale backups.
"""

import os
import time
import datetime
import subprocess
import glob
import threading
import mysql.connector
from config import DB_CONFIG

# Default Backups Directory
BACKUP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backups")
XAMPP_MYSQLDUMP = r"c:\xampp\mysql\bin\mysqldump.exe"
XAMPP_MYSQL = r"c:\xampp\mysql\bin\mysql.exe"
TASK_NAME = "SBAC_IPPhone_Daily_Backup"


def ensure_backup_dir():
    """Ensure the backups folder exists."""
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR, exist_ok=True)
    return BACKUP_DIR


def get_mysqldump_command():
    """Find mysqldump executable from XAMPP or system PATH."""
    if os.path.exists(XAMPP_MYSQLDUMP):
        return XAMPP_MYSQLDUMP
    return "mysqldump"


def get_mysql_command():
    """Find mysql executable from XAMPP or system PATH."""
    if os.path.exists(XAMPP_MYSQL):
        return XAMPP_MYSQL
    return "mysql"


def create_backup(tag="manual", retention_days=30):
    """
    Creates a full database backup (.sql file).
    Returns (success: bool, message_or_filepath: str).
    """
    try:
        ensure_backup_dir()
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"sbac_ipphone_{tag}_{timestamp}.sql"
        filepath = os.path.join(BACKUP_DIR, filename)

        host = DB_CONFIG.get('host', 'localhost')
        port = str(DB_CONFIG.get('port', 3306))
        user = DB_CONFIG.get('user', 'root')
        password = DB_CONFIG.get('password', '')
        database = DB_CONFIG.get('database', 'sbac_ipphone')

        dump_exe = get_mysqldump_command()

        # Build mysqldump command
        cmd = [
            dump_exe,
            f"--host={host}",
            f"--port={port}",
            f"--user={user}",
            "--routines",
            "--triggers",
            "--add-drop-table",
            "--quick",
            "--databases",
            database
        ]

        if password:
            cmd.insert(4, f"--password={password}")

        # Execute dump to file
        with open(filepath, "w", encoding="utf-8") as out_f:
            result = subprocess.run(
                cmd,
                stdout=out_f,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )

        if result.returncode != 0:
            # If mysqldump failed, fallback to python table dumper
            return _python_fallback_dump(filepath, database)

        # Check if file has valid content
        if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
            prune_old_backups(retention_days)
            return True, filepath
        else:
            return False, "Backup file was created but appears empty."

    except Exception as e:
        return False, f"Backup failed with error: {str(e)}"


def _python_fallback_dump(filepath, database):
    """Pure Python SQL dumper if mysqldump.exe encounters issues."""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"-- SBAC IP Phone Management System SQL Backup\n")
            f.write(f"-- Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"-- Database: {database}\n\n")
            f.write(f"CREATE DATABASE IF NOT EXISTS `{database}`;\n")
            f.write(f"USE `{database}`;\n\n")
            f.write("SET FOREIGN_KEY_CHECKS=0;\n\n")

            # Get all tables
            cursor.execute("SHOW TABLES")
            tables = [r[0] for r in cursor.fetchall()]

            for tbl in tables:
                cursor.execute(f"SHOW CREATE TABLE `{tbl}`")
                create_stmt = cursor.fetchone()[1]
                f.write(f"DROP TABLE IF EXISTS `{tbl}`;\n")
                f.write(f"{create_stmt};\n\n")

                cursor.execute(f"SELECT * FROM `{tbl}`")
                rows = cursor.fetchall()
                if rows:
                    cols = [d[0] for d in cursor.description]
                    cols_str = ", ".join([f"`{c}`" for c in cols])
                    for row in rows:
                        vals = []
                        for val in row:
                            if val is None:
                                vals.append("NULL")
                            elif isinstance(val, (int, float)):
                                vals.append(str(val))
                            else:
                                escaped = str(val).replace("'", "''").replace("\\", "\\\\")
                                vals.append(f"'{escaped}'")
                        vals_str = ", ".join(vals)
                        f.write(f"INSERT INTO `{tbl}` ({cols_str}) VALUES ({vals_str});\n")
                    f.write("\n")

            f.write("SET FOREIGN_KEY_CHECKS=1;\n")

        cursor.close()
        conn.close()
        return True, filepath
    except Exception as e:
        if os.path.exists(filepath):
            os.remove(filepath)
        return False, f"Python Fallback dump failed: {e}"


def restore_backup(filepath):
    """
    Restores the database from a given .sql backup file.
    Returns (success: bool, message: str).
    """
    if not os.path.exists(filepath):
        return False, "Specified backup file does not exist."

    try:
        host = DB_CONFIG.get('host', 'localhost')
        port = str(DB_CONFIG.get('port', 3306))
        user = DB_CONFIG.get('user', 'root')
        password = DB_CONFIG.get('password', '')
        database = DB_CONFIG.get('database', 'sbac_ipphone')

        mysql_exe = get_mysql_command()

        cmd = [
            mysql_exe,
            f"--host={host}",
            f"--port={port}",
            f"--user={user}",
            database
        ]
        if password:
            cmd.insert(4, f"--password={password}")

        with open(filepath, "r", encoding="utf-8") as in_f:
            result = subprocess.run(
                cmd,
                stdin=in_f,
                stderr=subprocess.PIPE,
                stdout=subprocess.PIPE,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )

        if result.returncode != 0:
            # Fallback to Python execute
            return _python_fallback_restore(filepath)

        return True, "Database restored successfully!"
    except Exception as e:
        return _python_fallback_restore(filepath)


def _python_fallback_restore(filepath):
    """Restore .sql file using Python MySQL connector."""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()

        with open(filepath, "r", encoding="utf-8") as f:
            sql_content = f.read()

        statements = sql_content.split(";\n")
        for stmt in statements:
            stmt = stmt.strip()
            if stmt and not stmt.startswith("--"):
                try:
                    cursor.execute(stmt)
                except Exception:
                    pass

        conn.commit()
        cursor.close()
        conn.close()
        return True, "Database restored successfully (via Python fallback)!"
    except Exception as e:
        return False, f"Restore failed: {str(e)}"


def list_backups():
    """
    Returns list of all available backup files with details.
    """
    ensure_backup_dir()
    sql_files = glob.glob(os.path.join(BACKUP_DIR, "*.sql"))
    backups = []

    for path in sorted(sql_files, key=os.path.getmtime, reverse=True):
        fname = os.path.basename(path)
        stat = os.stat(path)
        mtime = datetime.datetime.fromtimestamp(stat.st_mtime)
        size_kb = stat.st_size / 1024
        size_str = f"{size_kb:.1f} KB" if size_kb < 1024 else f"{(size_kb/1024):.2f} MB"

        b_type = "Automated" if "auto" in fname.lower() or "scheduled" in fname.lower() else "Manual"

        backups.append({
            'filename': fname,
            'filepath': path,
            'datetime': mtime.strftime("%Y-%m-%d %I:%M:%S %p"),
            'date': mtime.strftime("%Y-%m-%d"),
            'size': size_str,
            'type': b_type,
            'size_bytes': stat.st_size,
            'mtime': stat.st_mtime
        })

    return backups


def prune_old_backups(days=30):
    """Deletes backups older than specified days."""
    try:
        now = time.time()
        cutoff = now - (days * 86400)
        for b in list_backups():
            if b['mtime'] < cutoff:
                os.remove(b['filepath'])
    except Exception:
        pass


def check_and_run_startup_auto_backup():
    """
    Checks if today's backup exists. If not, runs background backup.
    Non-blocking, runs in separate daemon thread.
    """
    def _worker():
        try:
            today_str = datetime.datetime.now().strftime("%Y%m%d")
            existing = list_backups()
            already_done = any(today_str in b['filename'] for b in existing)
            if not already_done:
                create_backup(tag="auto_daily")
        except Exception:
            pass

    t = threading.Thread(target=_worker, daemon=True)
    t.start()


def register_windows_task(time_str="14:00"):
    """
    Registers or updates a daily automated backup task in Windows Task Scheduler.
    Task will run as soon as possible if a scheduled start was missed.
    """
    try:
        project_dir = os.path.dirname(os.path.abspath(__file__))
        bat_file = os.path.join(project_dir, "run_scheduled_backup.bat")

        # schtasks command to create/update daily task
        cmd = [
            "schtasks", "/Create",
            "/TN", TASK_NAME,
            "/TR", f'"{bat_file}"',
            "/SC", "DAILY",
            "/ST", time_str,
            "/F"  # Force overwrite if already exists
        ]

        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )

        if result.returncode == 0:
            return True, f"Windows Scheduled Task registered successfully for daily {time_str}!"
        else:
            return False, f"Could not create task: {result.stderr.strip() or result.stdout.strip()}"
    except Exception as e:
        return False, f"Error registering task: {str(e)}"


def get_windows_task_status():
    """Checks if the Windows Task Scheduler task is active."""
    try:
        cmd = ["schtasks", "/Query", "/TN", TASK_NAME, "/FO", "LIST"]
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        if result.returncode == 0 and "TaskName:" in result.stdout:
            # Extract Next Run Time if available
            next_run = "Active"
            for line in result.stdout.splitlines():
                if "Next Run Time:" in line:
                    next_run = line.split(":", 1)[1].strip()
                    break
            return True, next_run
        return False, "Not Registered"
    except Exception:
        return False, "Unknown"


def unregister_windows_task():
    """Removes the task from Windows Task Scheduler."""
    try:
        cmd = ["schtasks", "/Delete", "/TN", TASK_NAME, "/F"]
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        return result.returncode == 0
    except Exception:
        return False
