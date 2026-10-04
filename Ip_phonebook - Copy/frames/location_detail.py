"""
Location Detail Frame — SBAC IP Phone Management System
Drill-Down View: Displays all IP Phone entries assigned to a specific Branch or HO Division.
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox
from config import COLORS, setup_treeview_style
import db


class LocationDetailFrame(ctk.CTkFrame):
    COLUMNS_DEF = [
        ("id", "#", 65, "center"),
        ("ip", "IP Address", 150, "center"),
        ("ext", "Extension", 120, "center"),
        ("caller_id", "Caller ID", 130, "center"),
        ("emp_id", "Emp ID", 100, "center"),
        ("name", "Employee Name", 270, "w"),
        ("position", "Position / Designation", 270, "w"),
        ("brand_model", "Brand & Model", 150, "center"),
        ("status", "Status", 125, "center"),
        ("delivery", "Delivery", 130, "center")
    ]

    def __init__(self, parent, user, location_type, location_id, location_name, on_back):
        super().__init__(parent, fg_color=COLORS['bg_dark'])
        self.user = user
        self.location_type = location_type
        self.location_id = location_id
        self.location_name = location_name
        self.on_back = on_back
        self.sort_col = "id"
        self.sort_reverse = False
        self._last_data_sig = None
        self._sync_timer = None

        self.build_ui()
        self.load_location_phones()
        self.bind("<Destroy>", self._on_destroy)
        self._start_auto_sync()

    def build_ui(self):
        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(15, 10))

        back_btn = ctk.CTkButton(
            header, text="⬅ Back to Departments", width=160, height=36,
            corner_radius=18,
            fg_color=COLORS['primary_dark'], hover_color=COLORS['primary'],
            border_width=1, border_color=COLORS['border'],
            text_color=COLORS['text_light'],
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self.on_back)
        back_btn.pack(side="left", padx=(0, 15))

        title_icon = "🏛️" if self.location_type == "HO Division" else "🏢"
        ctk.CTkLabel(header, text=f"{title_icon}  {self.location_name} ({self.location_type})",
                     font=ctk.CTkFont(size=20, weight="bold"),
                     text_color=COLORS['text_white']).pack(side="left")

        # Action Buttons on Header Right
        edit_btn = ctk.CTkButton(
            header, text="✏️ Edit Phone", width=125, height=36,
            corner_radius=18,
            fg_color=COLORS['primary'], hover_color=COLORS['primary_light'],
            text_color=COLORS['text_white'],
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self.edit_selected_phone
        )
        edit_btn.pack(side="right", padx=(8, 0))

        add_btn = ctk.CTkButton(
            header, text="➕ Add Phone", width=125, height=36,
            corner_radius=18,
            fg_color=COLORS['primary_dark'], hover_color=COLORS['primary'],
            border_width=1, border_color=COLORS['border'],
            text_color=COLORS['text_light'],
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self.add_phone_for_location
        )
        add_btn.pack(side="right", padx=(8, 0))

        ping_btn = ctk.CTkButton(
            header, text="🌐 Ping Tool", width=105, height=36,
            corner_radius=18,
            fg_color=COLORS['primary_dark'], hover_color=COLORS['primary'],
            border_width=1, border_color=COLORS['secondary'],
            text_color=COLORS['secondary'],
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self.open_ping_tool_selected
        )
        ping_btn.pack(side="right", padx=(8, 0))

        # Container
        card = ctk.CTkFrame(self, fg_color=COLORS['bg_card'], corner_radius=14,
                            border_width=1, border_color=COLORS['border'])
        card.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        top_info = ctk.CTkFrame(card, fg_color="transparent")
        top_info.pack(fill="x", padx=15, pady=(10, 5))

        self.count_lbl = ctk.CTkLabel(top_info, text="Loading phones...",
                                      font=ctk.CTkFont(size=12, weight="bold"),
                                      text_color=COLORS['secondary'])
        self.count_lbl.pack(side="left")

        ctk.CTkLabel(top_info, text="💡 Click column header to sort (▲/▼) • Double-click to Edit • Right-click for IP Ping Tool",
                     font=ctk.CTkFont(size=11),
                     text_color=COLORS['text_muted']).pack(side="right")

        setup_treeview_style()

        table_box = ctk.CTkFrame(card, fg_color="transparent")
        table_box.pack(fill="both", expand=True, padx=10, pady=10)

        columns = [c[0] for c in self.COLUMNS_DEF]
        self.tree = ttk.Treeview(table_box, columns=columns, show="headings", selectmode="browse")

        for col_id, title, width, align in self.COLUMNS_DEF:
            self.tree.column(col_id, width=width, minwidth=width, anchor=align, stretch=False)

        self.update_headers()

        tree_scroll_y = ttk.Scrollbar(table_box, orient="vertical", command=self.tree.yview)
        tree_scroll_x = ttk.Scrollbar(table_box, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=tree_scroll_y.set, xscrollcommand=tree_scroll_x.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        tree_scroll_y.grid(row=0, column=1, sticky="ns")
        tree_scroll_x.grid(row=1, column=0, sticky="ew")

        table_box.grid_rowconfigure(0, weight=1)
        table_box.grid_columnconfigure(0, weight=1)

        # Alternating row colors
        self.tree.tag_configure("even_row", background="#1E1020", foreground="#FFFFFF")
        self.tree.tag_configure("odd_row",  background="#2A1530", foreground="#FFFFFF")

        # Double-click and Right-click bindings
        self.tree.bind("<Double-1>", lambda e: self.on_double_click_row())
        self.tree.bind("<Button-3>", lambda e: self.on_right_click_row(e))

    def update_headers(self):
        for col_id, title, width, align in self.COLUMNS_DEF:
            if self.sort_col == col_id:
                arrow = " ▼" if self.sort_reverse else " ▲"
            else:
                arrow = " ↕"
            self.tree.heading(
                col_id,
                text=f"{title}{arrow}",
                anchor="center",
                command=lambda c=col_id: self.sort_by_column(c)
            )

    def sort_by_column(self, col):
        if self.sort_col == col:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_col = col
            self.sort_reverse = False

        self.update_headers()
        self.render_location_phones()

    def get_sort_key(self, p, col):
        def _ip_tuple(ip):
            if not ip:
                return (999, 999, 999, 999)
            try:
                parts = [int(x) for x in str(ip).strip().split('.')]
                if len(parts) == 4:
                    return tuple(parts)
            except Exception:
                pass
            return (999, 999, 999, 999)

        def _num_or_str(v):
            if v is None:
                return ""
            s = str(v).strip()
            if s.isdigit():
                return int(s)
            return s.lower()

        if col == "id":
            return p.get('phone_id', 0)
        elif col == "ip":
            return _ip_tuple(p.get('ip_address'))
        elif col == "ext":
            return _num_or_str(p.get('extension'))
        elif col == "caller_id":
            return _num_or_str(p.get('caller_id'))
        elif col == "emp_id":
            return _num_or_str(p.get('employee_id'))
        elif col == "name":
            return str(p.get('employee_name') or '').lower()
        elif col == "position":
            return str(p.get('position') or '').lower()
        elif col == "brand_model":
            return f"{p.get('brand', '')} {p.get('model', '')}".strip().lower()
        elif col == "status":
            return str(p.get('status') or '').lower()
        elif col == "delivery":
            return str(p.get('delivery_status') or '').lower()
        return p.get('phone_id', 0)

    def load_location_phones(self):
        self._loc_load_gen = getattr(self, '_loc_load_gen', 0) + 1
        current_gen = self._loc_load_gen

        def _bg_worker():
            try:
                sig = db.get_phones_data_signature(location=self.location_name)
                phones = db.get_filtered_phones(location=self.location_name)
                err = None
            except Exception as e:
                sig = None
                phones = []
                err = e

            if self.winfo_exists():
                self.after(0, lambda: self._on_location_phones_loaded(current_gen, phones, sig, err))

        import threading
        threading.Thread(target=_bg_worker, daemon=True).start()

    def _on_location_phones_loaded(self, gen, phones, sig, err):
        if not self.winfo_exists() or gen != getattr(self, '_loc_load_gen', 0):
            return
        if err:
            return
        if sig:
            self._last_data_sig = sig
        self.current_phones = phones or []
        self.render_location_phones()

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

            self._sync_in_progress = True
            def _bg_sig():
                try:
                    sig = db.get_phones_data_signature(location=self.location_name)
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
                    self.load_location_phones()
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

    def render_location_phones(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        self.current_phones.sort(
            key=lambda p: self.get_sort_key(p, self.sort_col),
            reverse=self.sort_reverse
        )

        self.count_lbl.configure(text=f"📋 Total {len(self.current_phones)} IP phones assigned to {self.location_name}")

        for idx, p in enumerate(self.current_phones):
            brand_mod = f"{p.get('brand', '')} {p.get('model', '')}".strip()
            status_icon = "🟢 Active" if p.get('status') == 'Active' else "🔴 Inactive"
            deliv_icon = "📦 Delivered" if p.get('delivery_status') == 'Delivered' else "⏳ Pending"
            row_tag = "even_row" if idx % 2 == 0 else "odd_row"

            self.tree.insert("", "end", iid=str(p['phone_id']), values=(
                idx + 1, p.get('ip_address') or '', p.get('extension') or '',
                p.get('caller_id') or '', p.get('employee_id') or '',
                p.get('employee_name') or '', p.get('position') or '',
                brand_mod, status_icon, deliv_icon
            ), tags=(row_tag,))

    def get_selected_phone(self):
        selected = self.tree.selection()
        if not selected:
            return None
        phone_id_str = selected[0]
        return next((p for p in self.current_phones if str(p['phone_id']) == phone_id_str), None)

    def on_double_click_row(self):
        phone = self.get_selected_phone()
        if not phone:
            return
        self.show_edit_form(phone)

    def edit_selected_phone(self):
        phone = self.get_selected_phone()
        if not phone:
            messagebox.showwarning("Selection Required", "Please select an IP phone from the table to edit.", parent=self)
            return
        self.show_edit_form(phone)

    def show_edit_form(self, phone):
        from frames.phones import PhoneFormDialog
        PhoneFormDialog(self, user=self.user, phone_data=phone, on_save_success=self.load_location_phones)

    def add_phone_for_location(self):
        from frames.phones import PhoneFormDialog
        dialog = PhoneFormDialog(self, user=self.user, on_save_success=self.load_location_phones)
        dialog.dept_entry.delete(0, 'end')
        dialog.dept_entry.insert(0, self.location_name)

    def on_right_click_row(self, event):
        iid = self.tree.identify_row(event.y)
        if iid:
            self.tree.selection_set(iid)
            phone = next((p for p in self.current_phones if str(p['phone_id']) == iid), None)
            if not phone:
                return

            menu = tk.Menu(self, tearoff=0, bg="#251528", fg="#FFFFFF", activebackground="#85175F", font=("Segoe UI", 10))
            ip = phone.get('ip_address')
            if ip:
                menu.add_command(
                    label=f"🌐 Open IP Ping Tool ({ip})",
                    command=lambda: self.open_ping_tool(ip)
                )
            else:
                menu.add_command(
                    label="🌐 Open IP Ping Tool",
                    command=lambda: self.open_ping_tool()
                )

            if self.user.get('role') == 'Admin':
                menu.add_separator()
                menu.add_command(
                    label="✏️ Edit Phone Details",
                    command=lambda: self.show_edit_form(phone)
                )
                menu.add_command(
                    label="🗑️ Delete Phone Record",
                    command=lambda: self.confirm_delete(phone['phone_id'])
                )

            menu.post(event.x_root, event.y_root)

    def open_ping_tool_selected(self):
        phone = self.get_selected_phone()
        ip = phone.get('ip_address', '') if phone else ''
        self.open_ping_tool(ip)

    def open_ping_tool(self, default_ip=""):
        from ip_tool import open_ip_tool
        open_ip_tool(self, default_ip)

    def confirm_delete(self, phone_id):
        if not self.user or self.user.get('role') != 'Admin':
            messagebox.showerror("Permission Denied", "Only Admin users are permitted to delete IP phone records.", parent=self)
            return

        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this IP phone record?", parent=self):
            try:
                db.delete_phone(phone_id)
                self.load_location_phones()
                messagebox.showinfo("Success", "IP Phone record deleted successfully.", parent=self)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete phone:\n{str(e)}", parent=self)
