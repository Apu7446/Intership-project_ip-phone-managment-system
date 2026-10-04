"""
SBAC IP Phone Management System — Smart Form History & Auto-Suggestion Manager
Acts as a local persistent memory / desktop cookie for frequently entered values.
Tracks compact top 4-5 most-used Models, Brands, Designations, Recent Locations, Caller IDs, Employee data, and Serial Numbers.
"""

import os
import json
import db

HISTORY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".form_history.json")


def load_history():
    """Load history from file, or initialize from database frequency counts."""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if data and isinstance(data, dict):
                    return data
        except Exception:
            pass

    return _build_initial_history()


def _build_initial_history():
    """Scan existing database to populate frequent models, brands, positions, serials, etc."""
    history = {
        "models": {},
        "brands": {},
        "positions": {},
        "departments": [],
        "caller_ids": [],
        "employee_names": [],
        "employee_ids": [],
        "serial_numbers": [],
        "last_entry": {}
    }
    try:
        conn = db.get_connection()
        if conn:
            cursor = conn.cursor(dictionary=True)

            # Top models from ip_phones
            cursor.execute(
                "SELECT model, COUNT(*) as cnt FROM ip_phones "
                "WHERE model IS NOT NULL AND model != '' AND model != 'None' "
                "GROUP BY model ORDER BY cnt DESC LIMIT 10"
            )
            for r in cursor.fetchall():
                if r['model']:
                    history["models"][r['model'].strip()] = r['cnt']

            # Top brands from ip_phones
            cursor.execute(
                "SELECT brand, COUNT(*) as cnt FROM ip_phones "
                "WHERE brand IS NOT NULL AND brand != '' AND brand != 'None' "
                "GROUP BY brand ORDER BY cnt DESC LIMIT 10"
            )
            for r in cursor.fetchall():
                if r['brand']:
                    history["brands"][r['brand'].strip()] = r['cnt']

            # Top positions from ip_phones
            cursor.execute(
                "SELECT position, COUNT(*) as cnt FROM ip_phones "
                "WHERE position IS NOT NULL AND position != '' AND position != 'None' "
                "GROUP BY position ORDER BY cnt DESC LIMIT 10"
            )
            for r in cursor.fetchall():
                if r['position']:
                    history["positions"][r['position'].strip()] = r['cnt']

            # Recent departments from ip_phones
            cursor.execute(
                "SELECT department, COUNT(*) as cnt FROM ip_phones "
                "WHERE department IS NOT NULL AND department != '' AND department != 'None' "
                "GROUP BY department ORDER BY cnt DESC LIMIT 10"
            )
            for r in cursor.fetchall():
                if r['department'] and r['department'].strip() not in history["departments"]:
                    history["departments"].append(r['department'].strip())

            # Recent caller IDs from ip_phones
            cursor.execute(
                "SELECT caller_id, COUNT(*) as cnt FROM ip_phones "
                "WHERE caller_id IS NOT NULL AND caller_id != '' AND caller_id != 'None' "
                "GROUP BY caller_id ORDER BY cnt DESC LIMIT 10"
            )
            for r in cursor.fetchall():
                if r['caller_id'] and r['caller_id'].strip() not in history["caller_ids"]:
                    history["caller_ids"].append(r['caller_id'].strip())

            # Recent employee names
            cursor.execute(
                "SELECT employee_name FROM ip_phones "
                "WHERE employee_name IS NOT NULL AND employee_name != '' AND employee_name != 'None' "
                "ORDER BY phone_id DESC LIMIT 10"
            )
            for r in cursor.fetchall():
                if r['employee_name'] and r['employee_name'].strip() not in history["employee_names"]:
                    history["employee_names"].append(r['employee_name'].strip())

            # Recent employee IDs
            cursor.execute(
                "SELECT employee_id FROM ip_phones "
                "WHERE employee_id IS NOT NULL AND employee_id != '' AND employee_id != 'None' "
                "ORDER BY phone_id DESC LIMIT 10"
            )
            for r in cursor.fetchall():
                if r['employee_id'] and r['employee_id'].strip() not in history["employee_ids"]:
                    history["employee_ids"].append(r['employee_id'].strip())

            # Recent phone set serial numbers
            cursor.execute(
                "SELECT phone_set_serial_no FROM ip_phones "
                "WHERE phone_set_serial_no IS NOT NULL AND phone_set_serial_no != '' AND phone_set_serial_no != 'None' "
                "ORDER BY phone_id DESC LIMIT 10"
            )
            for r in cursor.fetchall():
                if r['phone_set_serial_no'] and r['phone_set_serial_no'].strip() not in history["serial_numbers"]:
                    history["serial_numbers"].append(r['phone_set_serial_no'].strip())

            cursor.close()
            conn.close()
    except Exception:
        pass

    save_history(history)
    return history


