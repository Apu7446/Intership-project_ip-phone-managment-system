"""
SBAC IP Phone Management System — Database Module
Handles MySQL connection, index setup, and all CRUD operations using unified departments master table.
Auto-starts XAMPP MySQL if offline. Auto-seeds initial CSV data files if database is empty.
"""

import mysql.connector
from mysql.connector import pooling
import subprocess
import time
import os
from config import DB_CONFIG

# XAMPP MySQL Executable Paths
XAMPP_MYSQL_DIR = r"c:\xampp\mysql"
MYSQLD_PATH = os.path.join(XAMPP_MYSQL_DIR, "bin", "mysqld.exe")
MY_INI_PATH = os.path.join(XAMPP_MYSQL_DIR, "bin", "my.ini")

_connection_pool = None


def reset_connection_pool():
    """Reset connection pool so it re-initializes with updated DB_CONFIG."""
    global _connection_pool
    _connection_pool = None


def init_connection_pool():
    """Initialize MySQL connection pool."""
    global _connection_pool
    if _connection_pool is not None:
        return True
    try:
        pool_config = DB_CONFIG.copy()
        pool_config['pool_name'] = 'sbac_pool'
        pool_config['pool_size'] = 10
        pool_config['pool_reset_session'] = True
        pool_config.setdefault('connect_timeout', 3)
        _connection_pool = pooling.MySQLConnectionPool(**pool_config)
        return True
    except Exception:
        _connection_pool = None
        return False


