"""
SBAC IP Phone - Import from CSV/Excel
======================================
Bulk import IP phones data from CSV or Excel (.xlsx) into ip_phones table.
Properly maps Branch, Sub-Branch, and Head Office divisions.
"""

import csv
import os
from datetime import datetime, date

try:
    import openpyxl
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False

import db


# Known Head Office division keywords
HEAD_OFFICE_KEYWORDS = [
    "SECRETARIAT", "DIVISION", "DIVISON", "CRM", "FAD", "PS",
    "MIS", "TRAINING", "TREASURY", "Investment", "Corporate Banking",
    "Corporate Business Banking", "Corporate Business Banking Division",
    "Legal Division", "Retail Distribution", "Trade Processing",
    "Digital Financial", "DFID", "ICC", "BOD", "CAD", "AML", "BAMLD",
    "INSTITUTE", "SECRETARY", "MANAGEMENT", "ATTACHMENT", "SERVICE",
    "OPERATION", "OPERATIONS", "UNIT", "DESK", "EXCHANGE", "PUBLIC RELATION",
    "SME", "SPECIAL ASSET", "AGENT BANKING", "SENIOR MANAGEMENT",
    " IT", "ICT"  # Information Technology divisions
]


def is_head_office(name):
    """Check if the name is a Head Office division (not a branch)"""
    if not name:
        return False
    upper = name.upper()
    for kw in HEAD_OFFICE_KEYWORDS:
        if kw.upper() in upper:
            return True
    return False


def parse_date(val):
    """Date value parse — multiple format support"""
    if val is None:
        return date.today()
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    if isinstance(val, str):
        val = val.strip()
        if not val:
            return date.today()
        for fmt in ['%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y', '%m/%d/%Y']:
            try:
                return datetime.strptime(val, fmt).date()
            except ValueError:
                continue
    return date.today()


def clean_val(val):
    """Clean a cell value to string, returning '' if empty or None."""
    if val is None:
        return ''
    if isinstance(val, (int, float)):
        return str(int(val))
    s = str(val).strip()
    if s.lower() in ('none', 'null'):
        return ''
    return s


def read_csv_rows(filepath):
    """Read rows from a CSV file. Returns list of dicts."""
    rows = []
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def read_excel_rows(filepath):
    """Read rows from an Excel file. Returns list of dicts."""
    if not HAS_OPENPYXL:
        raise ImportError("openpyxl package needed for Excel import. Install: pip install openpyxl")
    wb = openpyxl.load_workbook(filepath)
    ws = wb.active
    headers = [str(cell.value).strip() if cell.value else f"col{i}"
               for i, cell in enumerate(ws[1])]
    rows = []
    for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
        d = {}
        for i, cell in enumerate(row):
            if i < len(headers):
                d[headers[i]] = cell.value
        rows.append(d)
    return rows


def find_match(name, mapping):
    """Find a branch/division by name with fuzzy matching."""
    if not name:
        return None
    search = name.strip().lower()

    # Exact match
    if search in mapping:
        return mapping[search]

    # Partial match
    for key, val in mapping.items():
        if search in key or key in search:
            return val

    return None


