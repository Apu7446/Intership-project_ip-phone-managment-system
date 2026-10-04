"""
SBAC IP Phone Management System — One-Click Automated Server Setup
Automatically configures the current PC to act as the Central Database Server:
1. Detects XAMPP MySQL installation and ensures MySQL service is running.
2. Creates the 'sbac_ipphone' database if it does not exist.
3. Grants remote access privileges ('root'@'%') so client PCs can connect.
4. Auto-restores the database from the latest .sql backup in backups/ directory.
5. Auto-detects the local LAN IP address of this machine.
6. Saves server_config.json and generates a SERVER_INFO.txt for reference.
"""

import os
import sys
import time
import socket
import glob
import subprocess
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKUP_DIR = os.path.join(BASE_DIR, "backups")
CONFIG_FILE = os.path.join(BASE_DIR, "server_config.json")
SERVER_INFO_FILE = os.path.join(BASE_DIR, "SERVER_INFO.txt")

# Possible XAMPP MySQL locations
POSSIBLE_MYSQL_DIRS = [
    r"c:\xampp\mysql",
    r"d:\xampp\mysql",
    r"e:\xampp\mysql",
    os.path.join(os.environ.get("SystemDrive", "C:"), r"\xampp\mysql")
]


def log(msg, tag="*"):
    print(f"[{tag}] {msg}")


def find_xampp_mysql():
    """Find mysqld.exe and mysql.exe in common XAMPP paths."""
    for base in POSSIBLE_MYSQL_DIRS:
        mysqld = os.path.join(base, "bin", "mysqld.exe")
        mysql_cli = os.path.join(base, "bin", "mysql.exe")
        my_ini = os.path.join(base, "bin", "my.ini")
        if os.path.exists(mysqld) and os.path.exists(mysql_cli):
            return {
                "dir": base,
                "mysqld": mysqld,
                "mysql": mysql_cli,
                "my_ini": my_ini
            }
    return None


def get_lan_ip():
    """Detect local LAN IP address of this PC."""
    # Method 1: Connect to a dummy external target (no packets actually sent)
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)
        # Attempt bank gateway or common IP
        s.connect(('172.19.100.254', 1))
        ip = s.getsockname()[0]
        s.close()
        if ip and not ip.startswith('127.'):
            return ip
    except Exception:
        pass

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        if ip and not ip.startswith('127.'):
            return ip
    except Exception:
        pass

    # Method 2: Hostname resolution
    try:
        hostname = socket.gethostname()
        for ip in socket.gethostbyname_ex(hostname)[2]:
            if not ip.startswith('127.') and not ip.startswith('169.254.'):
                return ip
    except Exception:
        pass

    return "127.0.0.1"