def _start_mysql():
    """Attempt to start XAMPP MySQL background process."""
    if not os.path.exists(MYSQLD_PATH):
        return False
    try:
        subprocess.Popen(
            [MYSQLD_PATH, f"--defaults-file={MY_INI_PATH}", "--standalone"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        return True
    except Exception:
        return False


def ensure_database():
    """Ensure database 'sbac_ipphone' and all required tables exist in MySQL."""
    reset_connection_pool()
    db_name = DB_CONFIG.get('database', 'sbac_ipphone')
    server_config = {k: v for k, v in DB_CONFIG.items() if k != 'database'}
    server_config.setdefault('connect_timeout', 3)
    try:
        conn = mysql.connector.connect(**server_config)
    except mysql.connector.Error:
        is_local = str(DB_CONFIG.get('host', '')).strip().lower() in ('localhost', '127.0.0.1')
        if is_local and _start_mysql():
            for _ in range(8):
                time.sleep(1)
                try:
                    conn = mysql.connector.connect(**server_config)
                    break
                except mysql.connector.Error:
                    continue
            else:
                return False
        else:
            return False

    try:
        cursor = conn.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci")
        cursor.execute(f"USE `{db_name}`")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS `departments` (
              `dept_id` INT(11) NOT NULL AUTO_INCREMENT,
              `dept_name` VARCHAR(150) NOT NULL,
              `dept_type` ENUM('HO Division','Branch','Sub-Branch') NOT NULL DEFAULT 'Branch',
              `status` ENUM('Active','Inactive') DEFAULT 'Active',
              PRIMARY KEY (`dept_id`),
              UNIQUE KEY `dept_name` (`dept_name`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS `users` (
              `user_id` INT(11) NOT NULL AUTO_INCREMENT,
              `full_name` VARCHAR(100) NOT NULL,
              `username` VARCHAR(50) NOT NULL,
              `password` VARCHAR(255) NOT NULL,
              `role` ENUM('Admin','ICT Operator') NOT NULL,
              `status` ENUM('Active','Inactive') DEFAULT 'Active',
              PRIMARY KEY (`user_id`),
              UNIQUE KEY `username` (`username`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS `ip_phones` (
              `phone_id` INT(11) NOT NULL AUTO_INCREMENT,
              `dept_id` INT(11) DEFAULT NULL,
              `employee_id` VARCHAR(50) DEFAULT NULL,
              `employee_name` VARCHAR(150) DEFAULT NULL,
              `issue_date` DATE DEFAULT NULL,
              `brand` VARCHAR(50) NOT NULL DEFAULT 'Fanvil',
              `model` VARCHAR(50) DEFAULT NULL,
              `phone_set_serial_no` VARCHAR(100) DEFAULT NULL,
              `ip_address` VARCHAR(50) DEFAULT NULL,
              `extension` VARCHAR(20) DEFAULT NULL,
              `caller_id` VARCHAR(50) DEFAULT NULL,
              `position` VARCHAR(100) DEFAULT NULL,
              `department` VARCHAR(150) DEFAULT NULL,
              `status` ENUM('Active','Inactive') DEFAULT 'Active',
              `delivery_status` ENUM('Delivered','Pending') DEFAULT 'Pending',
              `configure_status` ENUM('Done','ON') DEFAULT 'Done',
              `remarks` TEXT DEFAULT NULL,
              `created_by` INT(11) NOT NULL,
              `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
              `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
              PRIMARY KEY (`phone_id`),
              UNIQUE KEY `phone_set_serial_no` (`phone_set_serial_no`),
              UNIQUE KEY `extension` (`extension`),
              UNIQUE KEY `ip_address` (`ip_address`),
              KEY `created_by` (`created_by`),
              CONSTRAINT `fk_ip_phones_dept` FOREIGN KEY (`dept_id`) REFERENCES `departments` (`dept_id`) ON DELETE SET NULL,
              CONSTRAINT `fk_ip_phones_user` FOREIGN KEY (`created_by`) REFERENCES `users` (`user_id`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
        """)

        cursor.execute("SELECT COUNT(*) FROM users WHERE username='admin'")
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                INSERT INTO users (full_name, username, password, role, status)
                VALUES ('System Administrator', 'admin', 'admin123', 'Admin', 'Active')
            """)

        cursor.execute("SELECT COUNT(*) FROM users WHERE username='joydev'")
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                INSERT INTO users (full_name, username, password, role, status)
                VALUES ('Joydev', 'joydev', 'joydev123456', 'ICT Operator', 'Active')
            """)

        cursor.execute("SELECT COUNT(*) FROM users WHERE username='tauhid'")
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                INSERT INTO users (full_name, username, password, role, status)
                VALUES ('Tauhid', 'tauhid', 'tauhid@123456', 'ICT Operator', 'Active')
            """)

        conn.commit()
        cursor.close()
        conn.close()

        # Seed data if empty
        seed_official_locations()
        return True
    except Exception as e:
        print(f"[ERROR] Database creation failed: {e}")
        return False


def get_connection():
    """Get MySQL connection using connection pool with fallback to direct connection."""
    global _connection_pool
    if _connection_pool is not None:
        try:
            return _connection_pool.get_connection()
        except mysql.connector.Error as pool_err:
            if pool_err.errno == 1049:  # Unknown database
                ensure_database()
                init_connection_pool()
                if _connection_pool:
                    return _connection_pool.get_connection()

    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        init_connection_pool()
        return conn
    except mysql.connector.Error as err:
        if err.errno == 1049:
            ensure_database()
            init_connection_pool()
            return mysql.connector.connect(**DB_CONFIG)
        is_local = str(DB_CONFIG.get('host', '')).strip().lower() in ('localhost', '127.0.0.1')
        if is_local and _start_mysql():
            for _ in range(8):
                time.sleep(1)
                try:
                    conn = mysql.connector.connect(**DB_CONFIG)
                    init_connection_pool()
                    return conn
                except mysql.connector.Error:
                    continue
        host = DB_CONFIG.get('host', 'server')
        raise ConnectionError(f"Unable to connect to MySQL database at {host}! Error: {err}")


def cleanup_legacy_none_values():
    """Clean up existing 'None' and empty string records in ip_phones to proper SQL NULL."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE ip_phones SET
                phone_set_serial_no = CASE WHEN phone_set_serial_no IN ('None', 'none', 'NULL', 'null', '') THEN NULL ELSE phone_set_serial_no END,
                extension = CASE WHEN extension IN ('None', 'none', 'NULL', 'null', '') THEN NULL ELSE extension END,
                caller_id = CASE WHEN caller_id IN ('None', 'none', 'NULL', 'null', '') THEN NULL ELSE caller_id END,
                employee_id = CASE WHEN employee_id IN ('None', 'none', 'NULL', 'null', '') THEN NULL ELSE employee_id END,
                employee_name = CASE WHEN employee_name IN ('None', 'none', 'NULL', 'null', '') THEN NULL ELSE employee_name END,
                model = CASE WHEN model IN ('None', 'none', 'NULL', 'null', '') THEN NULL ELSE model END,
                position = CASE WHEN position IN ('None', 'none', 'NULL', 'null', '') THEN NULL ELSE position END,
                ip_address = CASE WHEN ip_address IN ('None', 'none', 'NULL', 'null', '') THEN NULL ELSE ip_address END
            WHERE
                phone_set_serial_no IN ('None', 'none', 'NULL', 'null', '') OR
                extension IN ('None', 'none', 'NULL', 'null', '') OR
                caller_id IN ('None', 'none', 'NULL', 'null', '') OR
                employee_id IN ('None', 'none', 'NULL', 'null', '') OR
                employee_name IN ('None', 'none', 'NULL', 'null', '') OR
                model IN ('None', 'none', 'NULL', 'null', '') OR
                position IN ('None', 'none', 'NULL', 'null', '') OR
                ip_address IN ('None', 'none', 'NULL', 'null', '')
        """)
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"[WARN] Database cleanup error: {e}")


def ensure_indexes():
    """Create optimal database indexes for fast query execution."""
    cleanup_legacy_none_values()
    conn = get_connection()
    cursor = conn.cursor(buffered=True)
    indexes = [
        ("idx_serial", "ip_phones", "phone_set_serial_no"),
        ("idx_ip", "ip_phones", "ip_address"),
        ("idx_ext", "ip_phones", "extension"),
        ("idx_caller_id", "ip_phones", "caller_id"),
        ("idx_status", "ip_phones", "status"),
        ("idx_delivery", "ip_phones", "delivery_status"),
        ("idx_dept", "ip_phones", "dept_id"),
        ("idx_dept_type_status", "departments", "dept_type, status")
    ]
    for idx_name, table_name, column_name in indexes:
        try:
            cursor.execute(f"SHOW INDEX FROM {table_name} WHERE Key_name = '{idx_name}'")
            res = cursor.fetchall()
            if not res:
                cursor.execute(f"CREATE INDEX {idx_name} ON {table_name} ({column_name})")
        except Exception:
            pass
    conn.commit()
    cursor.close()
    conn.close()


def seed_official_locations():
    """Import CSV data files if ip_phones table is empty."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM ip_phones")
        count = cursor.fetchone()[0]
        cursor.close()
        conn.close()

        if count == 0:
            import import_from_excel
            base_dir = os.path.dirname(__file__)
            ho_csv = os.path.join(base_dir, "HeadOffice.csv")
            br_csv = os.path.join(base_dir, "Branch & Sub-Branch.csv")

            if os.path.exists(ho_csv):
                import_from_excel.import_file(ho_csv, created_by=1)
            if os.path.exists(br_csv):
                import_from_excel.import_file(br_csv, created_by=1)
    except Exception as e:
        print(f"[WARN] Data seeding error: {e}")


# ── Dashboard Stats Queries ──

def get_dashboard_stats():
    """Fetch high level stats for dashboard cards."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    stats = {
        'total_phones': 0, 'active_phones': 0, 'inactive_phones': 0,
        'delivered': 0, 'pending': 0, 'total_branches': 0,
        'total_divisions': 0, 'branch_phones': 0
    }

    cursor.execute("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN status = 'Active' THEN 1 ELSE 0 END) as active_cnt,
            SUM(CASE WHEN status = 'Inactive' THEN 1 ELSE 0 END) as inactive_cnt,
            SUM(CASE WHEN delivery_status = 'Delivered' THEN 1 ELSE 0 END) as delivered_cnt,
            SUM(CASE WHEN delivery_status = 'Pending' THEN 1 ELSE 0 END) as pending_cnt
        FROM ip_phones
    """)
    res = cursor.fetchone()
    if res:
        stats['total_phones'] = res['total'] or 0
        stats['active_phones'] = res['active_cnt'] or 0
        stats['inactive_phones'] = res['inactive_cnt'] or 0
        stats['delivered'] = res['delivered_cnt'] or 0
        stats['pending'] = res['pending_cnt'] or 0

    cursor.execute("SELECT COUNT(*) as cnt FROM departments WHERE dept_type IN ('Branch', 'Sub-Branch') AND status='Active'")
    res = cursor.fetchone()
    if res:
        stats['total_branches'] = res['cnt'] or 0

    cursor.execute("SELECT COUNT(*) as cnt FROM departments WHERE dept_type = 'HO Division' AND status='Active'")
    res = cursor.fetchone()
    if res:
        stats['total_divisions'] = res['cnt'] or 0

    cursor.execute("""
        SELECT COUNT(p.phone_id) as cnt
        FROM ip_phones p
        JOIN departments d ON p.dept_id = d.dept_id
        WHERE d.dept_type IN ('Branch', 'Sub-Branch')
    """)
    res = cursor.fetchone()
    if res:
        stats['branch_phones'] = res['cnt'] or 0

    cursor.close()
    conn.close()
    return stats


def get_division_phone_counts():
    """Get phone counts grouped by Head Office Division."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT 
            d.dept_id as division_id,
            d.dept_name as division_name,
            COUNT(p.phone_id) as total_phones,
            SUM(CASE WHEN p.status = 'Active' THEN 1 ELSE 0 END) as active_phones
        FROM departments d
        LEFT JOIN ip_phones p ON d.dept_id = p.dept_id
        WHERE d.dept_type = 'HO Division' AND d.status = 'Active'
        GROUP BY d.dept_id, d.dept_name
        ORDER BY total_phones DESC, d.dept_name ASC
    """)
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows


def get_position_phone_counts():
    """Get phone counts grouped by Position / Designation."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT 
            IFNULL(NULLIF(position, ''), 'Unspecified') as position_name,
            COUNT(phone_id) as total_phones,
            SUM(CASE WHEN status = 'Active' THEN 1 ELSE 0 END) as active_phones
        FROM ip_phones
        GROUP BY position_name
        ORDER BY total_phones DESC, position_name ASC
    """)
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows


# ── Department CRUD Queries ──

def get_all_departments():
    """Fetch list of all active departments."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM departments ORDER BY dept_name ASC")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows


def get_department_counts():
    """Fetch departments along with their assigned phone count."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT 
            d.dept_id, d.dept_name, d.dept_type, d.status,
            COUNT(p.phone_id) as phone_count
        FROM departments d
        LEFT JOIN ip_phones p ON d.dept_id = p.dept_id
        GROUP BY d.dept_id
        ORDER BY d.dept_type ASC, d.dept_name ASC
    """)
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows


def add_department(dept_name, dept_type='Branch'):
    """Add a new department."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO departments (dept_name, dept_type) VALUES (%s, %s)",
        (dept_name.strip(), dept_type)
    )
    dept_id = cursor.lastrowid
    conn.commit()
    cursor.close()
    conn.close()
    return dept_id


def update_department(dept_id, dept_name, dept_type, status):
    """Update department info."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE departments SET dept_name = %s, dept_type = %s, status = %s WHERE dept_id = %s",
        (dept_name.strip(), dept_type, status, dept_id)
    )
    conn.commit()
    cursor.close()
    conn.close()


def delete_department(dept_id):
    """Delete department if no phones attached."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM departments WHERE dept_id = %s", (dept_id,))
    conn.commit()
    cursor.close()
    conn.close()


# ── IP Phone Directory Queries ──

def get_filtered_phones(
    loc_type="All", search_by="All Fields", search_term="",
    location="All Locations", status="All Status",
    delivery="All Delivery", config_status="All Config",
    position_filter="", sort_asc=True
):
    """Fetch IP phones filtered by criteria."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT p.*, d.dept_name, d.dept_type
        FROM ip_phones p
        LEFT JOIN departments d ON p.dept_id = d.dept_id
        WHERE 1=1
    """
    params = []

    if loc_type != "All":
        query += " AND d.dept_type = %s"
        params.append(loc_type)

    if location != "All Locations":
        query += " AND d.dept_name = %s"
        params.append(location)

    if status != "All Status":
        query += " AND p.status = %s"
        params.append(status)

    if delivery != "All Delivery":
        query += " AND p.delivery_status = %s"
        params.append(delivery)

    if config_status != "All Config":
        query += " AND p.configure_status = %s"
        params.append(config_status)

    if position_filter:
        query += " AND p.position = %s"
        params.append(position_filter)

    if search_term:
        term = f"%{search_term}%"
        if search_by == "Employee ID":
            query += " AND p.employee_id LIKE %s"
            params.append(term)
        elif search_by == "Name":
            query += " AND p.employee_name LIKE %s"
            params.append(term)
        elif search_by in ("Department", "Branch Name", "Division Name"):
            query += " AND (d.dept_name LIKE %s OR p.department LIKE %s)"
            params.extend([term, term])
        elif search_by == "IP Address":
            query += " AND p.ip_address LIKE %s"
            params.append(term)
        elif search_by == "Extension":
            query += " AND p.extension LIKE %s"
            params.append(term)
        elif search_by == "Caller ID":
            query += " AND p.caller_id LIKE %s"
            params.append(term)
        elif search_by == "Serial No":
            query += " AND p.phone_set_serial_no LIKE %s"
            params.append(term)
        elif search_by == "Position":
            query += " AND p.position LIKE %s"
            params.append(term)
        elif search_by == "Brand & Model":
            query += " AND (p.brand LIKE %s OR p.model LIKE %s)"
            params.extend([term, term])
        else:  # All Fields
            query += """ AND (
                p.employee_name LIKE %s OR p.employee_id LIKE %s OR p.extension LIKE %s OR
                p.ip_address LIKE %s OR p.phone_set_serial_no LIKE %s OR p.caller_id LIKE %s OR
                p.position LIKE %s OR d.dept_name LIKE %s OR p.department LIKE %s OR
                p.brand LIKE %s OR p.model LIKE %s
            )"""
            params.extend([term] * 11)

    order = "ASC" if sort_asc else "DESC"
    query += f" ORDER BY p.phone_id {order}"

    cursor.execute(query, params)
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows


def _sanitize_db_val(val):
    """Sanitize database value to ensure empty, 'None', 'null' strings convert to None (SQL NULL)."""
    if val is None:
        return None
    if isinstance(val, str):
        v = val.strip()
        if not v or v.lower() in ('none', 'null', 'select location'):
            return None
        return v
    return val


def add_phone(phone_data):
    """Add a new IP phone entry."""
    cleanup_legacy_none_values()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO ip_phones (
            dept_id, employee_id, employee_name, issue_date,
            brand, model, phone_set_serial_no, ip_address,
            extension, caller_id, position, department,
            status, delivery_status, configure_status, remarks, created_by
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        phone_data.get('dept_id'),
        _sanitize_db_val(phone_data.get('employee_id')),
        _sanitize_db_val(phone_data.get('employee_name')),
        phone_data.get('issue_date'),
        phone_data.get('brand', 'Fanvil') or 'Fanvil',
        _sanitize_db_val(phone_data.get('model')),
        _sanitize_db_val(phone_data.get('phone_set_serial_no')),
        _sanitize_db_val(phone_data.get('ip_address')),
        _sanitize_db_val(phone_data.get('extension')),
        _sanitize_db_val(phone_data.get('caller_id')),
        _sanitize_db_val(phone_data.get('position')),
        _sanitize_db_val(phone_data.get('department')),
        phone_data.get('status', 'Active') or 'Active',
        phone_data.get('delivery_status', 'Pending') or 'Pending',
        phone_data.get('configure_status', 'Done') or 'Done',
        _sanitize_db_val(phone_data.get('remarks')),
        phone_data['created_by']
    ))
    phone_id = cursor.lastrowid
    conn.commit()
    cursor.close()
    conn.close()
    return phone_id


def update_phone(phone_id, phone_data):
    """Update an existing IP phone record."""
    cleanup_legacy_none_values()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE ip_phones SET
            dept_id = %s, employee_id = %s, employee_name = %s,
            issue_date = %s, brand = %s, model = %s,
            phone_set_serial_no = %s, ip_address = %s,
            extension = %s, caller_id = %s, position = %s, department = %s,
            status = %s, delivery_status = %s, configure_status = %s, remarks = %s
        WHERE phone_id = %s
    """, (
        phone_data.get('dept_id'),
        _sanitize_db_val(phone_data.get('employee_id')),
        _sanitize_db_val(phone_data.get('employee_name')),
        phone_data.get('issue_date'),
        phone_data.get('brand') or 'Fanvil',
        _sanitize_db_val(phone_data.get('model')),
        _sanitize_db_val(phone_data.get('phone_set_serial_no')),
        _sanitize_db_val(phone_data.get('ip_address')),
        _sanitize_db_val(phone_data.get('extension')),
        _sanitize_db_val(phone_data.get('caller_id')),
        _sanitize_db_val(phone_data.get('position')),
        _sanitize_db_val(phone_data.get('department')),
        phone_data.get('status') or 'Active',
        phone_data.get('delivery_status') or 'Pending',
        phone_data.get('configure_status') or 'Done',
        _sanitize_db_val(phone_data.get('remarks')),
        phone_id
    ))
    conn.commit()
    cursor.close()
    conn.close()