def save_history(history_data):
    """Save history dict to JSON file."""
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history_data, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


def record_phone_entry(payload):
    """Update frequency counts and save the last entered phone record."""
    history = load_history()

    def _is_valid(v):
        return v is not None and str(v).strip() != '' and str(v).strip().lower() not in ('none', 'null', 'select location')

    # Record model
    model = payload.get('model')
    if _is_valid(model):
        model_str = str(model).strip()
        history['models'][model_str] = history['models'].get(model_str, 0) + 1

    # Record brand
    brand = payload.get('brand')
    if _is_valid(brand):
        brand_str = str(brand).strip()
        history['brands'][brand_str] = history['brands'].get(brand_str, 0) + 1

    # Record position
    pos = payload.get('position')
    if _is_valid(pos):
        pos_str = str(pos).strip()
        history['positions'][pos_str] = history['positions'].get(pos_str, 0) + 1

    # Record department in recent list
    dept = payload.get('department')
    if _is_valid(dept):
        dept_str = str(dept).strip()
        depts = [d for d in history.get('departments', []) if d != dept_str]
        depts.insert(0, dept_str)
        history['departments'] = depts[:10]

    # Record caller_id in recent list
    caller = payload.get('caller_id')
    if _is_valid(caller):
        caller_str = str(caller).strip()
        callers = [c for c in history.get('caller_ids', []) if c != caller_str]
        callers.insert(0, caller_str)
        history['caller_ids'] = callers[:10]

    # Record employee name in recent list
    emp_name = payload.get('employee_name')
    if _is_valid(emp_name):
        emp_name_str = str(emp_name).strip()
        names = [n for n in history.get('employee_names', []) if n != emp_name_str]
        names.insert(0, emp_name_str)
        history['employee_names'] = names[:10]

    # Record employee id in recent list
    emp_id = payload.get('employee_id')
    if _is_valid(emp_id):
        emp_id_str = str(emp_id).strip()
        ids = [i for i in history.get('employee_ids', []) if i != emp_id_str]
        ids.insert(0, emp_id_str)
        history['employee_ids'] = ids[:10]

    # Record phone set serial no in recent list
    serial = payload.get('phone_set_serial_no')
    if _is_valid(serial):
        serial_str = str(serial).strip()
        serials = [s for s in history.get('serial_numbers', []) if s != serial_str]
        serials.insert(0, serial_str)
        history['serial_numbers'] = serials[:10]

    # Record extension in recent list
    ext = payload.get('extension')
    if _is_valid(ext):
        ext_str = str(ext).strip()
        exts = [e for e in history.get('extensions', []) if e != ext_str]
        exts.insert(0, ext_str)
        history['extensions'] = exts[:15]

    # Save last entry for quick fill
    history['last_entry'] = {
        'dept_id': payload.get('dept_id'),
        'department': payload.get('department'),
        'brand': payload.get('brand'),
        'model': payload.get('model'),
        'position': payload.get('position'),
        'status': payload.get('status'),
        'delivery_status': payload.get('delivery_status'),
        'configure_status': payload.get('configure_status'),
    }

    save_history(history)