# Column name aliases for mapping CSV/Excel headers to our fields
COLUMN_ALIASES = {
    'employee_id': ['employee id', 'employee_id', 'emp id', 'emp_id', 'employeeid'],
    'employee_name': ['name', 'employee name', 'user name', 'employee_name'],
    'issue_date': ['issue date', 'issue_date', 'date', 'issuedate'],
    'location': ['department(division/branch/sub_branch)', 'department', 'location', 'division/branch', 'division_branch', 'branch',
                 'division', 'branch / division', 'sub branch', 'sub_branch', 'posting', 'placement'],
    'brand': ['brand', 'make', 'manufacturer', 'phone brand'],
    'serial_no': ['phone set serial no', 'phone unique set serial id', 'set serial no', 'phone unique set serial no', 'model s/n', 'model_sn', 'model/sn', 'model sn', 'serial no', 'serial_no', 'serial', 's/n'],
    'ip_address': ['last reg. ip', 'ip address', 'ip_address', 'ip', 'ipaddress'],
    'extension': ['extention', 'extension', 'ext', 'ext.', 'extn'],
    'caller_id': ['callerid', 'caller id', 'caller_id', 'did no', 'did_no', 'did', 'did number'],
    'position': ['position', 'designation', 'post'],
    'configure_status': ['configure(done radio button) if not done then on', 'configure', 'ip configure', 'configure status', 'configure_status'],
    'status': ['active redio button', 'status', 'status (active', 'status (active/inactive)', 'status (active, inactive)'],
    'delivery_status': ['deliver (yes  or no radio button', 'deliver', 'delivery (yes ,no and pending)', 'delivery (yes, no, pending)',
                        'delivery status', 'delivery_status', 'delivery', 'delivery (yes/no/pending)'],
    'remarks': ['remarks', 'remark', 'note', 'notes'],
}


def map_columns(row_keys):
    """Map CSV/Excel column names to our field names."""
    mapping = {}
    lower_keys = {k.lower().strip(): k for k in row_keys}

    for field, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            # Exact match first
            if alias in lower_keys:
                mapping[field] = lower_keys[alias]
                break
            # Partial match if no exact match
            matched = False
            for k_lower, k_orig in lower_keys.items():
                if alias in k_lower:
                    mapping[field] = k_orig
                    matched = True
                    break
            if matched:
                break
    return mapping


