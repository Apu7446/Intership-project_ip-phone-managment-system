import os
import json
import customtkinter as ctk
from tkinter import messagebox
from config import COLORS, DB_CONFIG, save_server_config
import db

LOGIN_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".remembered_login.json")


class ServerConfigDialog(ctk.CTkToplevel):
    """
    Sleek, Modern SBAC Theme Modal Dialog to configure Server PC IP & Database connection.
    Features:
    1. Enter Server PC Host IP (e.g. 172.19.100.207 or localhost).
    2. Enter MySQL Port (default 3306).
    3. Live 'Test Connection' with immediate visual feedback (Success green / Fail red).
    4. 'Save & Connect' button which persists to server_config.json, re-inits DB, and updates UI.
    """
    def __init__(self, parent, on_saved=None):
        super().__init__(parent)
        self.parent = parent
        self.on_saved = on_saved

        self.title("🖥️ Server PC Connection Setup")
        self.geometry("480x440")
        self.resizable(False, False)
        self.configure(fg_color=COLORS['bg_dark'])
        self.transient(parent)

        # Center on parent
        self.update_idletasks()
        try:
            px = parent.winfo_rootx()
            py = parent.winfo_rooty()
            pw = parent.winfo_width()
            ph = parent.winfo_height()
            w, h = 480, 440
            x = px + (pw - w) // 2
            y = py + (ph - h) // 2
            self.geometry(f"{w}x{h}+{max(0, x)}+{max(0, y)}")
        except Exception:
            pass

        self.build_ui()
        self.grab_set()

    def build_ui(self):
        card = ctk.CTkFrame(self, fg_color=COLORS['bg_card'], corner_radius=16,
                            border_width=1, border_color=COLORS['border'])
        card.pack(fill="both", expand=True, padx=20, pady=20)

        # Header
        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(18, 12))

        ctk.CTkLabel(
            header, text="🖥️  Server PC Connection",
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            text_color=COLORS['text_white']
        ).pack(anchor="w")

        ctk.CTkLabel(
            header, text="Connect client PC to Admin / Host Database over LAN",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=COLORS['text_muted']
        ).pack(anchor="w", pady=(2, 0))

        # Form Fields
        form = ctk.CTkFrame(card, fg_color="transparent")
        form.pack(fill="x", padx=20, pady=(0, 10))

        # Host IP
        ctk.CTkLabel(
            form, text="Server PC IP Address / Hostname *",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=COLORS['text_light']
        ).pack(anchor="w", pady=(0, 4))

        self.host_entry = ctk.CTkEntry(
            form, height=38,
            placeholder_text="e.g. 172.19.100.207 or localhost",
            placeholder_text_color=COLORS['text_muted'],
            corner_radius=8,
            fg_color=COLORS['entry_bg'],
            border_color=COLORS['border'],
            text_color=COLORS['text_white'],
            font=ctk.CTkFont(size=12)
        )
        self.host_entry.pack(fill="x", pady=(0, 4))
        self.host_entry.insert(0, DB_CONFIG.get('host', 'localhost'))

        ctk.CTkLabel(
            form, text="💡 Tip: Main Server PC IP (e.g. 172.19.100.207) or 'localhost'",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color=COLORS['secondary']
        ).pack(anchor="w", pady=(0, 10))

        # Port
        ctk.CTkLabel(
            form, text="MySQL Port (Default 3306)",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=COLORS['text_light']
        ).pack(anchor="w", pady=(0, 4))

        self.port_entry = ctk.CTkEntry(
            form, height=36,
            placeholder_text="3306",
            placeholder_text_color=COLORS['text_muted'],
            corner_radius=8,
            fg_color=COLORS['entry_bg'],
            border_color=COLORS['border'],
            text_color=COLORS['text_white'],
            font=ctk.CTkFont(size=12)
        )
        self.port_entry.pack(fill="x", pady=(0, 12))
        self.port_entry.insert(0, str(DB_CONFIG.get('port', 3306)))

        # Live Status Box
        self.status_label = ctk.CTkLabel(
            card, text="",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=COLORS['info'], wraplength=400, justify="center"
        )
        self.status_label.pack(fill="x", padx=20, pady=(0, 10))

        # Action Buttons
        btn_box = ctk.CTkFrame(card, fg_color="transparent")
        btn_box.pack(fill="x", padx=20, pady=(0, 15))

        test_btn = ctk.CTkButton(
            btn_box, text="⚡ Test Connection", height=38, width=150,
            corner_radius=10,
            fg_color=COLORS['primary_dark'], hover_color=COLORS['primary'],
            border_width=1, border_color=COLORS['secondary'],
            text_color=COLORS['secondary'],
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            command=self.run_test_connection
        )
        test_btn.pack(side="left")

        save_btn = ctk.CTkButton(
            btn_box, text="💾 Save & Connect", height=38, width=150,
            corner_radius=10,
            fg_color=COLORS['primary'], hover_color=COLORS['primary_light'],
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=COLORS['text_white'],
            command=self.save_and_connect
        )
        save_btn.pack(side="right")

    def run_test_connection(self):
        host = self.host_entry.get().strip()
        port = self.port_entry.get().strip() or "3306"

        if not host:
            self.status_label.configure(text="⚠️ Please enter a Server IP address or 'localhost'!", text_color=COLORS['warning'])
            return

        self.status_label.configure(text=f"🔄 Testing connection to {host}:{port}...", text_color=COLORS['info'])
        self.update_idletasks()

        success, msg = db.test_db_connection(host, port=port)
        if success:
            self.status_label.configure(text=f"✅ {msg}", text_color=COLORS['success'])
        else:
            self.status_label.configure(text=f"❌ Failed: {msg[:75]}...", text_color=COLORS['danger'])

    def save_and_connect(self):
        host = self.host_entry.get().strip()
        port = self.port_entry.get().strip() or "3306"

        if not host:
            messagebox.showwarning("Warning", "Server IP cannot be empty!", parent=self)
            return

        # Save to persistent file
        ok = save_server_config(host=host, port=port)
        if not ok:
            messagebox.showerror("Error", "Failed to save server configuration file!", parent=self)
            return

        # Try database init
        db_ok = db.ensure_database()

        if self.on_saved:
            try:
                self.on_saved()
            except Exception:
                pass

        if db_ok:
            messagebox.showinfo(
                "Connected Successfully",
                f"Server connection established successfully!\n\nHost: {host}\nPort: {port}\nDatabase: sbac_ipphone",
                parent=self
            )
        else:
            messagebox.showwarning(
                "Config Saved",
                f"Configuration saved for '{host}:{port}', but database connection could not be fully established.\n\nPlease verify that MySQL is running on the Host PC.",
                parent=self
            )

        self.destroy()


