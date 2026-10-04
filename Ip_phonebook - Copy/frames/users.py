"""
Users Frame — SBAC IP Phone Management System
Admin User Account Control, Role Assignments (Admin / ICT Operator), and Password Reset.
"""

import customtkinter as ctk
from tkinter import ttk, messagebox
from config import COLORS, setup_treeview_style
import db


class UsersFrame(ctk.CTkFrame):
    USER_COLUMNS = [
        ("id", "User ID", 70, "center"),
        ("name", "Full Name", 250, "w"),
        ("username", "Username", 160, "center"),
        ("role", "System Role", 140, "center"),
        ("status", "Account Status", 120, "center")
    ]

    def __init__(self, parent, user):
        super().__init__(parent, fg_color=COLORS['bg_dark'])
        self.user = user
        self.sort_col = "id"
        self.sort_reverse = False
        self.users_data = []
        self.build_ui()
        self.load_users()

    def build_ui(self):
        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(15, 10))

        ctk.CTkLabel(header, text="👤  User Account & Role Management",
                     font=ctk.CTkFont(size=22, weight="bold"),
                     text_color=COLORS['text_white']).pack(side="left")

        if self.user['role'] == 'Admin':
            add_btn = ctk.CTkButton(
                header, text="➕ Add New User", width=140, height=36,
                corner_radius=18,
                fg_color=COLORS['primary'], hover_color=COLORS['primary_light'],
                text_color=COLORS['text_white'],
                font=ctk.CTkFont(size=12, weight="bold"),
                command=self.show_add_dialog)
            add_btn.pack(side="right")

        # Container
        card = ctk.CTkFrame(self, fg_color=COLORS['bg_card'], corner_radius=14,
                            border_width=1, border_color=COLORS['border'])
        card.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        setup_treeview_style()

        columns = [c[0] for c in self.USER_COLUMNS]
        self.tree = ttk.Treeview(card, columns=columns, show="headings", selectmode="browse")

        for col_id, title, width, align in self.USER_COLUMNS:
            self.tree.column(col_id, width=width, anchor=align)

        self.update_headers()

        scrollbar = ttk.Scrollbar(card, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=10)
        scrollbar.pack(side="right", fill="y", padx=(0, 10), pady=10)

        self.tree.bind("<Double-1>", lambda e: self.on_double_click())

    def update_headers(self):
        for col_id, title, width, align in self.USER_COLUMNS:
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
        self.render_users()

    def load_users(self):
        def _bg_users():
            try:
                users = db.get_all_users()
            except Exception:
                users = []
            if self.winfo_exists():
                self.after(0, lambda: self._on_users_loaded(users))

        import threading
        threading.Thread(target=_bg_users, daemon=True).start()

    def _on_users_loaded(self, users):
        if not self.winfo_exists():
            return
        self.users_data = users
        self.render_users()

    def render_users(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        if self.sort_col == "id":
            self.users_data.sort(key=lambda u: u['user_id'], reverse=self.sort_reverse)
        elif self.sort_col == "name":
            self.users_data.sort(key=lambda u: str(u.get('full_name', '')).lower(), reverse=self.sort_reverse)
        elif self.sort_col == "username":
            self.users_data.sort(key=lambda u: str(u.get('username', '')).lower(), reverse=self.sort_reverse)
        elif self.sort_col == "role":
            self.users_data.sort(key=lambda u: str(u.get('role', '')).lower(), reverse=self.sort_reverse)
        elif self.sort_col == "status":
            self.users_data.sort(key=lambda u: str(u.get('status', '')).lower(), reverse=self.sort_reverse)

        for u in self.users_data:
            status_icon = "🟢 Active" if u['status'] == 'Active' else "🔴 Inactive"
            role_icon = "👑 Admin" if u['role'] == 'Admin' else "👤 ICT Operator"
            self.tree.insert("", "end", values=(
                u['user_id'], u['full_name'], u['username'], role_icon, status_icon
            ))

    def on_double_click(self):
        if self.user['role'] != 'Admin':
            return
        selected = self.tree.selection()
        if not selected:
            return
        vals = self.tree.item(selected[0])['values']
        user_id = vals[0]
        users = db.get_all_users()
        target = next((u for u in users if u['user_id'] == user_id), None)
        if target:
            UserFormDialog(self, user_data=target, on_save_success=self.load_users)

    def show_add_dialog(self):
        UserFormDialog(self, on_save_success=self.load_users)


class UserFormDialog(ctk.CTkToplevel):
    def __init__(self, parent, user_data=None, on_save_success=None):
        super().__init__(parent)
        self.parent = parent
        self.user_data = user_data
        self.on_save_success = on_save_success

        title_txt = "✏️ Edit System User" if user_data else "➕ Add New System User"
        self.title(title_txt)
        self.geometry("450x440")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.configure(fg_color=COLORS['bg_dark'])

        # Center
        self.update_idletasks()
        x = (self.winfo_screenwidth() - 450) // 2
        y = (self.winfo_screenheight() - 440) // 2
        self.geometry(f"+{x}+{y}")

        self.build_ui()
        if user_data:
            self.populate_form()

    def build_ui(self):
        card = ctk.CTkFrame(self, fg_color=COLORS['bg_card'], corner_radius=14,
                            border_width=1, border_color=COLORS['border'])
        card.pack(fill="both", expand=True, padx=15, pady=15)

        title_txt = "✏️ Edit User Account" if self.user_data else "➕ Create User Account"
        ctk.CTkLabel(card, text=title_txt, font=ctk.CTkFont(size=16, weight="bold"),
                     text_color=COLORS['secondary']).pack(pady=(15, 10))

        # Full Name
        ctk.CTkLabel(card, text="Full Name *", font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=COLORS['text_light']).pack(anchor="w", padx=25, pady=(0, 2))
        self.name_entry = ctk.CTkEntry(card, height=36, corner_radius=8,
                                       fg_color=COLORS['entry_bg'], border_color=COLORS['border'],
                                       text_color=COLORS['text_white'])
        self.name_entry.pack(fill="x", padx=25, pady=(0, 10))

        # Username
        ctk.CTkLabel(card, text="Username *", font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=COLORS['text_light']).pack(anchor="w", padx=25, pady=(0, 2))
        self.username_entry = ctk.CTkEntry(card, height=36, corner_radius=8,
                                           fg_color=COLORS['entry_bg'], border_color=COLORS['border'],
                                           text_color=COLORS['text_white'])
        self.username_entry.pack(fill="x", padx=25, pady=(0, 10))

        # Password
        pass_lbl = "New Password (leave empty to keep current)" if self.user_data else "Password *"
        ctk.CTkLabel(card, text=pass_lbl, font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=COLORS['text_light']).pack(anchor="w", padx=25, pady=(0, 2))
        self.password_entry = ctk.CTkEntry(card, height=36, show="•", corner_radius=8,
                                           fg_color=COLORS['entry_bg'], border_color=COLORS['border'],
                                           text_color=COLORS['text_white'])
        self.password_entry.pack(fill="x", padx=25, pady=(0, 10))

        # Role
        ctk.CTkLabel(card, text="System Role *", font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=COLORS['text_light']).pack(anchor="w", padx=25, pady=(0, 2))
        self.role_combo = ctk.CTkComboBox(card, values=['ICT Operator', 'Admin'], height=36, corner_radius=8,
                                          fg_color=COLORS['entry_bg'], border_color=COLORS['border'],
                                          text_color=COLORS['text_white'], button_color=COLORS['primary'],
                                          dropdown_fg_color=COLORS['bg_card'])
        self.role_combo.pack(fill="x", padx=25, pady=(0, 15))

        # Save Button
        save_btn = ctk.CTkButton(
            card, text="💾 Save User Account", height=40,
            corner_radius=10, fg_color=COLORS['primary'],
            hover_color=COLORS['primary_light'],
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.save
        )
        save_btn.pack(fill="x", padx=25)

    def populate_form(self):
        u = self.user_data
        self.name_entry.insert(0, u['full_name'])
        self.username_entry.insert(0, u['username'])
        self.role_combo.set(u['role'])

    def save(self):
        name = self.name_entry.get().strip()
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        role = self.role_combo.get().strip()

        if not name or not username:
            messagebox.showwarning("Warning", "Name and Username are required!", parent=self)
            return

        if not self.user_data and not password:
            messagebox.showwarning("Warning", "Password is required for new user!", parent=self)
            return

        try:
            if self.user_data:
                db.update_user(self.user_data['user_id'], name, username, role, self.user_data['status'], password or None)
                messagebox.showinfo("Success", "User account updated successfully!", parent=self)
            else:
                db.add_user(name, username, password, role)
                messagebox.showinfo("Success", "User account created successfully!", parent=self)

            if self.on_save_success:
                self.on_save_success()
            self.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save user account:\n{str(e)}", parent=self)