def import_file(filepath, created_by=1):
    """
    Import data from a CSV or Excel file into the ip_phones table.
    Automatically maps departments to existing or new records in `departments`.
    Returns tuple: (inserted_count, skipped_count, errors_list)
    """
    ext = os.path.splitext(filepath)[1].lower()

    if ext == '.csv':
        rows = read_csv_rows(filepath)
    elif ext in ('.xlsx', '.xls'):
        rows = read_excel_rows(filepath)
    else:
        raise ValueError(f"Unsupported file format: {ext}")

    if not rows:
        return 0, 0, ["File is empty"]

    # Build column mapping
    col_map = map_columns(rows[0].keys())

    # Verify minimum required fields
    if 'extension' not in col_map:
        return 0, 0, ["Could not find 'Extension' column in file"]

    # Pre-fetch all departments for fast lookup
    all_depts = db.get_all_departments()
    dept_map = {}
    for d in all_depts:
        dept_map[d['dept_name'].strip().lower()] = d

    conn = db.get_connection()
    cursor = conn.cursor()

    inserted = 0
    skipped = 0
    errors = []

    for idx, row in enumerate(rows, start=2):
        try:
            ext_val = clean_val(row.get(col_map.get('extension', ''), ''))
            if not ext_val:
                skipped += 1
                continue

            # Format extension properly (remove decimals if float string)
            if '.' in ext_val:
                ext_val = ext_val.split('.')[0]

            ip_val = clean_val(row.get(col_map.get('ip_address', ''), ''))
            if ip_val == 'None' or ip_val.lower() == 'null':
                ip_val = ''

            serial_val = clean_val(row.get(col_map.get('serial_no', ''), ''))
            if serial_val == 'None' or serial_val.lower() == 'null':
                serial_val = ''

            # Map or create department
            loc_val = clean_val(row.get(col_map.get('location', ''), ''))
            dept_id = None
            if loc_val and loc_val.lower() != 'none':
                matched_dept = find_match(loc_val, dept_map)
                if matched_dept:
                    dept_id = matched_dept['dept_id']
                else:
                    # Auto-create department
                    dtype = 'HO Division' if is_head_office(loc_val) else 'Branch'
                    if 'sub' in loc_val.lower():
                        dtype = 'Sub-Branch'
                    try:
                        cursor.execute(
                            "INSERT INTO departments (dept_name, dept_type) VALUES (%s, %s)",
                            (loc_val, dtype)
                        )
                        dept_id = cursor.lastrowid
                        conn.commit()
                        new_dept = {'dept_id': dept_id, 'dept_name': loc_val, 'dept_type': dtype}
                        dept_map[loc_val.strip().lower()] = new_dept
                    except Exception:
                        cursor.execute("SELECT dept_id FROM departments WHERE dept_name = %s", (loc_val,))
                        res = cursor.fetchone()
                        if res:
                            dept_id = res[0]

            # Parse other fields
            emp_id = clean_val(row.get(col_map.get('employee_id', ''), ''))
            if emp_id.lower() in ('none', 'null', ''):
                emp_id = None

            emp_name = clean_val(row.get(col_map.get('employee_name', ''), ''))
            position = clean_val(row.get(col_map.get('position', ''), ''))

            brand_model = clean_val(row.get(col_map.get('brand', ''), ''))
            brand = 'Fanvil'
            model = ''
            if brand_model:
                parts = brand_model.split(maxsplit=1)
                brand = parts[0]
                model = parts[1] if len(parts) > 1 else ''

            caller_id = clean_val(row.get(col_map.get('caller_id', ''), ''))

            cfg_raw = clean_val(row.get(col_map.get('configure_status', ''), '')).upper()
            cfg_status = 'Done' if 'DONE' in cfg_raw or 'YES' in cfg_raw or cfg_raw == '1' else 'ON'

            deliv_raw = clean_val(row.get(col_map.get('delivery_status', ''), '')).upper()
            deliv_status = 'Delivered' if 'YES' in deliv_raw or 'DELIVER' in deliv_raw or deliv_raw == '1' else 'Pending'

            status_raw = clean_val(row.get(col_map.get('status', ''), '')).upper()
            status = 'Active' if 'ACTIVE' in status_raw or 'YES' in status_raw or status_raw == '1' else 'Inactive'

            remarks = clean_val(row.get(col_map.get('remarks', ''), ''))
            issue_dt = parse_date(row.get(col_map.get('issue_date', '')))

            # Check if record already exists by extension or serial
            cursor.execute("SELECT phone_id FROM ip_phones WHERE extension = %s", (ext_val,))
            existing = cursor.fetchone()

            if existing:
                # Update existing phone record
                cursor.execute("""
                    UPDATE ip_phones SET
                        dept_id = %s, employee_id = %s, employee_name = %s,
                        issue_date = %s, brand = %s, model = %s,
                        phone_set_serial_no = %s, ip_address = %s,
                        caller_id = %s, position = %s, department = %s,
                        status = %s, delivery_status = %s, configure_status = %s,
                        remarks = %s
                    WHERE extension = %s
                """, (
                    dept_id, emp_id or None, emp_name or None, issue_dt, brand or 'Fanvil', model or None,
                    serial_val or None, ip_val or None, caller_id or None, position or None, loc_val or None,
                    status, deliv_status, cfg_status, remarks or None, ext_val
                ))
                inserted += 1
            else:
                # Insert new phone record
                cursor.execute("""
                    INSERT INTO ip_phones (
                        dept_id, employee_id, employee_name, issue_date,
                        brand, model, phone_set_serial_no, ip_address,
                        extension, caller_id, position, department,
                        status, delivery_status, configure_status, remarks, created_by
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    dept_id, emp_id or None, emp_name or None, issue_dt,
                    brand or 'Fanvil', model or None, serial_val or None, ip_val or None,
                    ext_val, caller_id or None, position or None, loc_val or None,
                    status, deliv_status, cfg_status, remarks or None, created_by
                ))
                inserted += 1

            conn.commit()

        except Exception as e:
            conn.rollback()
            skipped += 1
            errors.append(f"Row {idx}: {str(e)}")

    cursor.close()
    conn.close()

    return inserted, skipped, errors