def delete_phone(phone_id):
    """Delete an IP phone entry."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM ip_phones WHERE phone_id = %s", (phone_id,))
    conn.commit()
    cursor.close()
    conn.close()


# ── User Authentication & Management Queries ──

def authenticate_user(username, password):
    """Authenticate system user."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE username = %s AND password = %s AND status = 'Active'", (username, password))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    return user


def get_all_users():
    """Fetch all users."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT user_id, full_name, username, role, status FROM users ORDER BY user_id ASC")
    users = cursor.fetchall()
    cursor.close()
    conn.close()
    return users


def add_user(full_name, username, password, role='ICT Operator'):
    """Add a new user."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO users (full_name, username, password, role, status)
        VALUES (%s, %s, %s, %s, 'Active')
    """, (full_name, username, password, role))
    user_id = cursor.lastrowid
    conn.commit()
    cursor.close()
    conn.close()
    return user_id


def update_user(user_id, full_name, username, role, status, password=None):
    """Update user account."""
    conn = get_connection()
    cursor = conn.cursor()
    if password:
        cursor.execute("""
            UPDATE users SET full_name = %s, username = %s, password = %s, role = %s, status = %s
            WHERE user_id = %s
        """, (full_name, username, password, role, status, user_id))
    else:
        cursor.execute("""
            UPDATE users SET full_name = %s, username = %s, role = %s, status = %s
            WHERE user_id = %s
        """, (full_name, username, role, status, user_id))
    conn.commit()
    cursor.close()
    conn.close()


def delete_user(user_id):
    """Delete a user account."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE user_id = %s", (user_id,))
    conn.commit()
    cursor.close()
    conn.close()


