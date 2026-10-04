"""
SBAC IP Phone Management System — Configuration Settings
Exact SBAC Bank PLC Official Palette (Extracted from sbacbank.com)
"""

import os
import json

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "server_config.json")

# Database Configuration (Set 'host' to Server PC IP like '172.19.100.X' for multi-PC use)
DB_CONFIG = {
    'host': os.environ.get('SBAC_DB_HOST', '172.19.100.32'),
    'user': os.environ.get('SBAC_DB_USER', 'root'),
    'password': os.environ.get('SBAC_DB_PASS', ''),
    'database': 'sbac_ipphone',
    'port': int(os.environ.get('SBAC_DB_PORT', 3306)),
    'connect_timeout': 3,
    'use_pure': True
}

def load_server_config():
    """Load persistent server configuration from server_config.json if present."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                saved = json.load(f)
                if 'host' in saved and saved['host']:
                    DB_CONFIG['host'] = saved['host']
                if 'port' in saved and saved['port']:
                    DB_CONFIG['port'] = int(saved['port'])
                if 'user' in saved:
                    DB_CONFIG['user'] = saved['user']
                if 'password' in saved:
                    DB_CONFIG['password'] = saved['password']
                if 'database' in saved and saved['database']:
                    DB_CONFIG['database'] = saved['database']
        except Exception as e:
            print(f"[WARN] Could not load server_config.json: {e}")

def save_server_config(host, port=3306, user='root', password='', database='sbac_ipphone'):
    """Save server connection configuration persistently to server_config.json."""
    DB_CONFIG['host'] = host.strip()
    DB_CONFIG['port'] = int(port)
    DB_CONFIG['user'] = user.strip()
    DB_CONFIG['password'] = password
    DB_CONFIG['database'] = database.strip()
    try:
        import db
        if hasattr(db, 'reset_connection_pool'):
            db.reset_connection_pool()
    except Exception:
        pass
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump({
                'host': DB_CONFIG['host'],
                'port': DB_CONFIG['port'],
                'user': DB_CONFIG['user'],
                'password': DB_CONFIG['password'],
                'database': DB_CONFIG['database']
            }, f, indent=4)
        return True
    except Exception as e:
        print(f"[ERROR] Failed to save server config: {e}")
        return False

# Initialize configuration on load
load_server_config()

# Real-Time Multi-PC Live Auto-Sync Interval (Milliseconds)
AUTO_SYNC_INTERVAL_MS = 6000  # 6 Seconds

# Application Metadata
APP_TITLE = "SBAC Bank PLC — IP Phone Management System"
APP_VERSION = "3.1.0"
APP_SIZE = "1240x750"

# Color Palette (Exact SBAC Bank PLC Web Theme)
COLORS = {
    'primary': '#85175F',         # SBAC Official Magenta-Purple
    'primary_light': '#A01F74',   # Lighter Purple
    'primary_dark': '#620E42',    # Darker Purple
    'secondary': '#F8A51D',       # SBAC Gold / S-Flame Yellow
    'secondary_hover': '#E09212', # Hover state for Gold
    'bg_dark': '#180E1A',         # Midnight Plum Deep Dark BG
    'bg_card': '#251528',         # Card Container Background
    'bg_sidebar': '#2A1227',      # SBAC Deep Purple Sidebar
    'text_white': '#FFFFFF',      # Primary White Text
    'text_light': '#F3E5F5',      # Soft Lilac Light Text
    'text_muted': '#C2A3C7',      # Muted Lavender Text
    'success': '#00E676',         # Green Status
    'warning': '#F8A51D',         # SBAC Gold Warning
    'danger': '#FF5252',          # Bright Coral Red
    'info': '#40C4FF',            # Sky Blue Info
    'border': '#4A2548',          # Card Border Color
    'entry_bg': '#331B34',        # Input Field Background
    'active_pill_bg': '#FFFFFF',  # Active White Pill Tab Background
    'active_pill_fg': '#85175F',  # Active Purple Text for Pill Tabs
}

# Master Options
BRANDS = ['Fanvil', 'Fortinet', 'Cisco', 'Yealink', 'Grandstream', 'Other']
POSITIONS = [
    'Manager',
    'Operation Manager',
    'In charge Cash',
    'Front Desk',
    'Clearing',
    'In charge GB(General Banking)',
    'In charge TF(Trade Finance) Import',
    'In charge TF(Trade Finance) Export',
    'Remittance',
    'Sub-Br In charge',
    'Sub-Br_Credit',
    'Sub-Br_GB',
    'Sub-Br_Cash',
    'Executive',
    'IT',
    'Staff',
    'Other'
]
STATUS_OPTIONS = ['Active', 'Inactive']
DELIVERY_OPTIONS = ['Delivered', 'Pending']
CONFIGURE_OPTIONS = ['Done', 'ON']


def setup_treeview_style():
    """Apply global SBAC dark theme styling to all ttk.Treeview tables with visible cell box borders."""
    from tkinter import ttk
    style = ttk.Style()
    style.theme_use("clam")
    
    grid_col = '#A83E82'   # Bright Magenta crisp cell border gridline
    border_col = '#A83E82'  # Matching border color

    style.configure(
        "Treeview",
        background="#1E1020",
        foreground="#F3E5F5",
        fieldbackground="#1E1020",
        borderwidth=1,
        relief="solid",
        gridcolor=grid_col,
        lightcolor=grid_col,
        darkcolor=grid_col,
        bordercolor=border_col,
        rowheight=36,
        font=('Segoe UI', 11)
    )

    style.configure(
        "Treeview.Heading",
        background=COLORS['primary'],
        foreground="white",
        relief="solid",
        borderwidth=1,
        lightcolor=grid_col,
        darkcolor=grid_col,
        bordercolor=border_col,
        rowheight=38,
        padding=(6, 4),
        font=('Segoe UI', 11, 'bold')
    )
    style.map(
        "Treeview",
        background=[("selected", COLORS['primary_light'])],
        foreground=[("selected", "#FFFFFF")]
    )
    style.map(
        "Treeview.Heading",
        background=[("active", COLORS['primary_light'])],
        relief=[("active", "solid")]
    )