class LoginFrame(ctk.CTkFrame):
    def __init__(self, parent, on_login_success):
        super().__init__(parent, fg_color=COLORS['bg_dark'])
        self.parent = parent
        self.on_login_success = on_login_success

        self.build_ui()
        self.load_remembered_credentials()

    def build_ui(self):
        # Outer Centered Container
        center_box = ctk.CTkFrame(
            self, width=420, height=540,
            fg_color=COLORS['bg_card'],
            corner_radius=18,
            border_width=1,
            border_color=COLORS['border']
        )
        center_box.place(relx=0.5, rely=0.5, anchor="center")
        center_box.pack_propagate(False)

        # Header Badge
        header_frame = ctk.CTkFrame(center_box, fg_color="transparent")
        header_frame.pack(pady=(25, 15))

        logo_label = ctk.CTkLabel(
            header_frame, text="🏛",
            font=ctk.CTkFont(family="Segoe UI", size=44, weight="bold"),
            text_color=COLORS['secondary']
        )
        logo_label.pack()

        title_label = ctk.CTkLabel(
            header_frame, text="SBAC BANK PLC",
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
            text_color=COLORS['text_white']
        )
        title_label.pack(pady=(2, 0))

        sub_label = ctk.CTkLabel(
            header_frame, text="IP Phone Management Portal",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color=COLORS['text_muted']
        )
        sub_label.pack(pady=(2, 0))

        # Inputs Form
        form_frame = ctk.CTkFrame(center_box, fg_color="transparent")
        form_frame.pack(fill="x", padx=40, pady=5)

        # Username
        ctk.CTkLabel(
            form_frame, text="Username",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=COLORS['text_light']
        ).pack(anchor="w", pady=(0, 4))

        self.username_entry = ctk.CTkEntry(
            form_frame, height=38,
            placeholder_text="Enter username...",
            placeholder_text_color=COLORS['text_muted'],
            corner_radius=10,
            fg_color=COLORS['entry_bg'],
            border_color=COLORS['border'],
            text_color=COLORS['text_white'],
            font=ctk.CTkFont(size=13)
        )
        self.username_entry.pack(fill="x", pady=(0, 12))

        # Password
        ctk.CTkLabel(
            form_frame, text="Password",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=COLORS['text_light']
        ).pack(anchor="w", pady=(0, 4))

        self.password_entry = ctk.CTkEntry(
            form_frame, height=38, show="•",
            placeholder_text="Enter password...",
            placeholder_text_color=COLORS['text_muted'],
            corner_radius=10,
            fg_color=COLORS['entry_bg'],
            border_color=COLORS['border'],
            text_color=COLORS['text_white'],
            font=ctk.CTkFont(size=13)
        )
        self.password_entry.pack(fill="x", pady=(0, 8))

        # Remember Me Checkbox
        self.remember_var = ctk.BooleanVar(value=True)
        remember_chk = ctk.CTkCheckBox(
            form_frame, text="Remember login credentials",
            variable=self.remember_var,
            font=ctk.CTkFont(size=11),
            text_color=COLORS['text_muted'],
            fg_color=COLORS['primary'],
            hover_color=COLORS['primary_light']
        )
        remember_chk.pack(anchor="w", pady=(0, 14))

        # Login Button
        login_btn = ctk.CTkButton(
            form_frame, text="🔐 Login to System", height=42,
            corner_radius=12,
            fg_color=COLORS['primary'],
            hover_color=COLORS['primary_light'],
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color=COLORS['text_white'],
            command=self.attempt_login
        )
        login_btn.pack(fill="x")

        # ── 1-Click Server PC Connection Button ──
        self.server_btn = ctk.CTkButton(
            form_frame,
            text=f"🌐 Server IP: {DB_CONFIG.get('host', 'localhost')}",
            height=34,
            corner_radius=10,
            fg_color="transparent",
            hover_color=COLORS['primary_dark'],
            border_width=1,
            border_color=COLORS['border'],
            text_color=COLORS['secondary'],
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            command=self.open_server_dialog
        )
        self.server_btn.pack(fill="x", pady=(12, 0))

        # Bind Enter Key
        self.password_entry.bind("<Return>", lambda event: self.attempt_login())
        self.username_entry.bind("<Return>", lambda event: self.password_entry.focus())

    def open_server_dialog(self):
        """Open Server Connection Configuration modal."""
        ServerConfigDialog(self.parent, on_saved=self.update_server_btn_text)

    def update_server_btn_text(self):
        """Update Server IP button display after configuration changes."""
        if hasattr(self, 'server_btn') and self.server_btn.winfo_exists():
            self.server_btn.configure(text=f"🌐 Server IP: {DB_CONFIG.get('host', 'localhost')}")

    def load_remembered_credentials(self):
        """Auto-fill credentials if previously remembered."""
        if os.path.exists(LOGIN_FILE):
            try:
                with open(LOGIN_FILE, "r") as f:
                    data = json.load(f)
                    if data.get("remember"):
                        self.username_entry.insert(0, data.get("username", ""))
                        self.password_entry.insert(0, data.get("password", ""))
                        self.remember_var.set(True)
            except Exception:
                pass

    def attempt_login(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()

        if not username or not password:
            messagebox.showwarning("Warning", "Please enter both username and password!")
            return

        try:
            user = db.authenticate_user(username, password)
            if user:
                # Handle Remember Me
                if self.remember_var.get():
                    with open(LOGIN_FILE, "w") as f:
                        json.dump({"username": username, "password": password, "remember": True}, f)
                else:
                    if os.path.exists(LOGIN_FILE):
                        os.remove(LOGIN_FILE)

                self.on_login_success(user)
            else:
                messagebox.showerror("Login Failed", "Invalid username or password, or user account is Inactive!")
        except Exception as e:
            err_str = str(e)
            if any(k in err_str.lower() for k in ["can't connect", "connection refused", "timed out", "2003", "access denied"]):
                if messagebox.askyesno(
                    "Server Connection Failed",
                    f"Could not reach MySQL database server at '{DB_CONFIG.get('host')}':\n\n{err_str}\n\nWould you like to configure the Server PC IP address now?"
                ):
                    self.open_server_dialog()
                    return
            messagebox.showerror("Error", f"Database error during login:\n{str(e)}")

