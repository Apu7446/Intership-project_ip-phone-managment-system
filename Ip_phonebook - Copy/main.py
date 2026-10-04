"""
SBAC Bank PLC — IP Phone Management System
Main Application Entry Point
"""

import os
import customtkinter as ctk
from config import APP_TITLE, APP_SIZE, COLORS, setup_treeview_style
from frames.login import LoginFrame
from app import MainApp
import db

# Set CustomTkinter theme
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")


class AppWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        setup_treeview_style()
        self.title(APP_TITLE)
        self.geometry(APP_SIZE)
        self.minsize(1100, 680)
        self.configure(fg_color=COLORS['bg_dark'])

        # Set window icon (ICO + sbac-logo.png)
        base_dir = os.path.dirname(__file__)
        icon_path = os.path.join(base_dir, "app_icon.ico")
        png_icon_path = os.path.join(base_dir, "sbac-logo.png")
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception:
                pass
        if os.path.exists(png_icon_path):
            try:
                from PIL import Image, ImageTk
                self._icon_img = ImageTk.PhotoImage(Image.open(png_icon_path))
                self.wm_iconphoto(True, self._icon_img)
            except Exception:
                pass

        # Center window on screen
        self.update_idletasks()
        w = 1240
        h = 750
        x = (self.winfo_screenwidth() - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

        self.current_user = None
        self.main_container = None

        # Initialize Database & Indexes
        self.init_db_connection()

        # Show login
        self.show_login()

    def init_db_connection(self):
        """Ensure MySQL database, tables, and indexes are connected and ready."""
        try:
            db.ensure_database()
            db.ensure_indexes()
        except Exception as e:
            from tkinter import messagebox
            from config import DB_CONFIG
            err_msg = (
                f"Could not connect to MySQL database at '{DB_CONFIG.get('host')}:{DB_CONFIG.get('port')}':\n\n"
                f"{str(e)}\n\n"
                "Would you like to configure the Server PC IP address now?"
            )
            print(f"[NOTICE] {err_msg}")
            if messagebox.askyesno("Server Connection Setup", err_msg):
                from frames.login import ServerConfigDialog
                ServerConfigDialog(self, on_saved=self.on_server_config_saved)

    def on_server_config_saved(self):
        """Callback when Server IP is updated via dialog."""
        try:
            db.ensure_database()
            db.ensure_indexes()
        except Exception:
            pass
        if self.main_container and hasattr(self.main_container, 'update_server_btn_text'):
            self.main_container.update_server_btn_text()

    def show_login(self):
        if self.main_container:
            self.main_container.destroy()

        self.main_container = LoginFrame(self, on_login_success=self.on_login_success)
        self.main_container.pack(fill="both", expand=True)

    def on_login_success(self, user):
        self.current_user = user
        if self.main_container:
            self.main_container.destroy()

        self.title(f"{APP_TITLE} — {user['full_name']} ({user['role']})")
        self.main_container = MainApp(self, user, on_logout=self.on_logout)
        self.main_container.pack(fill="both", expand=True)

    def on_logout(self):
        self.current_user = None
        self.title(APP_TITLE)
        self.show_login()


def main():
    app = AppWindow()
    app.mainloop()


if __name__ == '__main__':
    main()