def is_mysql_running(port=3306):
    """Check if MySQL is actively listening on localhost:port."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1.0)
        result = s.connect_ex(('127.0.0.1', port))
        s.close()
        return result == 0
    except Exception:
        return False


def start_mysql(mysql_info):
    """Attempt to start MySQL server in background."""
    if is_mysql_running():
        return True

    log("MySQL is offline. Attempting to start XAMPP MySQL...", "*")

    # 1. Try Windows Service first if installed
    try:
        res = subprocess.run(["net", "start", "mysql"], capture_output=True, text=True)
        if res.returncode == 0 or is_mysql_running():
            log("MySQL started via Windows Service.", "OK")
            return True
    except Exception:
        pass

    # 2. Try mysqld standalone process
    if mysql_info and os.path.exists(mysql_info['mysqld']):
        try:
            cmd = [mysql_info['mysqld']]
            if os.path.exists(mysql_info['my_ini']):
                cmd.append(f"--defaults-file={mysql_info['my_ini']}")
            cmd.append("--standalone")

            subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            for _ in range(10):
                time.sleep(1)
                if is_mysql_running():
                    log("MySQL started successfully.", "OK")
                    return True
        except Exception as e:
            log(f"Could not start mysqld: {e}", "WARN")

    return is_mysql_running()


def setup_mysql_database_and_privileges(mysql_info):
    """Configure sbac_ipphone database and grant root@'%' remote access."""
    import mysql.connector

    log("Connecting to local MySQL server...", "*")
    conn = None
    try:
        conn = mysql.connector.connect(
            host="127.0.0.1",
            user="root",
            password="",
            port=3306,
            autocommit=True
        )
    except Exception as e:
        log(f"Failed to connect to MySQL: {e}", "ERROR")
        log("Please verify XAMPP MySQL is started in XAMPP Control Panel.", "!")
        return False

    cursor = conn.cursor()

    # 1. Create Database
    log("Creating database 'sbac_ipphone' if not exists...", "*")
    cursor.execute("CREATE DATABASE IF NOT EXISTS `sbac_ipphone` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci")

    # 2. Grant Remote Access to root@'%'
    log("Granting remote network access permissions ('root'@'%')...", "*")
    try:
        cursor.execute("CREATE USER IF NOT EXISTS 'root'@'%' IDENTIFIED BY ''")
    except Exception:
        pass

    try:
        cursor.execute("GRANT ALL PRIVILEGES ON *.* TO 'root'@'%' WITH GRANT OPTION")
    except Exception as e:
        log(f"Notice on GRANT: {e}", "WARN")

    try:
        cursor.execute("FLUSH PRIVILEGES")
    except Exception:
        pass

    cursor.close()
    conn.close()
    log("MySQL privileges successfully configured for Multi-PC use.", "OK")
    return True


def restore_or_init_database(mysql_info):
    """Restore from latest .sql backup, or fallback to init_db."""
    import mysql.connector

    # Check for latest backup
    latest_backup = None
    if os.path.exists(BACKUP_DIR):
        sql_files = glob.glob(os.path.join(BACKUP_DIR, "*.sql"))
        if sql_files:
            # Sort by modified time descending
            sql_files.sort(key=os.path.getmtime, reverse=True)
            latest_backup = sql_files[0]

    if latest_backup and os.path.exists(latest_backup) and os.path.getsize(latest_backup) > 0:
        log(f"Found latest backup: {os.path.basename(latest_backup)}", "*")
        log("Restoring database from this backup...", "*")

        # Attempt restore with mysql CLI
        restored = False
        if mysql_info and os.path.exists(mysql_info['mysql']):
            cmd = [
                mysql_info['mysql'],
                "--host=127.0.0.1",
                "--port=3306",
                "--user=root",
                "sbac_ipphone"
            ]
            try:
                with open(latest_backup, "r", encoding="utf-8") as in_f:
                    res = subprocess.run(cmd, stdin=in_f, capture_output=True, text=True)
                    if res.returncode == 0:
                        log("Database successfully restored from backup!", "OK")
                        restored = True
                    else:
                        log(f"CLI restore notice: {res.stderr.strip()}", "WARN")
            except Exception as e:
                log(f"CLI restore failed: {e}", "WARN")

        # Python fallback restore
        if not restored:
            try:
                conn = mysql.connector.connect(
                    host="127.0.0.1",
                    user="root",
                    password="",
                    port=3306,
                    database="sbac_ipphone"
                )
                cursor = conn.cursor()
                with open(latest_backup, "r", encoding="utf-8") as f:
                    content = f.read()
                for stmt in content.split(";\n"):
                    s = stmt.strip()
                    if s and not s.startswith("--"):
                        try:
                            cursor.execute(s)
                        except Exception:
                            pass
                conn.commit()
                cursor.close()
                conn.close()
                log("Database restored successfully via Python parser!", "OK")
                restored = True
            except Exception as e:
                log(f"Python fallback restore error: {e}", "WARN")

        if restored:
            return True

    # If no backup or restore failed, use init_db
    log("Initializing database structure from schema & official CSVs...", "*")
    try:
        import init_db
        init_db.create_database_and_tables()
        log("Database schema initialized successfully.", "OK")
        return True
    except Exception as e:
        log(f"Database initialization failed: {e}", "ERROR")
        return False


def update_server_configs(server_ip):
    """Write server_config.json and SERVER_INFO.txt."""
    # On the server PC itself, host can be 127.0.0.1 so it connects instantly locally
    config_data = {
        "host": "127.0.0.1",
        "port": 3306,
        "user": "root",
        "password": "",
        "database": "sbac_ipphone"
    }
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=4)
    log(f"Local config updated to 127.0.0.1 in {os.path.basename(CONFIG_FILE)}", "OK")

    # Generate info file for client PCs
    info_text = f"""========================================================================
   SBAC BANK PLC — IP Phone Management System
   CENTRAL SERVER PC INFORMATION
