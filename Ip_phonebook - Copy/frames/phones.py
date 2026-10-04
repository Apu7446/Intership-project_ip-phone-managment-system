"""
IP Phones Frame — SBAC IP Phone Management System
High-Performance Directory View: Instant Search, Radio Category Filters,
Fast Table View (ttk.Treeview) & Box Card Grid View, Add, Edit, Delete, Excel Export, Data Import, IP Ping.
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox
from config import COLORS, BRANDS, POSITIONS, setup_treeview_style
import db
import form_history
from autocomplete import LiveAutocomplete


class PhonesFrame(ctk.CTkFrame):
    TABLE_HEADERS = {
        "sl": ("SL", 55, "center"),
        "ip": ("IP Address", 140, "center"),
        "ext": ("Extension", 95, "center"),
        "caller_id": ("Caller ID", 105, "center"),
        "emp_id": ("Emp ID", 95, "center"),
        "serial": ("Phone Set Serial No", 175, "center"),
        "name": ("Employee Name", 230, "w"),
        "position": ("Position / Designation", 210, "w"),
        "dept": ("Department / Location", 230, "w"),
        "brand_model": ("Brand & Model", 140, "center"),
        "status": ("Active Status", 125, "center"),
        "delivery": ("Deliver Status", 125, "center"),
        "config": ("Config Status", 115, "center"),
        "actions": ("Action", 95, "center")
    }

    def __init__(self, parent, user, initial_search="", initial_search_by="All Fields"):
        super().__init__(parent, fg_color=COLORS['bg_dark'])
        self.user = user
        self.departments = []
        self._search_timer = None
        self.view_mode = "table"  # "table" or "grid"
        self.id_sort_asc = True
        self.sort_col = "sl"
        self.sort_reverse = False
        self.current_phones_data = []
        self.grid_page = 1
        self.grid_page_size = 24
        self.grid_page_size_var = ctk.StringVar(value="24 / page")
        self._last_data_sig = None
        self._sync_timer = None

        self.build_ui()
        if initial_search:
            self.search_var.set(initial_search)
            if initial_search_by:
                self.search_by_var.set(initial_search_by)
        self.load_dropdowns()
        self.load_data()
        self.bind("<Destroy>", self._on_destroy)
        self._start_auto_sync()

    def build_ui(self):
        # ── Header ──
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(15, 8))

        ctk.CTkLabel(header, text="📞  IP Phonebook Directory",
                     font=ctk.CTkFont(size=22, weight="bold"),
                     text_color=COLORS['text_white']).pack(side="left")

        import_btn = ctk.CTkButton(
            header, text="📤 Import Data", width=115, height=36,
            corner_radius=18,
            fg_color=COLORS['primary_dark'], hover_color=COLORS['primary'],
            border_width=1, border_color=COLORS['border'],
            text_color=COLORS['text_light'],
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self.import_data_file)
        import_btn.pack(side="right", padx=(8, 0))

        export_btn = ctk.CTkButton(
            header, text="📥 Export Excel", width=115, height=36,
            corner_radius=18,
            fg_color=COLORS['primary_dark'], hover_color=COLORS['primary'],
            border_width=1, border_color=COLORS['border'],
            text_color=COLORS['text_light'],
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self.export_excel)
        export_btn.pack(side="right", padx=(8, 0))

        ping_btn = ctk.CTkButton(
            header, text="🌐 Ping Tool", width=105, height=36,
            corner_radius=18,
            fg_color=COLORS['primary_dark'], hover_color=COLORS['primary'],
            border_width=1, border_color=COLORS['secondary'],
            text_color=COLORS['secondary'],
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self.open_ping_tool)
        ping_btn.pack(side="right", padx=(8, 0))

        add_btn = ctk.CTkButton(
            header, text="➕ Add Phone", width=125, height=36,
            corner_radius=18,
            fg_color=COLORS['primary'], hover_color=COLORS['primary_light'],
            text_color=COLORS['text_white'],
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self.show_add_form)
        add_btn.pack(side="right")

        # ── Search & Radio Category Filter Card ──
        filter_frame = ctk.CTkFrame(self, fg_color=COLORS['bg_card'], corner_radius=14,
                                    border_width=1, border_color=COLORS['border'])
        filter_frame.pack(fill="x", padx=20, pady=(0, 10))

        # Row 1: Radio buttons for location category filtering
        radio_row = ctk.CTkFrame(filter_frame, fg_color="transparent")
        radio_row.pack(fill="x", padx=15, pady=(12, 6))

        ctk.CTkLabel(radio_row, text="📍 Category Filter:",
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=COLORS['secondary']).pack(side="left", padx=(0, 12))

        self.loc_type_var = ctk.StringVar(value="All")
        categories = [
            ("All", "All Categories"),
            ("HO Division", "Head Office Division"),
            ("Branch", "Branch"),
            ("Sub-Branch", "Sub-Branch")
        ]

        for val, label in categories:
            ctk.CTkRadioButton(
                radio_row, text=label,
                variable=self.loc_type_var, value=val,
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=COLORS['text_light'],
                fg_color=COLORS['primary'],
                hover_color=COLORS['primary_light'],
                radiobutton_width=18, radiobutton_height=18,
                command=self.on_location_type_change
            ).pack(side="left", padx=(0, 16))

        # Divider line
        ctk.CTkFrame(filter_frame, fg_color=COLORS['border'], height=1).pack(fill="x", padx=15, pady=2)

        # Row 2: Search Bar with Search By dropdown + Dropdown Filters
        filter_row = ctk.CTkFrame(filter_frame, fg_color="transparent")
        filter_row.pack(fill="x", padx=15, pady=(4, 12))

        ctk.CTkLabel(filter_row, text="Search By:", font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=COLORS['text_light']).pack(side="left", padx=(0, 5))

        self.search_by_var = ctk.StringVar(value="All Fields")
        self.search_by_combo = ctk.CTkComboBox(
            filter_row,
            values=["All Fields", "Employee Name", "IP Address", "Extension", "Caller ID", "Emp ID", "Serial No", "Location", "Designation"],
            variable=self.search_by_var, width=140, height=36, corner_radius=8,
            fg_color=COLORS['entry_bg'], border_color=COLORS['border'],
            text_color=COLORS['text_white'], button_color=COLORS['primary'],
            dropdown_fg_color=COLORS['bg_card'],
            font=ctk.CTkFont(size=12),
            command=lambda e: self.load_data()
        )
        self.search_by_combo.pack(side="left", padx=(0, 8))

        # Search Entry with live debounced typing
        self.search_var = ctk.StringVar()
        self.search_entry = ctk.CTkEntry(
            filter_row, textvariable=self.search_var,
            placeholder_text="🔍  Type keyword to filter directory in real time...",
            placeholder_text_color=COLORS['text_muted'],
            height=36, width=280, corner_radius=8,
            fg_color=COLORS['entry_bg'], border_color=COLORS['border'],
            text_color=COLORS['text_white'],
            font=ctk.CTkFont(size=12)
        )
        self.search_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.search_entry.bind("<Return>", lambda e: self.load_data())
        self.search_entry.bind("<KeyRelease>", lambda e: self._debounced_search())

        # Location Combo
        ctk.CTkLabel(filter_row, text="Location:", font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=COLORS['text_light']).pack(side="left", padx=(0, 5))

        self.location_var = ctk.StringVar(value="All Locations")
        self.location_combo = ctk.CTkComboBox(
            filter_row, values=["All Locations"], variable=self.location_var,
            width=170, height=36, corner_radius=8,
            fg_color=COLORS['entry_bg'], border_color=COLORS['border'],
            text_color=COLORS['text_white'], button_color=COLORS['primary'],
            dropdown_fg_color=COLORS['bg_card'],
            font=ctk.CTkFont(size=12),
            command=lambda e: self.load_data())
        self.location_combo.pack(side="left", padx=(0, 8))

        # Status Filter
        ctk.CTkLabel(filter_row, text="Status:", font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=COLORS['text_light']).pack(side="left", padx=(0, 5))

        self.status_var = ctk.StringVar(value="All Status")
        self.status_combo = ctk.CTkComboBox(
            filter_row, values=["All Status", "Active", "Inactive"],
            variable=self.status_var, width=110, height=36, corner_radius=8,
            fg_color=COLORS['entry_bg'], border_color=COLORS['border'],
            text_color=COLORS['text_white'], button_color=COLORS['primary'],
            dropdown_fg_color=COLORS['bg_card'],
            font=ctk.CTkFont(size=12),
            command=lambda e: self.load_data())
        self.status_combo.pack(side="left", padx=(0, 8))

        # Delivery Filter
        ctk.CTkLabel(filter_row, text="Delivery:", font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=COLORS['text_light']).pack(side="left", padx=(0, 5))

        self.delivery_var = ctk.StringVar(value="All Delivery")
        self.delivery_combo = ctk.CTkComboBox(
            filter_row, values=["All Delivery", "Delivered", "Pending"],
            variable=self.delivery_var, width=115, height=36, corner_radius=8,
            fg_color=COLORS['entry_bg'], border_color=COLORS['border'],
            text_color=COLORS['text_white'], button_color=COLORS['primary'],
            dropdown_fg_color=COLORS['bg_card'],
            font=ctk.CTkFont(size=12),
            command=lambda e: self.load_data())
        self.delivery_combo.pack(side="left", padx=(0, 8))

        # Config Filter
        ctk.CTkLabel(filter_row, text="Config:", font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=COLORS['text_light']).pack(side="left", padx=(0, 5))

        self.config_filter_var = ctk.StringVar(value="All Config")
        self.config_combo = ctk.CTkComboBox(
            filter_row, values=["All Config", "Done", "ON"],
            variable=self.config_filter_var, width=105, height=36, corner_radius=8,
            fg_color=COLORS['entry_bg'], border_color=COLORS['border'],
            text_color=COLORS['text_white'], button_color=COLORS['primary'],
            dropdown_fg_color=COLORS['bg_card'],
            font=ctk.CTkFont(size=12),
            command=lambda e: self.load_data())
        self.config_combo.pack(side="left", padx=(0, 8))

        # Reset Filter Button
        reset_btn = ctk.CTkButton(
            filter_row, text="🔄 Reset", width=80, height=36,
            corner_radius=8,
            fg_color=COLORS['primary_dark'], hover_color=COLORS['primary'],
            border_width=1, border_color=COLORS['border'],
            text_color=COLORS['text_light'],
            font=ctk.CTkFont(size=11, weight="bold"),
            command=self.clear_filters)
        reset_btn.pack(side="left")

        # ── Main Container (Table or Grid View) ──
        self.main_container = ctk.CTkFrame(self, fg_color=COLORS['bg_card'], corner_radius=14,
                                           border_width=1, border_color=COLORS['border'])
        self.main_container.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        # Top Bar of Table Container
        top_bar = ctk.CTkFrame(self.main_container, fg_color="transparent")
        top_bar.pack(fill="x", padx=15, pady=(8, 4))

        self.count_label = ctk.CTkLabel(top_bar, text="Loading directory...",
                                        font=ctk.CTkFont(size=13, weight="bold"),
                                        text_color=COLORS['secondary'])
        self.count_label.pack(side="left")

        # Compact Sort By Dropdown
        ctk.CTkLabel(top_bar, text="🔃 Sort By:", font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=COLORS['text_light']).pack(side="left", padx=(14, 4))

        self.sort_var = ctk.StringVar(value="ID (1 ➔ N)")
        self.sort_combo = ctk.CTkComboBox(
            top_bar, variable=self.sort_var,
            values=[
                "ID (1 ➔ N)",
                "ID (N ➔ 1)",
                "IP (Low ➔ High)",
                "IP (High ➔ Low)",
                "Extension (Low ➔ High)",
                "Extension (High ➔ Low)",
                "Name (A ➔ Z)",
                "Name (Z ➔ A)",
                "Serial No (A ➔ Z)",
                "Location (A ➔ Z)",
                "Status (Active ➔ Inactive)"
            ],
            width=155, height=28, corner_radius=6,
            fg_color=COLORS['entry_bg'], border_color=COLORS['border'],
            text_color=COLORS['text_white'], button_color=COLORS['primary'],
            dropdown_fg_color=COLORS['bg_card'],
            font=ctk.CTkFont(size=11),
            command=self.on_sort_dropdown_change
        )
        self.sort_combo.pack(side="left", padx=(0, 10))

        # Color Legend (🔵 Blue = Inactive+Pending+Config ON | 🟡 Yellow = Inactive+Pending | 🔴 Red = Just Inactive)
        legend_frame = ctk.CTkFrame(top_bar, fg_color="transparent")
        legend_frame.pack(side="left", padx=(10, 0))

        ctk.CTkLabel(legend_frame, text="🔵 All Inactive (Pending + Config ON)", font=ctk.CTkFont(size=10, weight="bold"),
                     text_color="#38BDF8").pack(side="left", padx=4)
        ctk.CTkLabel(legend_frame, text="🟡 Inactive + Pending", font=ctk.CTkFont(size=10, weight="bold"),
                     text_color="#FFD700").pack(side="left", padx=4)
        ctk.CTkLabel(legend_frame, text="🔴 Just Inactive", font=ctk.CTkFont(size=10, weight="bold"),
                     text_color="#FF4D4D").pack(side="left", padx=4)

        # View Mode Switcher Segmented Button
        self.view_switcher = ctk.CTkSegmentedButton(
            top_bar, values=["🏁 Table View", "🎴 Card Grid View"],
            selected_color=COLORS['primary'],
            selected_hover_color=COLORS['primary_light'],
            unselected_color=COLORS['entry_bg'],
            unselected_hover_color=COLORS['primary_dark'],
            text_color=COLORS['text_white'],
            font=ctk.CTkFont(size=11, weight="bold"),
            command=self.on_view_mode_switch
        )
        self.view_switcher.set("🏁 Table View")
        self.view_switcher.pack(side="right")

        # Content Frame holding either Table or Cards
        self.view_content_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.view_content_frame.pack(fill="both", expand=True, padx=10, pady=(5, 10))

        self.build_table_view()

    def build_table_view(self):
        for w in self.view_content_frame.winfo_children():
            w.destroy()

        table_container = ctk.CTkFrame(self.view_content_frame, fg_color="transparent")
        table_container.pack(fill="both", expand=True)

        setup_treeview_style()

        columns = list(self.TABLE_HEADERS.keys())
        self.tree = ttk.Treeview(table_container, columns=columns, show="headings", selectmode="browse")

        for col, (head, width, align) in self.TABLE_HEADERS.items():
            self.tree.column(col, width=width, minwidth=width, stretch=False, anchor=align)

        self.update_table_headers()

        tree_scroll_y = ttk.Scrollbar(table_container, orient="vertical", command=self.tree.yview)
        tree_scroll_x = ttk.Scrollbar(table_container, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=tree_scroll_y.set, xscrollcommand=tree_scroll_x.set)

        # Grid placement ensures horizontal scrollbar spans across the bottom properly
        self.tree.grid(row=0, column=0, sticky="nsew")
        tree_scroll_y.grid(row=0, column=1, sticky="ns")
        tree_scroll_x.grid(row=1, column=0, sticky="ew")

        table_container.grid_rowconfigure(0, weight=1)
        table_container.grid_columnconfigure(0, weight=1)

        # Alternating row colors for clearer cell separation
        self.tree.tag_configure("even_row", background="#1E1020", foreground="#FFFFFF")
        self.tree.tag_configure("odd_row",  background="#2A1530", foreground="#FFFFFF")

        # ── User-Defined Color Tags ──
        self.tree.tag_configure("hl_blue",   background="#0B2545", foreground="#38BDF8")
        self.tree.tag_configure("hl_yellow", background="#3B2A00", foreground="#FFD700")
        self.tree.tag_configure("hl_red",    background="#450A0A", foreground="#FF4D4D")

        self.tree.bind("<Double-1>", lambda e: self.on_double_click_row())
        self.tree.bind("<Button-3>", lambda e: self.on_right_click_row(e))

    def update_table_headers(self):
        if not hasattr(self, 'tree') or not self.tree.winfo_exists():
            return
        for col, (head, width, align) in self.TABLE_HEADERS.items():
            self.tree.heading(col, text=head, anchor="center")

    def on_sort_dropdown_change(self, choice):
        if choice == "ID (1 ➔ N)":
            self.sort_col = "sl"
            self.sort_reverse = False
        elif choice == "ID (N ➔ 1)":
            self.sort_col = "sl"
            self.sort_reverse = True
        elif choice == "IP (Low ➔ High)":
            self.sort_col = "ip"
            self.sort_reverse = False
        elif choice == "IP (High ➔ Low)":
            self.sort_col = "ip"
            self.sort_reverse = True
        elif choice == "Extension (Low ➔ High)":
            self.sort_col = "ext"
            self.sort_reverse = False
        elif choice == "Extension (High ➔ Low)":
            self.sort_col = "ext"
            self.sort_reverse = True
        elif choice == "Name (A ➔ Z)":
            self.sort_col = "name"
            self.sort_reverse = False
        elif choice == "Name (Z ➔ A)":
            self.sort_col = "name"
            self.sort_reverse = True
        elif choice == "Serial No (A ➔ Z)":
            self.sort_col = "serial"
            self.sort_reverse = False
        elif choice == "Location (A ➔ Z)":
            self.sort_col = "dept"
            self.sort_reverse = False
        elif choice == "Status (Active ➔ Inactive)":
            self.sort_col = "status"
            self.sort_reverse = False

        self.apply_sorting_and_render()

    def get_phone_sort_key(self, p, col):
        def _ip_tuple(ip):
            if not ip or str(ip).strip().lower() in ('none', 'null', ''):
                return (999, 999, 999, 999) if not self.sort_reverse else (-1, -1, -1, -1)
            try:
                parts = [int(x) for x in str(ip).strip().split('.')]
                if len(parts) == 4:
                    return tuple(parts)
            except Exception:
                pass
            return (999, 999, 999, 999) if not self.sort_reverse else (-1, -1, -1, -1)

        def _num_or_str(v):
            if v is None or str(v).strip().lower() in ('', 'none', 'null'):
                return (2, 0, "") if not self.sort_reverse else (-1, 0, "")
            s = str(v).strip()
            if s.isdigit():
                return (0, int(s), "")
            return (1, 0, s.lower())

        def _str_val(v):
            if v is None or str(v).strip().lower() in ('', 'none', 'null'):
                return "~~~~~~~~" if not self.sort_reverse else ""
            return str(v).strip().lower()

        if col == "sl":
            return (0, p.get('phone_id', 0), "")
        elif col == "ip":
            return _ip_tuple(p.get('ip_address'))
        elif col == "ext":
            return _num_or_str(p.get('extension'))
        elif col == "caller_id":
            return _num_or_str(p.get('caller_id'))
        elif col == "emp_id":
            return _num_or_str(p.get('employee_id'))
        elif col == "serial":
            return _str_val(p.get('phone_set_serial_no'))
        elif col == "name":
            return _str_val(p.get('employee_name'))
        elif col == "position":
            return _str_val(p.get('position'))
        elif col == "dept":
            return _str_val(p.get('dept_name') or p.get('department'))
        elif col == "brand_model":
            brand = p.get('brand') or ''
            model = p.get('model') or ''
            return _str_val(f"{brand} {model}".strip())
        elif col == "status":
            return _str_val(p.get('status'))
        elif col == "delivery":
            return _str_val(p.get('delivery_status'))
        elif col == "config":
            return _str_val(p.get('configure_status'))
        return (0, p.get('phone_id', 0), "")

    def apply_sorting_and_render(self):
        if hasattr(self, 'current_phones_data') and self.current_phones_data:
            self.current_phones_data.sort(
                key=lambda p: self.get_phone_sort_key(p, self.sort_col),
                reverse=self.sort_reverse
            )
        self.render_phones_data()

    def build_grid_view(self):
        for w in self.view_content_frame.winfo_children():
            w.destroy()

        self.scroll_grid = ctk.CTkScrollableFrame(
            self.view_content_frame, fg_color="transparent",
            scrollbar_button_color=COLORS['primary'],
            scrollbar_button_hover_color=COLORS['primary_light']
        )
        self.scroll_grid.pack(fill="both", expand=True)

        # ── Modern Pagination Control Bar ──
        self.grid_pagination_bar = ctk.CTkFrame(
            self.view_content_frame, fg_color=COLORS['bg_card'],
            corner_radius=12, height=44, border_width=1, border_color=COLORS['border']
        )
        self.grid_pagination_bar.pack(fill="x", pady=(8, 0))

        # Left Info Label
        self.page_info_label = ctk.CTkLabel(
            self.grid_pagination_bar, text="Page 1 of 1",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=COLORS['text_light']
        )
        self.page_info_label.pack(side="left", padx=15)

        # Right: Page Size Selector Menu
        page_size_menu = ctk.CTkOptionMenu(
            self.grid_pagination_bar,
            values=["12 / page", "24 / page", "48 / page", "96 / page"],
            variable=self.grid_page_size_var,
            width=110, height=28, corner_radius=8,
            fg_color=COLORS['entry_bg'],
            button_color=COLORS['primary'],
            button_hover_color=COLORS['primary_light'],
            dropdown_fg_color=COLORS['bg_card'],
            dropdown_hover_color=COLORS['primary'],
            text_color=COLORS['text_white'],
            font=ctk.CTkFont(size=11, weight="bold"),
            command=self.on_grid_page_size_change
        )
        page_size_menu.pack(side="right", padx=(5, 15), pady=8)

        # Center / Right Nav Box
        nav_box = ctk.CTkFrame(self.grid_pagination_bar, fg_color="transparent")
        nav_box.pack(side="right", padx=10)

        self.btn_first_page = ctk.CTkButton(
            nav_box, text="⏮ First", width=65, height=28, corner_radius=8,
            fg_color=COLORS['entry_bg'], hover_color=COLORS['primary'],
            border_width=1, border_color=COLORS['border'],
            text_color=COLORS['text_white'], font=ctk.CTkFont(size=11, weight="bold"),
            command=lambda: self.change_grid_page(1)
        )
        self.btn_first_page.pack(side="left", padx=3)

        self.btn_prev_page = ctk.CTkButton(
            nav_box, text="◀ Prev", width=65, height=28, corner_radius=8,
            fg_color=COLORS['entry_bg'], hover_color=COLORS['primary'],
            border_width=1, border_color=COLORS['border'],
            text_color=COLORS['text_white'], font=ctk.CTkFont(size=11, weight="bold"),
            command=lambda: self.change_grid_page(self.grid_page - 1)
        )
        self.btn_prev_page.pack(side="left", padx=3)

        self.page_indicator = ctk.CTkLabel(
            nav_box, text=" 1 / 1 ", width=65,
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=COLORS['secondary']
        )
        self.page_indicator.pack(side="left", padx=6)

        self.btn_next_page = ctk.CTkButton(
            nav_box, text="Next ▶", width=65, height=28, corner_radius=8,
            fg_color=COLORS['entry_bg'], hover_color=COLORS['primary'],
            border_width=1, border_color=COLORS['border'],
            text_color=COLORS['text_white'], font=ctk.CTkFont(size=11, weight="bold"),
            command=lambda: self.change_grid_page(self.grid_page + 1)
        )
        self.btn_next_page.pack(side="left", padx=3)

        self.btn_last_page = ctk.CTkButton(
            nav_box, text="Last ⏭", width=65, height=28, corner_radius=8,
            fg_color=COLORS['entry_bg'], hover_color=COLORS['primary'],
            border_width=1, border_color=COLORS['border'],
            text_color=COLORS['text_white'], font=ctk.CTkFont(size=11, weight="bold"),
            command=self.go_to_last_page
        )
        self.btn_last_page.pack(side="left", padx=3)

    def change_grid_page(self, page_num):
        total_records = len(self.current_phones_data)
        total_pages = max(1, (total_records + self.grid_page_size - 1) // self.grid_page_size)
        target_page = max(1, min(page_num, total_pages))
        if target_page != self.grid_page or (hasattr(self, 'scroll_grid') and not self.scroll_grid.winfo_children()):
            self.grid_page = target_page
            self.render_phones_data()
            if hasattr(self, 'scroll_grid') and self.scroll_grid:
                try:
                    self.scroll_grid._parent_canvas.yview_moveto(0)
                except Exception:
                    pass

    def go_to_last_page(self):
        total_records = len(self.current_phones_data)
        total_pages = max(1, (total_records + self.grid_page_size - 1) // self.grid_page_size)
        self.change_grid_page(total_pages)

    def on_grid_page_size_change(self, selected_size_str):
        try:
            val = int(selected_size_str.split()[0])
            self.grid_page_size = val
            self.grid_page = 1
            self.render_phones_data()
        except Exception:
            pass

    def on_view_mode_switch(self, selected_mode):
        if "Card Grid" in selected_mode:
            self.view_mode = "grid"
            self.build_grid_view()
        else:
            self.view_mode = "table"
            self.build_table_view()
        self.render_phones_data()

    def _debounced_search(self):
        if self._search_timer:
            self.after_cancel(self._search_timer)
        self._search_timer = self.after(300, self.load_data)

    def on_location_type_change(self):
        self.grid_page = 1
        self.load_dropdowns()
        self.load_data()

    def load_dropdowns(self):
        def _bg_depts():
            try:
                depts = db.get_all_departments()
            except Exception:
                depts = []
            if self.winfo_exists():
                self.after(0, lambda: self._populate_dropdowns(depts))

        import threading
        threading.Thread(target=_bg_depts, daemon=True).start()

    def _populate_dropdowns(self, depts):
        if not self.winfo_exists():
            return
        try:
            loc_type = self.loc_type_var.get()
            if loc_type != "All":
                depts = [d for d in depts if d.get('dept_type') == loc_type]

            names = ["All Locations"] + [d['dept_name'] for d in depts]
            self.location_combo.configure(values=names)

            if self.location_var.get() not in names:
                self.location_var.set("All Locations")
        except Exception:
            pass

    def clear_filters(self):
        self.loc_type_var.set("All")
        self.search_by_var.set("All Fields")
        self.search_var.set("")
        self.location_var.set("All Locations")
        self.status_var.set("All Status")
        self.delivery_var.set("All Delivery")
        self.config_filter_var.set("All Config")
        self.grid_page = 1
        self.load_dropdowns()
        self.load_data()

    def load_data(self):
        loc_type = self.loc_type_var.get()
        search_by = self.search_by_var.get()
        search_term = self.search_var.get().strip()
        location = self.location_var.get()
        status = self.status_var.get()
        delivery = self.delivery_var.get()
        config_status = self.config_filter_var.get()
        sort_asc = self.id_sort_asc

        self._load_gen = getattr(self, '_load_gen', 0) + 1
        current_gen = self._load_gen

        def _bg_fetch():
            try:
                phones = db.get_filtered_phones(
                    loc_type=loc_type,
                    search_by=search_by,
                    search_term=search_term,
                    location=location,
                    status=status,
                    delivery=delivery,
                    config_status=config_status,
                    sort_asc=sort_asc
                )
                sig = db.get_phones_data_signature()
                err = None
            except Exception as e:
                phones = None
                sig = None
                err = e

            if self.winfo_exists():
                self.after(0, lambda: self._on_data_loaded(current_gen, phones, sig, err))

        import threading
        threading.Thread(target=_bg_fetch, daemon=True).start()

    def _on_data_loaded(self, gen, phones, sig, err):
        if not self.winfo_exists() or gen != getattr(self, '_load_gen', 0):
            return
        if err:
            self.count_label.configure(text=f"Error: {err}")
            return
        if sig:
            self._last_data_sig = sig
        self.current_phones_data = phones or []
        self.apply_sorting_and_render()

    def _start_auto_sync(self):
        self._last_data_sig = None
        self._sync_in_progress = False
        self._schedule_next_sync()

    def _schedule_next_sync(self):
        try:
            from config import AUTO_SYNC_INTERVAL_MS
            interval = AUTO_SYNC_INTERVAL_MS
        except Exception:
            interval = 6000
        if self.winfo_exists():
            self._sync_timer = self.after(interval, self._sync_heartbeat)

    def _sync_heartbeat(self):
        try:
            if not self.winfo_exists() or getattr(self, '_sync_in_progress', False):
                return

            # Non-intrusive safety: do not interrupt if search box is actively focused by typing
            has_focus = False
            try:
                focused = self.focus_get()
                if focused and hasattr(self, 'search_entry'):
                    inner_search = getattr(self.search_entry, '_entry', self.search_entry)
                    if focused == inner_search:
                        has_focus = True
            except Exception:
                pass

            if not has_focus:
                self._sync_in_progress = True
                def _bg_sig():
                    try:
                        sig = db.get_phones_data_signature()
                    except Exception:
                        sig = None
                    if self.winfo_exists():
                        self.after(0, lambda: self._on_sync_checked(sig))

                import threading
                threading.Thread(target=_bg_sig, daemon=True).start()
                return
        except Exception:
            pass
        self._schedule_next_sync()

    def _on_sync_checked(self, current_sig):
        try:
            self._sync_in_progress = False
            if current_sig:
                if self._last_data_sig is not None and current_sig != self._last_data_sig:
                    self._last_data_sig = current_sig
                    self.load_data()
                else:
                    self._last_data_sig = current_sig
        except Exception:
            pass
        finally:
            self._schedule_next_sync()

    def _on_destroy(self, event=None):
        if self._sync_timer:
            try:
                self.after_cancel(self._sync_timer)
            except Exception:
                pass
            self._sync_timer = None

    def render_phones_data(self):
        phones = self.current_phones_data
        count = len(phones)
        self.count_label.configure(text=f"📋 Total {count} phone records found")

        if self.view_mode == "table":
            for item in self.tree.get_children():
                self.tree.delete(item)

            for idx, p in enumerate(phones):
                def _display(v):
                    if v is None:
                        return ''
                    s = str(v).strip()
                    return '' if s.lower() in ('none', 'null') else s

                brand_mod = f"{p.get('brand', '')} {_display(p.get('model'))}".strip()
                dept_name = _display(p.get('dept_name') or p.get('department'))
                status_icon = "🟢 Active" if p.get('status') == 'Active' else "🔴 Inactive"
                deliv_icon = "📦 Delivered" if p.get('delivery_status') == 'Delivered' else "⏳ Pending"
                cfg_icon = p.get('configure_status') or 'Done'

                ext_val = _display(p.get('extension'))
                caller_val = _display(p.get('caller_id'))
                empid_val = _display(p.get('employee_id'))
                serial_val = _display(p.get('phone_set_serial_no'))
                name_val = _display(p.get('employee_name'))
                pos_val = _display(p.get('position'))
                ip_val = _display(p.get('ip_address'))

                # ── Exact Color Logic: 🔵 All No -> Blue | 🟡 Inactive+Pending -> Yellow | 🔴 Just Inactive -> Red ──
                is_inactive  = p.get('status') != 'Active'
                is_pending   = p.get('delivery_status') != 'Delivered'
                is_not_cfg   = p.get('configure_status') not in ('Done', None, '')

                if is_inactive and is_pending and is_not_cfg:
                    row_tag = "hl_blue"       # 🔵 BLUE: Inactive + Pending + Config ON
                elif is_inactive and is_pending:
                    row_tag = "hl_yellow"     # 🟡 YELLOW: Inactive + Pending delivery
                elif is_pending:
                    row_tag = "hl_yellow"     # 🟡 YELLOW: Pending delivery
                elif is_inactive:
                    row_tag = "hl_red"        # 🔴 RED: Inactive only
                elif is_not_cfg:
                    row_tag = "hl_blue"       # 🔵 BLUE: Config ON
                else:
                    row_tag = "even_row" if idx % 2 == 0 else "odd_row"

                self.tree.insert("", "end", iid=str(p['phone_id']), values=(
                    idx + 1,
                    ip_val,
                    ext_val,
                    caller_val,
                    empid_val,
                    serial_val,
                    name_val,
                    pos_val,
                    dept_name,
                    brand_mod,
                    status_icon,
                    deliv_icon,
                    cfg_icon,
                    "⚙️ Manage"
                ), tags=(row_tag,))
        else:
            if not hasattr(self, 'scroll_grid') or not self.scroll_grid.winfo_exists():
                return

            for w in self.scroll_grid.winfo_children():
                w.destroy()

            # Pagination calculations
            total_records = len(phones)
            total_pages = max(1, (total_records + self.grid_page_size - 1) // self.grid_page_size)
            if self.grid_page > total_pages:
                self.grid_page = total_pages
            if self.grid_page < 1:
                self.grid_page = 1

            start_idx = (self.grid_page - 1) * self.grid_page_size
            end_idx = min(start_idx + self.grid_page_size, total_records)
            page_items = phones[start_idx:end_idx]

            # Update pagination controls
            if hasattr(self, 'page_info_label') and self.page_info_label.winfo_exists():
                if total_records == 0:
                    self.page_info_label.configure(text="No records to display")
                    self.page_indicator.configure(text=" 0 / 0 ")
                else:
                    self.page_info_label.configure(
                        text=f"Showing {start_idx + 1}–{end_idx} of {total_records} cards (Page {self.grid_page} of {total_pages})"
                    )
                    self.page_indicator.configure(text=f" {self.grid_page} / {total_pages} ")

                # Enable/disable navigation buttons
                self.btn_first_page.configure(state="normal" if self.grid_page > 1 else "disabled")
                self.btn_prev_page.configure(state="normal" if self.grid_page > 1 else "disabled")
                self.btn_next_page.configure(state="normal" if self.grid_page < total_pages else "disabled")
                self.btn_last_page.configure(state="normal" if self.grid_page < total_pages else "disabled")

            if not page_items:
                empty_frame = ctk.CTkFrame(self.scroll_grid, fg_color="transparent")
                empty_frame.pack(fill="both", expand=True, pady=60)
                ctk.CTkLabel(
                    empty_frame, text="🔍 No phone records found matching current filter.",
                    font=ctk.CTkFont(size=14, weight="bold"),
                    text_color=COLORS['text_muted']
                ).pack()
                return

            # Render Card Grid for Current Page
            grid_container = ctk.CTkFrame(self.scroll_grid, fg_color="transparent")
            grid_container.pack(fill="both", expand=True)

            cols = 3
            for i in range(cols):
                grid_container.grid_columnconfigure(i, weight=1, uniform="card_col")

            for idx, p in enumerate(page_items):
                r = idx // cols
                c = idx % cols
                card = self.create_phone_card(grid_container, p)
                card.grid(row=r, column=c, padx=8, pady=8, sticky="nsew")

    def create_phone_card(self, parent, p):
        card = ctk.CTkFrame(parent, fg_color=COLORS['bg_card'], corner_radius=14,
                            border_width=1, border_color=COLORS['border'])

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=12, pady=10)

        # Header of card
        top = ctk.CTkFrame(inner, fg_color="transparent")
        top.pack(fill="x")

        def _card_val(v, default='-'):
            if v is None:
                return default
            s = str(v).strip()
            return default if s.lower() in ('none', 'null', '') else s

        ext_val = _card_val(p.get('extension'), default='N/A')
        ext_label = ctk.CTkLabel(top, text=f"📞 Ext: {ext_val}",
                                font=ctk.CTkFont(size=14, weight="bold"),
                                text_color=COLORS['secondary'])
        ext_label.pack(side="left")

        status_col = COLORS['success'] if p.get('status') == 'Active' else COLORS['danger']
        st_badge = ctk.CTkLabel(top, text=f"{p.get('status', 'Active')} ({p.get('configure_status', 'Done')})",
                                font=ctk.CTkFont(size=10, weight="bold"),
                                text_color=status_col)
        st_badge.pack(side="right")

        ctk.CTkFrame(inner, fg_color=COLORS['border'], height=1).pack(fill="x", pady=6)

        body = ctk.CTkFrame(inner, fg_color="transparent")
        body.pack(fill="x")

        dept_str = _card_val(p.get('dept_name') or p.get('department'), default='-')
        name_str = _card_val(p.get('employee_name'), default='-')
        pos_str = _card_val(p.get('position'), default='-')
        ip_str = _card_val(p.get('ip_address'), default='-')
        serial_str = _card_val(p.get('phone_set_serial_no'), default='-')

        ctk.CTkLabel(body, text=f"👤 {name_str}", font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=COLORS['text_white'], anchor="w").pack(fill="x")
        ctk.CTkLabel(body, text=f"💼 {pos_str}", font=ctk.CTkFont(size=10),
                     text_color=COLORS['text_muted'], anchor="w").pack(fill="x")
        ctk.CTkLabel(body, text=f"🏢 {dept_str}", font=ctk.CTkFont(size=10),
                     text_color=COLORS['text_light'], anchor="w").pack(fill="x")
        ctk.CTkLabel(body, text=f"🌐 IP: {ip_str}", font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=COLORS['info'], anchor="w").pack(fill="x", pady=(2, 0))
        ctk.CTkLabel(body, text=f"🔢 S/N: {serial_str}", font=ctk.CTkFont(size=10),
                     text_color=COLORS['text_muted'], anchor="w").pack(fill="x")

        # Action Buttons
        btn_bar = ctk.CTkFrame(inner, fg_color="transparent")
        btn_bar.pack(fill="x", pady=(8, 0))

        if p.get('ip_address'):
            ping_btn = ctk.CTkButton(
                btn_bar, text="⚡ Ping", width=60, height=26,
                corner_radius=8, fg_color=COLORS['primary'],
                hover_color=COLORS['primary_light'],
                font=ctk.CTkFont(size=10, weight="bold"),
                command=lambda ip=p.get('ip_address'): self.open_ping_tool(ip)
            )
            ping_btn.pack(side="left", padx=(0, 4))

        edit_btn = ctk.CTkButton(
            btn_bar, text="✏️ Edit", width=60, height=26,
            corner_radius=8, fg_color=COLORS['secondary'],
            hover_color=COLORS['secondary_hover'], text_color="#000000",
            font=ctk.CTkFont(size=10, weight="bold"),
            command=lambda phone=p: self.show_edit_form(phone)
        )
        edit_btn.pack(side="left", padx=2)

        del_btn = ctk.CTkButton(
            btn_bar, text="🗑️", width=30, height=26,
            corner_radius=8, fg_color=COLORS['danger'],
            hover_color="#D32F2F",
            command=lambda pid=p['phone_id']: self.confirm_delete(pid)
        )
        del_btn.pack(side="right")

        return card

    def on_double_click_row(self):
        selected = self.tree.selection()
        if not selected:
            return
        phone_id_str = selected[0]
        # Find full object by phone_id (iid)
        phone = next((p for p in self.current_phones_data if str(p['phone_id']) == phone_id_str), None)
        if phone:
            self.show_edit_form(phone)

    def on_right_click_row(self, event):
        iid = self.tree.identify_row(event.y)
        if iid:
            self.tree.selection_set(iid)
            phone = next((p for p in self.current_phones_data if str(p['phone_id']) == iid), None)

            menu = tk.Menu(self, tearoff=0, bg="#251528", fg="#FFFFFF", activebackground="#85175F")
            if phone and phone.get('ip_address'):
                menu.add_command(label=f"💻 Continuous Ping {phone['ip_address']}", command=lambda: self.open_ping_tool(phone['ip_address']))
            if phone:
                menu.add_command(label="✏️ Edit Phone Details", command=lambda: self.show_edit_form(phone))
                # Only Admin is allowed to see and perform delete
                if self.user and self.user.get('role') == 'Admin':
                    menu.add_separator()
                    menu.add_command(label="🗑️ Delete Phone Record", command=lambda: self.confirm_delete(phone['phone_id']))

            menu.post(event.x_root, event.y_root)

    def open_ping_tool(self, default_ip=""):
        from ip_tool import open_ip_tool
        open_ip_tool(self, default_ip)

    def show_add_form(self):
        PhoneFormDialog(self, user=self.user, on_save_success=self.load_data)

    def show_edit_form(self, phone):
        PhoneFormDialog(self, user=self.user, phone_data=phone, on_save_success=self.load_data)

    def confirm_delete(self, phone_id):
        # Strict Admin role enforcement
        if not self.user or self.user.get('role') != 'Admin':
            messagebox.showerror("Permission Denied", "Only Admin users are permitted to delete IP phone records.", parent=self)
            return

        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this IP phone record?"):
            try:
                db.delete_phone(phone_id)
                self.load_data()
                messagebox.showinfo("Success", "IP Phone record deleted successfully.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete phone:\n{str(e)}")

    def export_excel(self):
        try:
            import openpyxl
        except ImportError:
            messagebox.showerror("Error", "openpyxl package is required for Excel export.\nRun: pip install openpyxl")
            return

        from tkinter import filedialog
        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel Files", "*.xlsx")],
            title="Save IP Phone Directory Export"
        )
        if not path:
            return

        try:
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "IP Phonebook"

            headers = [
                "ID", "IP Address", "Extension", "Caller ID", "Emp ID",
                "Serial No", "Employee Name", "Position", "Department",
                "Brand", "Model", "Status", "Delivery Status", "Config Status", "Remarks"
            ]
            ws.append(headers)

            for p in self.current_phones_data:
                ws.append([
                    p['phone_id'], p.get('ip_address') or '', p.get('extension') or '',
                    p.get('caller_id') or '', p.get('employee_id') or '',
                    p.get('phone_set_serial_no') or '', p.get('employee_name') or '',
                    p.get('position') or '', p.get('dept_name') or p.get('department') or '',
                    p.get('brand') or '', p.get('model') or '', p.get('status') or '',
                    p.get('delivery_status') or '', p.get('configure_status') or '',
                    p.get('remarks') or ''
                ])

            wb.save(path)
            messagebox.showinfo("Success", f"Data exported successfully to:\n{path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export file:\n{str(e)}")

    def import_data_file(self):
        from tkinter import filedialog
        path = filedialog.askopenfilename(
            filetypes=[("CSV and Excel Files", "*.csv;*.xlsx;*.xls")],
            title="Select File to Import IP Phones"
        )
        if not path:
            return

        try:
            import import_from_excel
            inserted, skipped, errors = import_from_excel.import_file(path, created_by=self.user['user_id'])
            msg = f"Import completed successfully!\n\nInserted/Updated: {inserted}\nSkipped: {skipped}"
            if errors:
                msg += f"\n\nFirst few warnings:\n" + "\n".join(errors[:5])
            messagebox.showinfo("Import Summary", msg)
            self.load_data()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to import file:\n{str(e)}")


class LocationSearchDialog(ctk.CTkToplevel):
    """Sleek, Compact Modal Dialog for Searching & Selecting Location/Branch."""
    def __init__(self, parent, departments, on_select):
        super().__init__(parent)
        self.parent = parent
        self.departments = departments
        self.on_select = on_select

        self.title("🏢 Select Department / Location")
        self.geometry("480x420")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.configure(fg_color=COLORS['bg_dark'])

        # Center dialog
        self.update_idletasks()
        x = (self.winfo_screenwidth() - 480) // 2
        y = (self.winfo_screenheight() - 420) // 2
        self.geometry(f"+{x}+{y}")

        self.build_ui()
        self.load_locations()

    def build_ui(self):
        card = ctk.CTkFrame(self, fg_color=COLORS['bg_card'], corner_radius=14,
                            border_width=1, border_color=COLORS['border'])
        card.pack(fill="both", expand=True, padx=12, pady=12)

        ctk.CTkLabel(card, text="🏢 Select Location / Branch", font=ctk.CTkFont(size=16, weight="bold"),
                     text_color=COLORS['secondary']).pack(pady=(12, 6))

        # Category Filter Row
        cat_frame = ctk.CTkFrame(card, fg_color="transparent")
        cat_frame.pack(fill="x", padx=10, pady=(0, 6))

        self.cat_var = ctk.StringVar(value="All")
        cats = [("All", "All"), ("Branch", "Branch"), ("Sub-Branch", "Sub-Branch"), ("HO Division", "HO Div")]
        for val, label in cats:
            ctk.CTkRadioButton(
                cat_frame, text=label, variable=self.cat_var, value=val,
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color=COLORS['text_light'], fg_color=COLORS['primary'],
                hover_color=COLORS['primary_light'],
                radiobutton_width=16, radiobutton_height=16,
                command=self.load_locations
            ).pack(side="left", padx=5)

        # Quick Recent Locations Chips (if available)
        recent_depts = form_history.load_history().get('departments', [])[:3]
        if recent_depts:
            rec_frame = ctk.CTkFrame(card, fg_color="transparent")
            rec_frame.pack(fill="x", padx=10, pady=(0, 4))
            ctk.CTkLabel(rec_frame, text="⭐ Recent:", font=ctk.CTkFont(size=10, weight="bold"),
                         text_color=COLORS['secondary']).pack(side="left", padx=(0, 4))
            for r_name in recent_depts:
                ctk.CTkButton(
                    rec_frame, text=r_name, height=24, corner_radius=12,
                    fg_color=COLORS['primary_dark'], hover_color=COLORS['primary'],
                    text_color=COLORS['text_white'], font=ctk.CTkFont(size=10),
                    command=lambda n=r_name: self.choose_location(n)
                ).pack(side="left", padx=2)

        # Search Bar
        search_frame = ctk.CTkFrame(card, fg_color="transparent")
        search_frame.pack(fill="x", padx=10, pady=(0, 8))

        self.search_var = ctk.StringVar()
        search_entry = ctk.CTkEntry(
            search_frame, textvariable=self.search_var,
            placeholder_text="🔍 Type location (e.g. Agrabad, HRD, Principal)...",
            placeholder_text_color=COLORS['text_muted'],
            height=36, corner_radius=8,
            fg_color=COLORS['entry_bg'], border_color=COLORS['border'],
            text_color=COLORS['text_white'],
            font=ctk.CTkFont(size=12)
        )
        search_entry.pack(fill="x")
        search_entry.focus()
        search_entry.bind("<KeyRelease>", lambda e: self.load_locations())

        # Scrollable Location List
        self.scroll_list = ctk.CTkScrollableFrame(
            card, fg_color=COLORS['entry_bg'], corner_radius=8,
            scrollbar_button_color=COLORS['primary'],
            scrollbar_button_hover_color=COLORS['primary_light']
        )
        self.scroll_list.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def load_locations(self):
        for w in self.scroll_list.winfo_children():
            w.destroy()

        cat = self.cat_var.get()
        term = self.search_var.get().strip().lower()

        filtered = []
        for d in self.departments:
            if cat != "All" and d.get('dept_type') != cat:
                continue
            if term and term not in d['dept_name'].lower():
                continue
            filtered.append(d)

        if not filtered:
            ctk.CTkLabel(self.scroll_list, text="No matching locations found",
                         text_color=COLORS['text_muted'],
                         font=ctk.CTkFont(size=12)).pack(pady=20)
            return

        for d in filtered:
            name = d['dept_name']
            dtype = d.get('dept_type', '')
            badge_text = f"{name} ({dtype})" if dtype else name

            btn = ctk.CTkButton(
                self.scroll_list, text=badge_text, height=34, anchor="w",
                corner_radius=6, fg_color="transparent",
                hover_color=COLORS['primary'],
                text_color=COLORS['text_white'],
                font=ctk.CTkFont(size=12),
                command=lambda n=name: self.choose_location(n)
            )
            btn.pack(fill="x", padx=4, pady=2)

    def choose_location(self, name):
        self.on_select(name)
        self.destroy()


class PhoneFormDialog(ctk.CTkToplevel):
    def __init__(self, parent, user, phone_data=None, on_save_success=None):
        super().__init__(parent)
        self.parent = parent
        self.user = user
        self.phone_data = phone_data
        self.on_save_success = on_save_success

        self.departments = db.get_all_departments()
        self.all_dept_names = [d['dept_name'] for d in self.departments] if self.departments else []
        self.top_models = form_history.get_top_models(4)

        title_str = "✏️ Edit IP Phone Details" if phone_data else "➕ Add New IP Phone"
        self.title(title_str)
        self.geometry("680x690")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.configure(fg_color=COLORS['bg_dark'])

        # Center dialog
        self.update_idletasks()
        x = (self.winfo_screenwidth() - 680) // 2
        y = (self.winfo_screenheight() - 690) // 2
        self.geometry(f"+{x}+{y}")

        self.build_ui()

        if phone_data:
            self.populate_form()

    def build_ui(self):
        card = ctk.CTkFrame(self, fg_color=COLORS['bg_card'], corner_radius=14,
                            border_width=1, border_color=COLORS['border'])
        card.pack(fill="both", expand=True, padx=15, pady=15)

        top_header = ctk.CTkFrame(card, fg_color="transparent")
        top_header.pack(fill="x", padx=15, pady=(12, 6))

        title_txt = "✏️ Edit IP Phone Record" if self.phone_data else "➕ Add New IP Phone Record"
        ctk.CTkLabel(top_header, text=title_txt, font=ctk.CTkFont(size=18, weight="bold"),
                     text_color=COLORS['secondary']).pack(side="left")

        # Smart Auto-Fill Last Used Button (Only on Add Mode)
        if not self.phone_data:
            ctk.CTkButton(
                top_header, text="⚡ Fill Last Used",
                height=28, corner_radius=6,
                fg_color=COLORS['primary'], hover_color=COLORS['primary_light'],
                font=ctk.CTkFont(size=11, weight="bold"),
                command=self.fill_last_used_entry
            ).pack(side="right")

        scroll = ctk.CTkScrollableFrame(card, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=15, pady=(0, 10))

        # Form Fields Grid
        grid_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        grid_frame.pack(fill="x")

        # ── Row 0: Department / Location * (col 0) | Extension (col 1) ──
        ctk.CTkLabel(grid_frame, text="Department / Location *", font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=COLORS['text_light']).grid(row=0, column=0, sticky="w", padx=5, pady=(5, 2))

        dept_box = ctk.CTkFrame(grid_frame, fg_color="transparent")
        dept_box.grid(row=1, column=0, padx=5, pady=(0, 10), sticky="w")

        self.dept_entry = ctk.CTkEntry(
            dept_box, width=195, height=36, corner_radius=8,
            placeholder_text="Type or click Select...",
            fg_color=COLORS['entry_bg'], border_color=COLORS['border'],
            text_color=COLORS['text_white'],
            font=ctk.CTkFont(size=12)
        )
        self.dept_entry.pack(side="left", padx=(0, 4))
        # Live Google-style Autocomplete for Department
        LiveAutocomplete(self, self.dept_entry, lambda: self.all_dept_names, max_items=5)

        select_btn = ctk.CTkButton(
            dept_box, text="🔍 Select", width=80, height=36,
            corner_radius=8, fg_color=COLORS['primary'],
            hover_color=COLORS['primary_light'],
            font=ctk.CTkFont(size=11, weight="bold"),
            command=self.open_location_selector
        )
        select_btn.pack(side="left")

        ctk.CTkLabel(grid_frame, text="Extension", font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=COLORS['text_light']).grid(row=0, column=1, sticky="w", padx=5, pady=(5, 2))
        ext_box = ctk.CTkFrame(grid_frame, fg_color="transparent")
        ext_box.grid(row=1, column=1, padx=5, pady=(0, 10), sticky="w")

        self.ext_entry = ctk.CTkEntry(
            ext_box, width=195, height=36, corner_radius=8,
            placeholder_text="e.g. 6101 or 5202 (Auto None if blank)",
            fg_color=COLORS['entry_bg'], border_color=COLORS['border'],
            text_color=COLORS['text_white']
        )
        self.ext_entry.pack(side="left", padx=(0, 4))
        # Live Google-style Autocomplete for Extension 3-digit prefixes & suggestions
        LiveAutocomplete(self, self.ext_entry, lambda: form_history.get_recent_extensions(self.dept_entry.get().strip()), max_items=6)

        ext_btn_text = "Open" if self.phone_data else "Create"
        ext_btn = ctk.CTkButton(
            ext_box, text=ext_btn_text, width=80, height=36,
            corner_radius=8, fg_color=COLORS['primary'],
            hover_color=COLORS['primary_light'],
            font=ctk.CTkFont(size=11, weight="bold"),
            command=self.open_extension_in_browser
        )
        ext_btn.pack(side="left")

        # ── Row 1: IP Address * (col 0) | Employee Name (col 1) ──
        ctk.CTkLabel(grid_frame, text="IP Address *", font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=COLORS['text_light']).grid(row=2, column=0, sticky="w", padx=5, pady=(5, 2))

        ip_box = ctk.CTkFrame(grid_frame, fg_color="transparent")
        ip_box.grid(row=3, column=0, padx=5, pady=(0, 10), sticky="w")

        self.ip_entry = ctk.CTkEntry(ip_box, width=195, height=36, corner_radius=8,
                                     placeholder_text="e.g. 172.19.102.204",
                                     fg_color=COLORS['entry_bg'], border_color=COLORS['border'],
                                     text_color=COLORS['text_white'])
        self.ip_entry.pack(side="left", padx=(0, 4))

        open_browser_btn = ctk.CTkButton(
            ip_box, text="🌐 Open", width=80, height=36,
            corner_radius=8, fg_color=COLORS['primary'],
            hover_color=COLORS['primary_light'],
            font=ctk.CTkFont(size=11, weight="bold"),
            command=self.open_ip_in_browser
        )
        open_browser_btn.pack(side="left")

        ctk.CTkLabel(grid_frame, text="Employee Name", font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=COLORS['text_light']).grid(row=2, column=1, sticky="w", padx=5, pady=(5, 2))
        self.name_entry = ctk.CTkEntry(
            grid_frame, width=280, height=36, corner_radius=8,
            placeholder_text="Optional (Auto None if blank)",
            fg_color=COLORS['entry_bg'], border_color=COLORS['border'],
            text_color=COLORS['text_white']
        )
        self.name_entry.grid(row=3, column=1, padx=5, pady=(0, 10), sticky="w")

        # ── Row 2: Phone Set Serial No (col 0) | Position / Designation (col 1) ──
        ctk.CTkLabel(grid_frame, text="Phone Set Serial No", font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=COLORS['text_light']).grid(row=4, column=0, sticky="w", padx=5, pady=(5, 2))
        self.serial_entry = ctk.CTkEntry(
            grid_frame, width=280, height=36, corner_radius=8,
            placeholder_text="e.g. Q7D223A00... or UPD025800...",
            fg_color=COLORS['entry_bg'], border_color=COLORS['border'],
            text_color=COLORS['text_white']
        )
        self.serial_entry.grid(row=5, column=0, padx=5, pady=(0, 10), sticky="w")
        # Live Google-style Autocomplete for Serial Number prefixes
        LiveAutocomplete(self, self.serial_entry, lambda: form_history.get_recent_serial_numbers(8), max_items=5)

        ctk.CTkLabel(grid_frame, text="Position / Designation", font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=COLORS['text_light']).grid(row=4, column=1, sticky="w", padx=5, pady=(5, 2))
        self.pos_combo = ctk.CTkComboBox(grid_frame, values=["None"] + POSITIONS, width=280, height=36, corner_radius=8,
                                         fg_color=COLORS['entry_bg'], border_color=COLORS['border'],
                                         text_color=COLORS['text_white'], button_color=COLORS['primary'],
                                         dropdown_fg_color=COLORS['bg_card'])
        self.pos_combo.set("None")
        self.pos_combo.grid(row=5, column=1, padx=5, pady=(0, 10), sticky="w")

        # ── Row 3: Caller ID / DID (col 0) | Employee ID (col 1) ──
        ctk.CTkLabel(grid_frame, text="Caller ID / DID", font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=COLORS['text_light']).grid(row=6, column=0, sticky="w", padx=5, pady=(5, 2))
        self.caller_entry = ctk.CTkEntry(
            grid_frame, width=280, height=36, corner_radius=8,
            placeholder_text="Optional (Auto None if blank)",
            fg_color=COLORS['entry_bg'], border_color=COLORS['border'],
            text_color=COLORS['text_white']
        )
        self.caller_entry.grid(row=7, column=0, padx=5, pady=(0, 10), sticky="w")
        # Live Google-style Autocomplete for Caller ID
        LiveAutocomplete(self, self.caller_entry, lambda: form_history.get_recent_caller_ids(8), max_items=5)

        ctk.CTkLabel(grid_frame, text="Employee ID", font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=COLORS['text_light']).grid(row=6, column=1, sticky="w", padx=5, pady=(5, 2))
        self.empid_entry = ctk.CTkEntry(
            grid_frame, width=280, height=36, corner_radius=8,
            placeholder_text="Optional (Auto None if blank)",
            fg_color=COLORS['entry_bg'], border_color=COLORS['border'],
            text_color=COLORS['text_white']
        )
        self.empid_entry.grid(row=7, column=1, padx=5, pady=(0, 10), sticky="w")
        # Live Google-style Autocomplete for Employee ID
        LiveAutocomplete(self, self.empid_entry, lambda: form_history.get_recent_employee_ids(8), max_items=5)

        # ── Row 4: Brand (col 0) | Model (col 1) ──
        ctk.CTkLabel(grid_frame, text="Brand", font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=COLORS['text_light']).grid(row=8, column=0, sticky="w", padx=5, pady=(5, 2))
        self.brand_combo = ctk.CTkComboBox(grid_frame, values=BRANDS, width=280, height=36, corner_radius=8,
                                           fg_color=COLORS['entry_bg'], border_color=COLORS['border'],
                                           text_color=COLORS['text_white'], button_color=COLORS['primary'],
                                           dropdown_fg_color=COLORS['bg_card'])
        self.brand_combo.grid(row=9, column=0, padx=5, pady=(0, 10), sticky="w")

        ctk.CTkLabel(grid_frame, text="Model", font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=COLORS['text_light']).grid(row=8, column=1, sticky="w", padx=5, pady=(5, 2))
        self.model_combo = ctk.CTkComboBox(
            grid_frame, values=self.top_models if self.top_models else ["X303", "V50P"],
            width=280, height=36, corner_radius=8,
            fg_color=COLORS['entry_bg'], border_color=COLORS['border'],
            text_color=COLORS['text_white'], button_color=COLORS['primary'],
            dropdown_fg_color=COLORS['bg_card']
        )
        self.model_combo.set(self.top_models[0] if self.top_models else "X303")
        self.model_combo.grid(row=9, column=1, padx=5, pady=(0, 10), sticky="w")

        # ── Row 5: 🔘 Phone Status (Default Inactive) | Deliver Radio Button (Default Pending/No) ──
        ctk.CTkLabel(grid_frame, text="Active Radio Button *", font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=COLORS['text_light']).grid(row=10, column=0, sticky="w", padx=5, pady=(5, 2))
        status_rf = ctk.CTkFrame(grid_frame, fg_color="transparent")
        status_rf.grid(row=11, column=0, padx=5, pady=(0, 10), sticky="w")

        self.status_var = ctk.StringVar(value="Inactive")
        ctk.CTkRadioButton(status_rf, text="Active", variable=self.status_var, value="Active",
                           font=ctk.CTkFont(size=12, weight="bold"), text_color=COLORS['text_white'],
                           fg_color=COLORS['primary'], hover_color=COLORS['primary_light']).pack(side="left", padx=(0, 15))
        ctk.CTkRadioButton(status_rf, text="Inactive", variable=self.status_var, value="Inactive",
                           font=ctk.CTkFont(size=12, weight="bold"), text_color=COLORS['text_white'],
                           fg_color=COLORS['danger'], hover_color="#D32F2F").pack(side="left")

        ctk.CTkLabel(grid_frame, text="Deliver Radio Button *", font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=COLORS['text_light']).grid(row=10, column=1, sticky="w", padx=5, pady=(5, 2))
        delivery_rf = ctk.CTkFrame(grid_frame, fg_color="transparent")
        delivery_rf.grid(row=11, column=1, padx=5, pady=(0, 10), sticky="w")

        self.delivery_var = ctk.StringVar(value="Pending")
        ctk.CTkRadioButton(delivery_rf, text="Delivered (Yes)", variable=self.delivery_var, value="Delivered",
                           font=ctk.CTkFont(size=12, weight="bold"), text_color=COLORS['text_white'],
                           fg_color=COLORS['primary'], hover_color=COLORS['primary_light']).pack(side="left", padx=(0, 15))
        ctk.CTkRadioButton(delivery_rf, text="Pending (No)", variable=self.delivery_var, value="Pending",
                           font=ctk.CTkFont(size=12, weight="bold"), text_color=COLORS['text_white'],
                           fg_color=COLORS['warning'], hover_color=COLORS['secondary_hover']).pack(side="left")

        # ── Row 6: 🔘 Configure Status (Default ON / Not Done) ──
        ctk.CTkLabel(grid_frame, text="Configure Radio Button (Done / ON) *", font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=COLORS['text_light']).grid(row=12, column=0, sticky="w", padx=5, pady=(5, 2))
        config_rf = ctk.CTkFrame(grid_frame, fg_color="transparent")
        config_rf.grid(row=13, column=0, padx=5, pady=(0, 10), sticky="w")

        self.config_var = ctk.StringVar(value="ON")
        ctk.CTkRadioButton(config_rf, text="Done", variable=self.config_var, value="Done",
                           font=ctk.CTkFont(size=12, weight="bold"), text_color=COLORS['text_white'],
                           fg_color=COLORS['primary'], hover_color=COLORS['primary_light']).pack(side="left", padx=(0, 15))
        ctk.CTkRadioButton(config_rf, text="ON (Not Done)", variable=self.config_var, value="ON",
                           font=ctk.CTkFont(size=12, weight="bold"), text_color=COLORS['text_white'],
                           fg_color=COLORS['secondary'], hover_color=COLORS['secondary_hover']).pack(side="left")

        # Action Button Row
        btn_bar = ctk.CTkFrame(card, fg_color="transparent")
        btn_bar.pack(fill="x", padx=15, pady=(5, 15))

        # Delete Button (Shown ONLY to Admin users when editing an existing record)
        if self.phone_data and self.user and self.user.get('role') == 'Admin':
            del_btn = ctk.CTkButton(
                btn_bar, text="🗑️ Delete Record", height=42, width=140,
                corner_radius=10, fg_color=COLORS['danger'],
                hover_color="#D32F2F", text_color="#FFFFFF",
                font=ctk.CTkFont(size=13, weight="bold"),
                command=self.delete_current_phone
            )
            del_btn.pack(side="left", padx=5)

        save_btn = ctk.CTkButton(
            btn_bar, text="💾 Save Record", height=42, width=150,
            corner_radius=10, fg_color=COLORS['primary'],
            hover_color=COLORS['primary_light'],
            font=ctk.CTkFont(size=13, weight="bold"),
            command=lambda: self.save_form(close_dialog=True)
        )
        save_btn.pack(side="right", padx=5)

        if not self.phone_data:
            save_add_btn = ctk.CTkButton(
                btn_bar, text="⚡ Save & Add Next", height=42, width=170,
                corner_radius=10, fg_color=COLORS['secondary'],
                hover_color=COLORS['secondary_hover'],
                text_color="#FFFFFF",
                font=ctk.CTkFont(size=12, weight="bold"),
                command=lambda: self.save_form(close_dialog=False)
            )
            save_add_btn.pack(side="right", padx=5)

        cancel_btn = ctk.CTkButton(
            btn_bar, text="Cancel", height=42, width=90,
            corner_radius=10, fg_color=COLORS['primary_dark'],
            hover_color=COLORS['primary'],
            command=self.destroy
        )
        cancel_btn.pack(side="right", padx=5)

    def delete_current_phone(self):
        if not self.phone_data:
            return
        if not self.user or self.user.get('role') != 'Admin':
            messagebox.showerror("Permission Denied", "Only Admin users are permitted to delete IP phone records.", parent=self)
            return
        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this IP phone record?", parent=self):
            try:
                db.delete_phone(self.phone_data['phone_id'])
                messagebox.showinfo("Success", "IP Phone record deleted successfully!", parent=self)
                if self.on_save_success:
                    self.on_save_success()
                self.destroy()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete phone record:\n{str(e)}", parent=self)

    def fill_last_used_entry(self):
        """Auto-populate Department, Brand, Model, Designation, and Radio Buttons from last entry."""
        last = form_history.get_last_entry()
        if not last:
            messagebox.showinfo("Smart Memory", "No previous entry record found in history!", parent=self)
            return

        if last.get('department'):
            self.dept_entry.delete(0, tk.END)
            self.dept_entry.insert(0, last['department'])
        if last.get('brand'):
            self.brand_combo.set(last['brand'])
        if last.get('model'):
            self.model_combo.set(last['model'])
        if last.get('position'):
            self.pos_combo.set(last['position'])
        if last.get('status'):
            self.status_var.set(last['status'])
        if last.get('delivery_status'):
            self.delivery_var.set(last['delivery_status'])
        if last.get('configure_status'):
            self.config_var.set(last['configure_status'])

    def open_location_selector(self):
        def on_selected(name):
            self.dept_entry.delete(0, tk.END)
            self.dept_entry.insert(0, name)

        LocationSearchDialog(self, self.departments, on_selected)

    def open_ip_in_browser(self):
        """Open the IP address in the default web browser to check if the phone is active."""
        import webbrowser
        ip = self.ip_entry.get().strip()
        if not ip:
            messagebox.showwarning("Warning", "Please enter an IP Address first!", parent=self)
            return
        url = f"http://{ip}"
        webbrowser.open(url)

    def open_extension_in_browser(self):
        """Open extension page in browser: /extension/add for new record, /extension for existing record."""
        import webbrowser
        if self.phone_data:
            webbrowser.open("http://10.9.1.18/extension")
        else:
            webbrowser.open("http://10.9.1.18/extension/add")

    def populate_form(self):
        p = self.phone_data
        dept = p.get('dept_name') or p.get('department')
        if dept and str(dept).lower() not in ('none', 'null', ''):
            self.dept_entry.delete(0, tk.END)
            self.dept_entry.insert(0, str(dept))
        if p.get('extension') and str(p.get('extension')).lower() not in ('none', 'null', ''):
            self.ext_entry.delete(0, tk.END)
            self.ext_entry.insert(0, str(p['extension']))
        if p.get('ip_address') and str(p.get('ip_address')).lower() not in ('none', 'null', ''):
            self.ip_entry.delete(0, tk.END)
            self.ip_entry.insert(0, str(p['ip_address']))
        if p.get('caller_id') and str(p.get('caller_id')).lower() not in ('none', 'null', ''):
            self.caller_entry.delete(0, tk.END)
            self.caller_entry.insert(0, str(p['caller_id']))
        if p.get('employee_id') and str(p.get('employee_id')).lower() not in ('none', 'null', ''):
            self.empid_entry.delete(0, tk.END)
            self.empid_entry.insert(0, str(p['employee_id']))
        if p.get('employee_name') and str(p.get('employee_name')).lower() not in ('none', 'null', ''):
            self.name_entry.delete(0, tk.END)
            self.name_entry.insert(0, str(p['employee_name']))
        if p.get('phone_set_serial_no') and str(p.get('phone_set_serial_no')).lower() not in ('none', 'null', ''):
            self.serial_entry.delete(0, tk.END)
            self.serial_entry.insert(0, str(p['phone_set_serial_no']))
        if p.get('position') and str(p.get('position')).lower() not in ('none', 'null', ''):
            self.pos_combo.set(str(p['position']))
        else:
            self.pos_combo.set("None")
        if p.get('brand'):
            self.brand_combo.set(p['brand'])
        if p.get('model') and str(p.get('model')).lower() not in ('none', 'null', ''):
            self.model_combo.set(str(p['model']))
        if p.get('status'):
            self.status_var.set(p['status'])
        if p.get('delivery_status'):
            self.delivery_var.set(p['delivery_status'])
        if p.get('configure_status'):
            self.config_var.set(p['configure_status'])

    def save_form(self, close_dialog=True):
        dept_name = self.dept_entry.get().strip()
        ip_address = self.ip_entry.get().strip()

        if not dept_name or not ip_address or dept_name == "Select Location":
            messagebox.showwarning("Warning", "Department and IP Address are required fields!", parent=self)
            return

        def _val(entry_widget):
            v = entry_widget.get().strip() if hasattr(entry_widget, 'get') else str(entry_widget).strip()
            if not v or v == "Select Location" or v.lower() in ("none", "null"):
                return None
            return v

        dept_id = None
        matched_dept = next((d for d in self.departments if d['dept_name'].lower() == dept_name.lower()), None)
        if matched_dept:
            dept_id = matched_dept['dept_id']

        pos_val = self.pos_combo.get().strip()
        if not pos_val or pos_val.lower() in ("none", "null"):
            pos_val = None

        model_val = self.model_combo.get().strip()
        if not model_val or model_val.lower() in ("none", "null"):
            model_val = None

        phone_payload = {
            'dept_id': dept_id,
            'department': dept_name,
            'extension': _val(self.ext_entry),
            'ip_address': ip_address,
            'caller_id': _val(self.caller_entry),
            'employee_id': _val(self.empid_entry),
            'employee_name': _val(self.name_entry),
            'phone_set_serial_no': _val(self.serial_entry),
            'position': pos_val,
            'brand': self.brand_combo.get().strip() or 'Fanvil',
            'model': model_val,
            'status': self.status_var.get() or 'Inactive',
            'delivery_status': self.delivery_var.get() or 'Pending',
            'configure_status': self.config_var.get() or 'ON',
            'created_by': self.user['user_id']
        }

        try:
            if self.phone_data:
                db.update_phone(self.phone_data['phone_id'], phone_payload)
                form_history.record_phone_entry(phone_payload)
                messagebox.showinfo("Success", "IP Phone record updated successfully!", parent=self)
            else:
                db.add_phone(phone_payload)
                form_history.record_phone_entry(phone_payload)
                messagebox.showinfo("Success", "New IP Phone record added successfully!", parent=self)

            if self.on_save_success:
                self.on_save_success()

            if close_dialog:
                self.destroy()
            else:
                # Rapid entry mode: keep Department, Brand, Model, Designation
                # Clear IP, Ext, Name, Serial, EmpID, CallerID
                self.ip_entry.delete(0, tk.END)
                self.ext_entry.delete(0, tk.END)
                self.name_entry.delete(0, tk.END)
                self.serial_entry.delete(0, tk.END)
                self.empid_entry.delete(0, tk.END)
                self.caller_entry.delete(0, tk.END)
                self.ip_entry.focus()
        except Exception as e:
            messagebox.showerror("Error", f"Database error while saving record:\n{str(e)}", parent=self)
