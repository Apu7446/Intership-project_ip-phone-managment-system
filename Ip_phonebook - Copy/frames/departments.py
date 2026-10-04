"""
Departments Frame — SBAC IP Phone Management System
Master Head Office Division, Branch & Sub-Branch Manager with Assigned Phone Counts.
Interactive Category Filter (HO Division, Branch, Sub-Branch), Live Search, and Multi-Option Sorting.
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox
from config import COLORS, setup_treeview_style
import db


class DepartmentsFrame(ctk.CTkFrame):
    DEPT_COLUMNS = [
        ("id", "ID", 80, "center"),
        ("name", "Department / Location Name", 420, "center"),
        ("type", "Category Type", 200, "center"),
        ("phones", "Assigned IP Phones", 180, "center"),
        ("status", "Status", 140, "center")
    ]

    def __init__(self, parent, user, app_ref=None):
        super().__init__(parent, fg_color=COLORS['bg_dark'])
        self.user = user
        self.app_ref = app_ref
        self.sort_col = "name"
        self.sort_reverse = False
        self._last_data_sig = None
        self._sync_timer = None
        self.build_ui()
        self.load_departments()
        self.bind("<Destroy>", self._on_destroy)
        self._start_auto_sync()

    def build_ui(self):
        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(15, 10))

        ctk.CTkLabel(header, text="🏢  Head Office Divisions & Branch Master",
                     font=ctk.CTkFont(size=22, weight="bold"),
                     text_color=COLORS['text_white']).pack(side="left")

        if self.user.get('role') == 'Admin':
            add_btn = ctk.CTkButton(
                header, text="➕ Add Department/Branch", width=180, height=36,
                corner_radius=18,
                fg_color=COLORS['primary'], hover_color=COLORS['primary_light'],
                text_color=COLORS['text_white'],
                font=ctk.CTkFont(size=12, weight="bold"),
                command=self.show_add_dialog)
            add_btn.pack(side="right", padx=(8, 0))

            edit_btn = ctk.CTkButton(
                header, text="✏️ Edit Department", width=150, height=36,
                corner_radius=18,
                fg_color=COLORS['primary_dark'], hover_color=COLORS['primary'],
                border_width=1, border_color=COLORS['border'],
                text_color=COLORS['text_light'],
                font=ctk.CTkFont(size=12, weight="bold"),
                command=self.edit_selected_department)
            edit_btn.pack(side="right")

        # ── Category Filter & Search Card ──
        filter_frame = ctk.CTkFrame(self, fg_color=COLORS['bg_card'], corner_radius=14,
                                    border_width=1, border_color=COLORS['border'])
        filter_frame.pack(fill="x", padx=20, pady=(0, 10))

        filter_row = ctk.CTkFrame(filter_frame, fg_color="transparent")
        filter_row.pack(fill="x", padx=15, pady=10)

        ctk.CTkLabel(filter_row, text="📍 Category Filter:",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color=COLORS['secondary']).pack(side="left", padx=(0, 12))

        self.category_var = ctk.StringVar(value="All")
        categories = [
            ("All", "All Categories"),
            ("HO Division", "Head Office Division"),
            ("Branch", "Branch"),
            ("Sub-Branch", "Sub-Branch")
        ]

        for val, label in categories:
            ctk.CTkRadioButton(
                filter_row, text=label,
                variable=self.category_var, value=val,
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=COLORS['text_light'],
                fg_color=COLORS['primary'],
                hover_color=COLORS['primary_light'],
                radiobutton_width=18, radiobutton_height=18,
                command=self.load_departments
            ).pack(side="left", padx=(0, 14))

        # Search Box
        ctk.CTkLabel(filter_row, text="🔍 Search:",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=COLORS['text_light']).pack(side="left", padx=(8, 4))

        self.dept_search_var = ctk.StringVar()
        dept_search_entry = ctk.CTkEntry(
            filter_row, textvariable=self.dept_search_var,
            placeholder_text="Type location name...",
            placeholder_text_color=COLORS['text_muted'],
            height=30, width=150, corner_radius=8,
            fg_color=COLORS['entry_bg'], border_color=COLORS['border'],
            text_color=COLORS['text_white'],
            font=ctk.CTkFont(size=11)
        )
        dept_search_entry.pack(side="left", padx=(0, 6))
        dept_search_entry.bind("<KeyRelease>", lambda e: self.load_departments())

        # Sort Dropdown Combo Box
        ctk.CTkLabel(filter_row, text="🔃 Sort By:",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=COLORS['text_light']).pack(side="left", padx=(8, 4))

        self.sort_var = ctk.StringVar(value="Name (A ➔ Z)")
        sort_combo = ctk.CTkComboBox(
            filter_row, variable=self.sort_var,
            values=[
                "Name (A ➔ Z)",
                "Name (Z ➔ A)",
                "Phones (High ➔ Low)",
                "Phones (Low ➔ High)",
                "ID (1 ➔ N)",
                "ID (N ➔ 1)",
                "Category Type"
            ],
            width=145, height=30, corner_radius=8,
            fg_color=COLORS['entry_bg'], border_color=COLORS['border'],
            text_color=COLORS['text_white'], button_color=COLORS['primary'],
            dropdown_fg_color=COLORS['bg_card'],
            font=ctk.CTkFont(size=11),
            command=self.on_sort_dropdown_change
        )
        sort_combo.pack(side="left", padx=(0, 6))

        # Main Table Container
        card = ctk.CTkFrame(self, fg_color=COLORS['bg_card'], corner_radius=14,
                            border_width=1, border_color=COLORS['border'])
        card.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        top_info = ctk.CTkFrame(card, fg_color="transparent")
        top_info.pack(fill="x", padx=15, pady=(8, 2))

        self.count_lbl = ctk.CTkLabel(top_info, text="0 locations",
                                      font=ctk.CTkFont(size=12, weight="bold"),
                                      text_color=COLORS['secondary'])
        self.count_lbl.pack(side="left")

        ctk.CTkLabel(top_info, text="💡 Click column header to sort (▲/▼) • Double-click to view phones • Right-click for options",
                     font=ctk.CTkFont(size=11),
                     text_color=COLORS['text_muted']).pack(side="right")

        setup_treeview_style()

        table_box = ctk.CTkFrame(card, fg_color="transparent")
        table_box.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        columns = [c[0] for c in self.DEPT_COLUMNS]
        self.tree = ttk.Treeview(table_box, columns=columns, show="headings", selectmode="browse")

        for col_id, title, width, align in self.DEPT_COLUMNS:
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

        self.tree.bind("<Double-1>", lambda e: self.on_double_click())
        self.tree.bind("<Button-3>", lambda e: self.on_right_click_row(e))

    def update_headers(self):
        for col_id, title, width, align in self.DEPT_COLUMNS:
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
        self.load_departments()

    def on_sort_dropdown_change(self, choice):
        if choice == "Name (A ➔ Z)":
            self.sort_col = "name"
            self.sort_reverse = False
        elif choice == "Name (Z ➔ A)":
            self.sort_col = "name"
            self.sort_reverse = True
        elif choice == "Phones (High ➔ Low)":
            self.sort_col = "phones"
            self.sort_reverse = True
        elif choice == "Phones (Low ➔ High)":
            self.sort_col = "phones"
            self.sort_reverse = False
        elif choice == "ID (1 ➔ N)":
            self.sort_col = "id"
            self.sort_reverse = False
        elif choice == "ID (N ➔ 1)":
            self.sort_col = "id"
            self.sort_reverse = True
        elif choice == "Category Type":
            self.sort_col = "type"
            self.sort_reverse = False
        self.update_headers()
        self.load_departments()

    def load_departments(self):
        selected_cat = self.category_var.get()
        search_term = self.dept_search_var.get().strip().lower()

        self._dept_load_gen = getattr(self, '_dept_load_gen', 0) + 1
        current_gen = self._dept_load_gen

        def _bg_worker():
            try:
                depts = db.get_department_counts()
                sig = (db.get_departments_data_signature(), db.get_phones_data_signature())
                err = None
            except Exception as e:
                depts = []
                sig = None
                err = e

            if self.winfo_exists():
                self.after(0, lambda: self._on_departments_loaded(current_gen, depts, sig, err, selected_cat, search_term))

        import threading
        threading.Thread(target=_bg_worker, daemon=True).start()

    def _on_departments_loaded(self, gen, depts, sig, err, selected_cat, search_term):
        if not self.winfo_exists() or gen != getattr(self, '_dept_load_gen', 0):
            return
        if err:
            self.count_lbl.configure(text=f"Error: {err}")
            return

        for item in self.tree.get_children():
            self.tree.delete(item)

        filtered_depts = []
        for d in depts:
            if selected_cat != "All" and d['dept_type'] != selected_cat:
                continue
            if search_term and search_term not in d['dept_name'].lower():
                continue
            filtered_depts.append(d)

        if self.sort_col == "name":
            filtered_depts.sort(key=lambda x: str(x['dept_name']).lower(), reverse=self.sort_reverse)
        elif self.sort_col == "type":
            filtered_depts.sort(key=lambda x: (str(x['dept_type']).lower(), str(x['dept_name']).lower()), reverse=self.sort_reverse)
        elif self.sort_col == "phones":
            filtered_depts.sort(key=lambda x: x['phone_count'], reverse=self.sort_reverse)
        elif self.sort_col == "id":
            filtered_depts.sort(key=lambda x: x['dept_id'], reverse=self.sort_reverse)
        elif self.sort_col == "status":
            filtered_depts.sort(key=lambda x: str(x['status']).lower(), reverse=self.sort_reverse)

        for d in filtered_depts:
            status_str = "🟢 Active" if d['status'] == 'Active' else "🔴 Inactive"
            self.tree.insert("", "end", values=(
                d['dept_id'], d['dept_name'], d['dept_type'], d['phone_count'], status_str
            ))

        self.count_lbl.configure(text=f"🏢 Total {len(filtered_depts)} locations found")
        if sig:
            self._last_data_sig = sig

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

            # Check if search entry has active focus
            has_focus = False
            try:
                focused = self.focus_get()
                if focused and hasattr(self, 'dept_search_var'):
                    has_focus = bool(self.dept_search_var.get().strip())
            except Exception:
                pass

            if not has_focus:
                self._sync_in_progress = True
                def _bg_sig():
                    try:
                        sig = (db.get_departments_data_signature(), db.get_phones_data_signature())
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
                    self.load_departments()
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

    def get_selected_department(self):
        selected = self.tree.selection()
        if not selected:
            return None
        vals = self.tree.item(selected[0])['values']
        return {
            'dept_id': vals[0],
            'dept_name': str(vals[1]),
            'dept_type': str(vals[2]),
            'phone_count': vals[3],
            'status': 'Active' if 'Active' in str(vals[4]) else 'Inactive'
        }

    def on_double_click(self):
        dept = self.get_selected_department()
        if not dept:
            return
        if self.app_ref:
            self.app_ref.show_location_detail(dept['dept_type'], dept['dept_id'], dept['dept_name'])

    def edit_selected_department(self):
        dept = self.get_selected_department()
        if not dept:
            messagebox.showwarning("Selection Required", "Please select a department from the table to edit.", parent=self)
            return
        DepartmentDialog(self, dept_data=dept, on_save_success=self.load_departments)

    def on_right_click_row(self, event):
        iid = self.tree.identify_row(event.y)
        if iid:
            self.tree.selection_set(iid)
            dept = self.get_selected_department()
            if not dept:
                return

            menu = tk.Menu(self, tearoff=0, bg="#251528", fg="#FFFFFF", activebackground="#85175F", font=("Segoe UI", 10))
            menu.add_command(
                label=f"📂 View Assigned Phones ({dept['dept_name']})",
                command=lambda: self.app_ref.show_location_detail(dept['dept_type'], dept['dept_id'], dept['dept_name']) if self.app_ref else None
            )
            if self.user.get('role') == 'Admin':
                menu.add_separator()
                menu.add_command(
                    label="✏️ Edit Department Details",
                    command=lambda: DepartmentDialog(self, dept_data=dept, on_save_success=self.load_departments)
                )

            menu.post(event.x_root, event.y_root)

    def show_add_dialog(self):
        DepartmentDialog(self, on_save_success=self.load_departments)


class DepartmentDialog(ctk.CTkToplevel):
    def __init__(self, parent, dept_data=None, on_save_success=None):
        super().__init__(parent)
        self.parent = parent
        self.dept_data = dept_data
        self.on_save_success = on_save_success

        title_txt = "✏️ Edit Department" if dept_data else "➕ Add New Department / Branch"
        self.title(title_txt)
        self.geometry("450x330")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.configure(fg_color=COLORS['bg_dark'])

        # Center
        self.update_idletasks()
        x = (self.winfo_screenwidth() - 450) // 2
        y = (self.winfo_screenheight() - 330) // 2
        self.geometry(f"+{x}+{y}")

        self.build_ui()

    def build_ui(self):
        card = ctk.CTkFrame(self, fg_color=COLORS['bg_card'], corner_radius=14,
                            border_width=1, border_color=COLORS['border'])
        card.pack(fill="both", expand=True, padx=15, pady=15)

        title_txt = "✏️ Edit Department / Location" if self.dept_data else "Department / Location Info"
        ctk.CTkLabel(card, text=title_txt,
                     font=ctk.CTkFont(size=16, weight="bold"),
                     text_color=COLORS['secondary']).pack(pady=(15, 15))

        # Dept Name
        ctk.CTkLabel(card, text="Location Name *", font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=COLORS['text_light']).pack(anchor="w", padx=25, pady=(0, 2))
        self.name_entry = ctk.CTkEntry(card, height=36, corner_radius=8,
                                       fg_color=COLORS['entry_bg'], border_color=COLORS['border'],
                                       text_color=COLORS['text_white'])
        self.name_entry.pack(fill="x", padx=25, pady=(0, 12))

        # Dept Type
        ctk.CTkLabel(card, text="Category Type *", font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=COLORS['text_light']).pack(anchor="w", padx=25, pady=(0, 2))
        self.type_combo = ctk.CTkComboBox(card, values=['Branch', 'Sub-Branch', 'HO Division'],
                                          height=36, corner_radius=8,
                                          fg_color=COLORS['entry_bg'], border_color=COLORS['border'],
                                          text_color=COLORS['text_white'], button_color=COLORS['primary'],
                                          dropdown_fg_color=COLORS['bg_card'])
        self.type_combo.pack(fill="x", padx=25, pady=(0, 18))

        if self.dept_data:
            self.name_entry.insert(0, self.dept_data.get('dept_name', ''))
            if self.dept_data.get('dept_type'):
                self.type_combo.set(self.dept_data['dept_type'])

        # Action Buttons Row
        btn_row = ctk.CTkFrame(card, fg_color="transparent")
        btn_row.pack(fill="x", padx=25, pady=(0, 10))

        if self.dept_data:
            del_btn = ctk.CTkButton(
                btn_row, text="🗑️ Delete", height=40, width=105,
                corner_radius=10, fg_color=COLORS['danger'],
                hover_color="#D32F2F", text_color="#FFFFFF",
                font=ctk.CTkFont(size=12, weight="bold"),
                command=self.delete_dept
            )
            del_btn.pack(side="left", padx=(0, 10))

        save_btn = ctk.CTkButton(
            btn_row, text="💾 Save Location", height=40,
            corner_radius=10, fg_color=COLORS['primary'],
            hover_color=COLORS['primary_light'],
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.save
        )
        save_btn.pack(side="right", fill="x", expand=True)

    def delete_dept(self):
        if not self.dept_data:
            return
        dept_name = self.dept_data.get('dept_name', '')
        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete location '{dept_name}'?", parent=self):
            try:
                db.delete_department(self.dept_data['dept_id'])
                messagebox.showinfo("Success", "Department deleted successfully!", parent=self)
                if self.on_save_success:
                    self.on_save_success()
                self.destroy()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete location:\n{str(e)}", parent=self)

    def save(self):
        name = self.name_entry.get().strip()
        dtype = self.type_combo.get().strip()
        if not name:
            messagebox.showwarning("Warning", "Location name is required!", parent=self)
            return

        try:
            if self.dept_data:
                status = self.dept_data.get('status', 'Active')
                db.update_department(self.dept_data['dept_id'], name, dtype, status)
                messagebox.showinfo("Success", "Department updated successfully!", parent=self)
            else:
                db.add_department(name, dtype)
                messagebox.showinfo("Success", "Department added successfully!", parent=self)

            if self.on_save_success:
                self.on_save_success()
            self.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save location:\n{str(e)}", parent=self)