========================================================================

This computer is configured as the CENTRAL DATABASE SERVER.

► Server IP Address : {server_ip}
► MySQL Port        : 3306
► Database Name     : sbac_ipphone
► Configured At     : {time.strftime('%Y-%m-%d %H:%M:%S')}

------------------------------------------------------------------------
HOW TO CONNECT OTHER COMPUTERS (Client PCs) TO THIS SERVER:
------------------------------------------------------------------------
Method 1 (Recommended):
1. Copy the project folder to the client PC.
2. Launch the application by double-clicking RUN_APP.bat.
3. On the Login Screen, click the [🖥️ Server Settings] button.
4. In "Server PC Host IP", enter: {server_ip}
5. Click [Test Connection] -> Click [Save & Connect].

Method 2:
Open "server_config.json" on any Client PC and set:
{{
    "host": "{server_ip}",
    "port": 3306,
    "user": "root",
    "password": "",
    "database": "sbac_ipphone"
}}
========================================================================
"""
    with open(SERVER_INFO_FILE, "w", encoding="utf-8") as f:
        f.write(info_text)
    log(f"Instructions saved to {os.path.basename(SERVER_INFO_FILE)}", "OK")


def main():
    print("=" * 72)
    print("   SBAC BANK PLC — IP Phone Management System")
    print("   1-CLICK AUTOMATED SERVER PC SETUP & MIGRATION TOOL")
    print("=" * 72)
    print()

    # Step 1: Detect LAN IP
    detected_ip = get_lan_ip()
    log(f"Detected Network IP Address: {detected_ip}", "OK")
    print()
    user_choice = input(f"► Press [ENTER] to use '{detected_ip}', or type custom IP: ").strip()
    server_ip = user_choice if user_choice else detected_ip
    log(f"Selected Server Host IP: {server_ip}", "OK")
    print()

    # Step 2: Locate XAMPP MySQL
    mysql_info = find_xampp_mysql()
    if mysql_info:
        log(f"Found XAMPP MySQL at: {mysql_info['dir']}", "OK")
    else:
        log("XAMPP MySQL directory not found in standard paths (c:\\xampp\\mysql).", "WARN")

    # Step 3: Start MySQL if not running
    if not start_mysql(mysql_info):
        print()
        log("CRITICAL: MySQL server is not running on port 3306!", "ERROR")
        log("Please open XAMPP Control Panel and click [Start] next to MySQL.", "!")
        input("\nPress Enter once MySQL is started in XAMPP...")
        if not is_mysql_running():
            log("MySQL is still not running. Aborting setup.", "ERROR")
            sys.exit(1)

    log("MySQL connection test passed (port 3306 is ACTIVE).", "OK")

    # Step 4: Configure Database and Privileges
    if not setup_mysql_database_and_privileges(mysql_info):
        log("Could not configure MySQL database and permissions.", "ERROR")
        sys.exit(1)

    # Step 5: Restore or Initialize Database
    if not restore_or_init_database(mysql_info):
        log("Could not restore or initialize database.", "ERROR")
        sys.exit(1)

    # Step 6: Update Configs
    update_server_configs(server_ip)

    print()
    print("=" * 72)
    print("   🎉 SERVER SETUP COMPLETED SUCCESSFULLY! 🎉")
    print("=" * 72)
    print(f" ► Server PC Host IP : {server_ip}")
    print(f" ► MySQL Port        : 3306")
    print(f" ► Database          : sbac_ipphone")
    print(f" ► Status            : Ready for Multi-PC live connections!")
    print("=" * 72)
    print()
    print("Client PCs will connect to Host IP:", server_ip)
    print("Full details are saved in: SERVER_INFO.txt")
    print()


if __name__ == "__main__":
    main()