def get_top_models(limit=4):
    """Returns compact top 4 frequent models list."""
    history = load_history()
    models = sorted(history.get('models', {}).items(), key=lambda x: x[1], reverse=True)
    results = [m[0] for m in models[:limit]]
    if not results:
        results = ["X303", "V50P", "X303P", "X303G"]
    return results[:limit]


def get_recent_extensions(dept_name=None, limit=8):
    """Returns 3-digit prefix suggestions and frequent extensions based on location or global history."""
    history = load_history()
    recent = history.get('extensions', [])
    candidates = []

    # If department is provided, check database for extensions in this department
    if dept_name and str(dept_name).strip().lower() not in ('none', 'null', '', 'select location', 'type or click select...'):
        try:
            conn = db.get_connection()
            if conn:
                cursor = conn.cursor(dictionary=True)
                cursor.execute(
                    "SELECT DISTINCT extension FROM ip_phones WHERE (department = %s OR dept_id IN (SELECT dept_id FROM departments WHERE dept_name = %s)) AND extension IS NOT NULL AND extension != '' AND extension != 'None'",
                    (dept_name, dept_name)
                )
                dept_exts = [r['extension'].strip() for r in cursor.fetchall() if r.get('extension')]
                cursor.close()
                conn.close()

                # Extract 3-digit prefixes from this department first
                for ext in dept_exts:
                    if len(ext) >= 3:
                        p3 = ext[:3]
                        if p3 not in candidates:
                            candidates.append(p3)
                for ext in dept_exts:
                    if ext not in candidates:
                        candidates.append(ext)
        except Exception:
            pass

    # Add all unique 3-digit prefixes from recent history
    for ext in recent:
        ext_str = str(ext).strip()
        if len(ext_str) >= 3:
            p3 = ext_str[:3]
            if p3 not in candidates:
                candidates.append(p3)

    # Add full recent extensions
    for ext in recent:
        ext_str = str(ext).strip()
        if ext_str and ext_str not in candidates:
            candidates.append(ext_str)

    # Fallback to query all extensions from DB if candidate list is small
    if len(candidates) < 5:
        try:
            conn = db.get_connection()
            if conn:
                cursor = conn.cursor(dictionary=True)
                cursor.execute(
                    "SELECT DISTINCT extension FROM ip_phones WHERE extension IS NOT NULL AND extension != '' AND extension != 'None' ORDER BY extension LIMIT 30"
                )
                for r in cursor.fetchall():
                    e = str(r['extension']).strip()
                    if len(e) >= 3:
                        p3 = e[:3]
                        if p3 not in candidates:
                            candidates.append(p3)
                    if e not in candidates:
                        candidates.append(e)
                cursor.close()
                conn.close()
        except Exception:
            pass

    return candidates[:limit]


def get_recent_caller_ids(limit=4):
    """Returns compact top 4 recent caller IDs."""
    history = load_history()
    return history.get('caller_ids', [])[:limit]


def get_recent_employee_names(limit=4):
    """Returns compact top 4 recent employee names."""
    history = load_history()
    return history.get('employee_names', [])[:limit]


def get_recent_employee_ids(limit=4):
    """Returns compact top 4 recent employee IDs."""
    history = load_history()
    return history.get('employee_ids', [])[:limit]


def get_recent_serial_numbers(limit=5):
    """Returns compact smart serial suggestions including standard bank prefixes (Q7D223A00, UPD025800) and recent entries."""
    history = load_history()
    recent = history.get('serial_numbers', [])

    common_prefixes = ["Q7D223A00", "UPD025800"]
    suggestions = []

    for p in common_prefixes:
        if p not in suggestions:
            suggestions.append(p)

    for s in recent:
        if s and s != "None" and s not in suggestions:
            suggestions.append(s)

    return suggestions[:limit]


def get_recent_departments(limit=4):
    """Returns compact top 4 recent departments."""
    history = load_history()
    return history.get('departments', [])[:limit]


def get_last_entry():
    """Returns the last entered phone record dict."""
    history = load_history()
    return history.get('last_entry', {})
