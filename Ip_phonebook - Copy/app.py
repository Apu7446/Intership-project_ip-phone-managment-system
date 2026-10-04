"""
SBAC IP Phone Management System — Main Application Window
Sidebar navigation + Frame switching logic (Official SBAC Bank Theme).
"""

import customtkinter as ctk
from config import COLORS, DB_CONFIG
from frames.dashboard import DashboardFrame
from frames.phones import PhonesFrame
from frames.departments import DepartmentsFrame
from frames.users import UsersFrame
from frames.location_detail import LocationDetailFrame
from frames.backup import BackupFrame
from backup_manager import check_and_run_startup_auto_backup


class MainApp(ctk.CTkFrame):
    def __init__(self, parent, user, on_logout):
        super().__init__(parent, fg_color=COLORS['bg_dark'])
        self.parent = parent
        self.user = user
        self.on_logout = on_logout
        self.current_frame = None
        self.nav_buttons = {}

        # Run background daily auto-backup check on startup (silent & non-blocking)
        if self.user.get('role') == 'Admin':
            check_and_run_startup_auto_backup()

        self.build_ui()
        self.show_frame("dashboard")

    def build_ui(self):
        # ── Compact Sidebar Container ──
        sidebar = ctk.CTkFrame(self, fg_color=COLORS['bg_sidebar'], width=210, corner_radius=0)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        # Brand Header Card
        brand_card = ctk.CTkFrame(sidebar, fg_color=COLORS['primary_dark'], corner_radius=14,
                                  border_width=1, border_color=COLORS['border'])
        brand_card.pack(fill="x", padx=10, pady=(12, 8))

        logo_sub = ctk.CTkFrame(brand_card, fg_color="transparent")
        logo_sub.pack(pady=10)

        ctk.CTkLabel(logo_sub, text="🏛", font=ctk.CTkFont(family="Segoe UI", size=26, weight="bold"),
                     text_color=COLORS['secondary']).pack()
        ctk.CTkLabel(logo_sub, text="SBAC BANK",
                     font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
                     text_color=COLORS['text_white']).pack(pady=(2, 0))

        # Gold tag badge
        badge = ctk.CTkFrame(logo_sub, fg_color=COLORS['secondary'], corner_radius=8)
        badge.pack(pady=(4, 0))
        ctk.CTkLabel(badge, text=" IP PHONE PORTAL ",
                     font=ctk.CTkFont(family="Segoe UI", size=9, weight="bold"),
                     text_color="#000000").pack(padx=6, pady=2)

        ctk.CTkFrame(sidebar, fg_color=COLORS['border'], height=1).pack(fill="x", padx=10, pady=6)

        # Nav items
        nav_items = [
            ("dashboard", "📊  Dashboard"),
            ("phones", "📞  IP Phonebook"),
            ("departments", "🏢  Departments"),
        ]

        if self.user.get('role') == 'Admin':
            nav_items.append(("users", "👤  User Management"))
            nav_items.append(("backup", "💾  Database Backup"))

        for key, text in nav_items:
            btn = ctk.CTkButton(
                sidebar, text=text, height=42, anchor="w",
                corner_radius=21,
                fg_color="transparent",
                hover_color=COLORS['primary_light'],
                text_color=COLORS['text_light'],
                font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                command=lambda k=key: self.show_frame(k))
            btn.pack(fill="x", padx=10, pady=3)
            self.nav_buttons[key] = btn

        # Ping Tool Button with Gold accent
        ping_btn = ctk.CTkButton(
            sidebar, text="🌐  IP Ping Tool", height=42, anchor="w",
            corner_radius=21,
            fg_color="transparent",
            hover_color=COLORS['primary_light'],
            text_color=COLORS['secondary'],
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            command=self.open_ping_dialog)
        ping_btn.pack(fill="x", padx=10, pady=3)

        # Bottom User Profile & Logout
        bottom = ctk.CTkFrame(sidebar, fg_color=COLORS['primary_dark'], corner_radius=12,
                              border_width=1, border_color=COLORS['border'])
        bottom.pack(side="bottom", fill="x", padx=10, pady=12)

        user_info = ctk.CTkFrame(bottom, fg_color="transparent")
        user_info.pack(fill="x", padx=10, pady=(8, 4))

        ctk.CTkLabel(user_info, text=f"👤 {self.user['full_name']}",
                     font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                     text_color=COLORS['text_white']).pack(anchor="w")

        role_color = COLORS['secondary'] if self.user['role'] == 'Admin' else COLORS['text_muted']
        ctk.CTkLabel(user_info, text=f"Role: {self.user['role']}",
                     font=ctk.CTkFont(family="Segoe UI", size=11),
                     text_color=role_color).pack(anchor="w")

        # Server IP status button
        self.server_status_btn = ctk.CTkButton(
            bottom, text=f"🌐 Host: {DB_CONFIG.get('host', 'localhost')}", height=26,
            corner_radius=8, fg_color="transparent", hover_color=COLORS['primary'],
            text_color=COLORS['text_muted'],
            font=ctk.CTkFont(family="Segoe UI", size=10),
            command=self.open_server_dialog
        )
        self.server_status_btn.pack(fill="x", padx=8, pady=(2, 2))

        logout_btn = ctk.CTkButton(
            bottom, text="🚪 Logout System", height=34,
            corner_radius=17,
            fg_color=COLORS['danger'], hover_color="#D32F2F",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            command=self.on_logout)
        logout_btn.pack(fill="x", padx=8, pady=(2, 8))

        # Content Container
        self.content_area = ctk.CTkFrame(self, fg_color=COLORS['bg_dark'], corner_radius=0)
        self.content_area.pack(side="right", fill="both", expand=True)

    def open_server_dialog(self):
        from frames.login import ServerConfigDialog
        ServerConfigDialog(self.parent, on_saved=self.update_server_display)

    def update_server_display(self):
        if hasattr(self, 'server_status_btn') and self.server_status_btn.winfo_exists():
            self.server_status_btn.configure(text=f"🌐 Host: {DB_CONFIG.get('host', 'localhost')}")

    def show_frame(self, name):
        for key, btn in self.nav_buttons.items():
            if key == name:
                btn.configure(fg_color=COLORS['active_pill_bg'], text_color=COLORS['active_pill_fg'])
            else:
                btn.configure(fg_color="transparent", text_color=COLORS['text_light'])

        if self.current_frame:
            self.current_frame.destroy()

        frames_map = {
            "dashboard": lambda parent, user: DashboardFrame(parent, user, app_ref=self),
            "phones": lambda parent, user: PhonesFrame(parent, user),
            "departments": lambda parent, user: DepartmentsFrame(parent, user, app_ref=self),
            "users": lambda parent, user: UsersFrame(parent, user),
            "backup": lambda parent, user: BackupFrame(parent, user, app_ref=self),
        }

        frame_factory = frames_map.get(name)
        if frame_factory:
            self.current_frame = frame_factory(self.content_area, self.user)
            self.current_frame.pack(fill="both", expand=True)

    def show_location_detail(self, location_type, location_id, location_name):
        """Navigate to detail view for a specific department/location."""
        for key, btn in self.nav_buttons.items():
            if key == "departments":
                btn.configure(fg_color=COLORS['active_pill_bg'], text_color=COLORS['active_pill_fg'])
            else:
                btn.configure(fg_color="transparent", text_color=COLORS['text_light'])

        if self.current_frame:
            self.current_frame.destroy()

        self.current_frame = LocationDetailFrame(
            self.content_area, self.user,
            location_type=location_type,
            location_id=location_id,
            location_name=location_name,
            on_back=lambda: self.show_frame("departments")
        )
        self.current_frame.pack(fill="both", expand=True)

    def open_ping_dialog(self):
        from ip_tool import open_ip_tool
        open_ip_tool(self)
