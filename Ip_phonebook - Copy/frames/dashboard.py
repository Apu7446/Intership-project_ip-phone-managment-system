"""
Dashboard Frame — SBAC IP Phone Management System
Official SBAC Bank PLC Theme & Metric Summary Cards
Interactive Division & Position Phone Breakdown Tables with click-to-view navigation.
"""

import customtkinter as ctk
from tkinter import ttk
from config import COLORS, setup_treeview_style
import db


class DashboardFrame(ctk.CTkFrame):
    def __init__(self, parent, user, app_ref=None):
        super().__init__(parent, fg_color=COLORS['bg_dark'])
        self.user = user
        self.app_ref = app_ref
        self.build_ui()

    def build_ui(self):
        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(15, 10))

        ctk.CTkLabel(header, text="📊  System Overview & Analytics",
                     font=ctk.CTkFont(size=22, weight="bold"),
                     text_color=COLORS['text_white']).pack(side="left")

        welcome = ctk.CTkLabel(
            header,
            text=f"Welcome back, {self.user['full_name']} ({self.user['role']})",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=COLORS['text_light'])
        welcome.pack(side="right")

        refresh_btn = ctk.CTkButton(
            header, text="⟳ Refresh Stats", width=110, height=34,
            corner_radius=8,
            fg_color=COLORS['primary'], hover_color=COLORS['primary_light'],
            text_color=COLORS['secondary'],
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self.refresh_stats)
        refresh_btn.pack(side="right", padx=(0, 15))

        # Main Scrollable Body
        self.scroll_body = ctk.CTkScrollableFrame(
            self, fg_color="transparent",
            scrollbar_button_color=COLORS['primary'],
            scrollbar_button_hover_color=COLORS['primary_light']
        )
        self.scroll_body.pack(fill="both", expand=True, padx=15, pady=(0, 10))

        self.refresh_stats()

    def refresh_stats(self):
        for widget in self.scroll_body.winfo_children():
            widget.destroy()

        loading_lbl = ctk.CTkLabel(
            self.scroll_body, text="📊 Loading analytics and statistics...",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLORS['secondary']
        )
        loading_lbl.pack(pady=40)

        self._dash_load_gen = getattr(self, '_dash_load_gen', 0) + 1
        current_gen = self._dash_load_gen

        def _bg_fetch():
            try:
                stats = db.get_dashboard_stats()
                div_counts = db.get_division_phone_counts()
                pos_counts = db.get_position_phone_counts()
                err = None
            except Exception as e:
                stats = None
                div_counts = []
                pos_counts = []
                err = e

            if self.winfo_exists():
                self.after(0, lambda: self._on_stats_loaded(current_gen, stats, div_counts, pos_counts, err))

        import threading
        threading.Thread(target=_bg_fetch, daemon=True).start()

    def _on_stats_loaded(self, gen, stats, div_counts, pos_counts, err):
        if not self.winfo_exists() or gen != getattr(self, '_dash_load_gen', 0):
            return

        for widget in self.scroll_body.winfo_children():
            widget.destroy()

        if err or not stats:
            ctk.CTkLabel(self.scroll_body, text=f"Error loading stats: {err}",
                         text_color=COLORS['danger']).pack(pady=20)
            return

        # ── 1. Top Summary Metric Cards ──
        row1 = ctk.CTkFrame(self.scroll_body, fg_color="transparent")
        row1.pack(fill="x", pady=(0, 12))

        cards_row1 = [
            ("📞", "Total IP Phones", stats['total_phones'], COLORS['secondary']),
            ("✅", "Active Phones", stats['active_phones'], COLORS['success']),
            ("⛔", "Inactive Phones", stats['inactive_phones'], COLORS['danger']),
            ("📦", "Delivered Devices", stats['delivered'], COLORS['info']),
        ]
        for icon, title, value, color in cards_row1:
            self._create_card(row1, icon, title, value, color)

        row2 = ctk.CTkFrame(self.scroll_body, fg_color="transparent")
        row2.pack(fill="x", pady=(0, 15))

        cards_row2 = [
            ("⏳", "Pending Delivery", stats['pending'], COLORS['warning']),
            ("🏢", "Active Branches", stats['total_branches'], COLORS['secondary']),
            ("🏛️", "HO Divisions", stats['total_divisions'], '#BA68C8'),
            ("📍", "Branch Telephones", stats['branch_phones'], '#64B5F6'),
        ]
        for icon, title, value, color in cards_row2:
            self._create_card(row2, icon, title, value, color)

        # ── 2. Interactive Division & Position Breakdown Tables ──
        tables_row = ctk.CTkFrame(self.scroll_body, fg_color="transparent")
        tables_row.pack(fill="both", expand=True, pady=(5, 10))

        # Setup Treeview Style
        setup_treeview_style()

        # --- Left Section: Division Breakdown ---
        div_frame = ctk.CTkFrame(tables_row, fg_color=COLORS['bg_card'], corner_radius=14,
                                 border_width=1, border_color=COLORS['border'])
        div_frame.pack(side="left", fill="both", expand=True, padx=(0, 8))

        div_header = ctk.CTkFrame(div_frame, fg_color="transparent")
        div_header.pack(fill="x", padx=15, pady=(12, 6))

        ctk.CTkLabel(div_header, text="🏛️  HO Division Phone Breakdown",
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=COLORS['secondary']).pack(side="left")

        ctk.CTkLabel(div_header, text="💡 Double-click to view division phones",
                     font=ctk.CTkFont(size=10),
                     text_color=COLORS['text_muted']).pack(side="right")

        div_tree_container = ctk.CTkFrame(div_frame, fg_color="transparent")
        div_tree_container.pack(fill="both", expand=True, padx=10, pady=(0, 12))

        div_columns = ("id", "name", "total", "active")
        self.div_tree = ttk.Treeview(div_tree_container, columns=div_columns, show="headings", height=8, selectmode="browse")

        self.div_tree.heading("id", text="ID")
        self.div_tree.heading("name", text="Division Name")
        self.div_tree.heading("total", text="Total Phones")
        self.div_tree.heading("active", text="Active")

        self.div_tree.column("id", width=45, anchor="center")
        self.div_tree.column("name", width=220, anchor="w")
        self.div_tree.column("total", width=90, anchor="center")
        self.div_tree.column("active", width=75, anchor="center")

        div_scrollbar = ttk.Scrollbar(div_tree_container, orient="vertical", command=self.div_tree.yview)
        self.div_tree.configure(yscrollcommand=div_scrollbar.set)

        self.div_tree.pack(side="left", fill="both", expand=True)
        div_scrollbar.pack(side="right", fill="y")

        self.div_tree.bind("<Double-1>", lambda e: self._on_division_double_click())

        for d in div_counts:
            self.div_tree.insert("", "end", values=(
                d['division_id'], d['division_name'], d['total_phones'], d['active_phones']
            ))

        # --- Right Section: Position Breakdown ---
        pos_frame = ctk.CTkFrame(tables_row, fg_color=COLORS['bg_card'], corner_radius=14,
                                 border_width=1, border_color=COLORS['border'])
        pos_frame.pack(side="right", fill="both", expand=True, padx=(8, 0))

        pos_header = ctk.CTkFrame(pos_frame, fg_color="transparent")
        pos_header.pack(fill="x", padx=15, pady=(12, 6))

        ctk.CTkLabel(pos_header, text="💼  Position / Designation Breakdown",
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=COLORS['secondary']).pack(side="left")

        ctk.CTkLabel(pos_header, text="💡 Double-click to filter phonebook",
                     font=ctk.CTkFont(size=10),
                     text_color=COLORS['text_muted']).pack(side="right")

        pos_tree_container = ctk.CTkFrame(pos_frame, fg_color="transparent")
        pos_tree_container.pack(fill="both", expand=True, padx=10, pady=(0, 12))

        pos_columns = ("position", "total", "active")
        self.pos_tree = ttk.Treeview(pos_tree_container, columns=pos_columns, show="headings", height=8, selectmode="browse")

        self.pos_tree.heading("position", text="Position / Designation")
        self.pos_tree.heading("total", text="Total Phones")
        self.pos_tree.heading("active", text="Active")

        self.pos_tree.column("position", width=250, anchor="w")
        self.pos_tree.column("total", width=90, anchor="center")
        self.pos_tree.column("active", width=75, anchor="center")

        pos_scrollbar = ttk.Scrollbar(pos_tree_container, orient="vertical", command=self.pos_tree.yview)
        self.pos_tree.configure(yscrollcommand=pos_scrollbar.set)

        self.pos_tree.pack(side="left", fill="both", expand=True)
        pos_scrollbar.pack(side="right", fill="y")

        self.pos_tree.bind("<Double-1>", lambda e: self._on_position_double_click())

        for p in pos_counts:
            self.pos_tree.insert("", "end", values=(
                p['position_name'], p['total_phones'], p['active_phones']
            ))

    def _create_card(self, parent, icon, title, value, val_color):
        card = ctk.CTkFrame(
            parent, fg_color=COLORS['bg_card'], corner_radius=14,
            border_width=1, border_color=COLORS['border']
        )
        card.pack(side="left", fill="both", expand=True, padx=6)

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(padx=14, pady=12, fill="both")

        ctk.CTkLabel(inner, text=f"{icon} {title}",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=COLORS['text_muted']).pack(anchor="w")

        ctk.CTkLabel(inner, text=str(value),
                     font=ctk.CTkFont(size=26, weight="bold"),
                     text_color=val_color).pack(anchor="w", pady=(4, 0))

    def _on_division_double_click(self):
        selected = self.div_tree.selection()
        if selected and self.app_ref:
            item = self.div_tree.item(selected[0])
            values = item['values']
            div_id = values[0]
            div_name = values[1]
            self.app_ref.show_location_detail("HO Division", div_id, div_name)

    def _on_position_double_click(self):
        selected = self.pos_tree.selection()
        if selected and self.app_ref:
            item = self.pos_tree.item(selected[0])
            values = item['values']
            pos_name = values[0]
            if self.app_ref.current_frame:
                self.app_ref.show_frame("phones")
                if hasattr(self.app_ref.current_frame, 'search_by_var'):
                    self.app_ref.current_frame.search_by_var.set("Position")
                    self.app_ref.current_frame.search_var.set(pos_name)
                    self.app_ref.current_frame.load_data()