# ── Real-Time Multi-PC Live Sync Signatures ──

def get_phones_data_signature(location=None):
    """
    Returns an ultra-lightweight fingerprint (count, max_id, sum_id)
    to check whether data in ip_phones was added, modified, or deleted on another computer in <2ms.
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        if location and location != "All Locations":
            cursor.execute(
                "SELECT COUNT(*), COALESCE(MAX(phone_id), 0), COALESCE(SUM(phone_id), 0), COALESCE(MAX(UNIX_TIMESTAMP(updated_at)), 0) FROM ip_phones "
                "WHERE department = %s OR dept_id IN (SELECT dept_id FROM departments WHERE dept_name = %s)",
                (location, location)
            )
        else:
            cursor.execute(
                "SELECT COUNT(*), COALESCE(MAX(phone_id), 0), COALESCE(SUM(phone_id), 0), COALESCE(MAX(UNIX_TIMESTAMP(updated_at)), 0) FROM ip_phones"
            )
        res = cursor.fetchone()
        cursor.close()
        conn.close()
        return res
    except Exception:
        return None


def get_departments_data_signature():
    """Returns fingerprint for departments table changes."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*), COALESCE(MAX(dept_id), 0), COALESCE(SUM(dept_id), 0) FROM departments")
        res = cursor.fetchone()
        cursor.close()
        conn.close()
        return res
    except Exception:
        return None


def test_db_connection(host, port=3306, user='root', password='', database='sbac_ipphone'):
    """Test connection to specified MySQL host server with a short timeout."""
    try:
        conn = mysql.connector.connect(
            host=host.strip(),
            port=int(port),
            user=user.strip(),
            password=password,
            database=database.strip(),
            connect_timeout=4,
            use_pure=True
        )
        cursor = conn.cursor()
        cursor.execute("SELECT DATABASE(), VERSION()")
        info = cursor.fetchone()
        cursor.close()
        conn.close()
        return True, f"Connected to '{info[0]}' (MySQL {info[1]})"
    except Exception as e:
        return False, str(e)

