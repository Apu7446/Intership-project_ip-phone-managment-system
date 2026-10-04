"""
Backup & Disaster Recovery Frame — SBAC IP Phone Management System
Admin Database Backup Control: Manual Dumps, 1-Click Restore, Windows Task Scheduler, and History Management.
"""

import os
import threading
import subprocess
import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox
from config import COLORS, setup_treeview_style
import backup_manager


class BackupFrame(ctk.CTkFrame):
    def __init__(self, parent, user, app_ref=None):
        super().__init__(parent, fg_color=COLORS['bg_dark'])
        self.user = user
        self.app_ref = app_ref
        self._is_working = False

        self.build_ui()
        self.load_backup_history()

    def build_ui(self):
        # ── Header ──
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(15, 10))

        ctk.CTkLabel(header, text="💾  Database Backup & Disaster Recovery",
                     font=ctk.CTkFont(size=22, weight="bold"),
                     text_color=COLORS['text_white']).pack(side="left")

        # Top Action Buttons
        btn_box = ctk.CTkFrame(header, fg_color="transparent")
        btn_box.pack(side="right")

        open_dir_btn = ctk.CTkButton(
            btn_box, text="📂 Open Folder", width=120, height=36,
            corner_radius=18,
            fg_color=COLORS['entry_bg'], hover_color=COLORS['primary_dark'],
            border_width=1, border_color=COLORS['border'],
            text_color=COLORS['text_light'],
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self.open_backup_directory)
        open_dir_btn.pack(side="left", padx=4)

        sched_btn = ctk.CTkButton(
            btn_box, text="⏰ Schedule Timer", width=140, height=36,
            corner_radius=18,
            fg_color=COLORS['primary_dark'], hover_color=COLORS['primary'],
            border_width=1, border_color=COLORS['border'],
            text_color=COLORS['secondary'],
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self.show_scheduler_dialog)
        sched_btn.pack(side="left", padx=4)

        self.backup_btn = ctk.CTkButton(
            btn_box, text="⚡ Create Backup Now", width=170, height=36,
            corner_radius=18,
            fg_color=COLORS['primary'], hover_color=COLORS['primary_light'],
            text_color=COLORS['text_white'],
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self.trigger_manual_backup)
        self.backup_btn.pack(side="left", padx=(4, 0))

        # ── KPI Metric Cards ──
        metrics_frame = ctk.CTkFrame(self, fg_color="transparent")
        metrics_frame.pack(fill="x", padx=20, pady=(0, 10))

        # Card 1: Total Backups
        self.card_total = self._create_kpi_card(
            metrics_frame, "📦 Total Backups", "0", COLORS['info'], "Available .sql files"
        )
        self.card_total.pack(side="left", fill="both", expand=True, padx=(0, 8))

        # Card 2: Last Backup Time
        self.card_last = self._create_kpi_card(
            metrics_frame, "🕒 Latest Backup", "None", COLORS['secondary'], "Timestamp of last dump"
        )
        self.card_last.pack(side="left", fill="both", expand=True, padx=4)

        # Card 3: Scheduler Status
        self.card_status = self._create_kpi_card(
            metrics_frame, "🛡️ Disaster Recovery", "Active", COLORS['success'], "Daily automated backup"
        )
        self.card_status.pack(side="left", fill="both", expand=True, padx=(8, 0))

        # ── Main Container: Backups History Table ──
        main_card = ctk.CTkFrame(self, fg_color=COLORS['bg_card'], corner_radius=14,
                                 border_width=1, border_color=COLORS['border'])
        main_card.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        # Top Bar of Main Card
        top_bar = ctk.CTkFrame(main_card, fg_color="transparent")
        top_bar.pack(fill="x", padx=15, pady=(12, 6))

        self.table_title = ctk.CTkLabel(
            top_bar, text="📋 Backup History Archive",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLORS['text_white']
        )
        self.table_title.pack(side="left")

        restore_selected_btn = ctk.CTkButton(
            top_bar, text="🔄 Restore Selected Backup", width=190, height=30,
            corner_radius=15,
            fg_color=COLORS['entry_bg'], hover_color=COLORS['primary'],
            border_width=1, border_color=COLORS['border'],
            text_color=COLORS['text_white'],
            font=ctk.CTkFont(size=11, weight="bold"),
            command=self.restore_selected_backup
        )
        restore_selected_btn.pack(side="right", padx=(8, 0))

        refresh_btn = ctk.CTkButton(
            top_bar, text="🔄 Refresh", width=90, height=30,
            corner_radius=15,
            fg_color=COLORS['entry_bg'], hover_color=COLORS['primary_dark'],
            border_width=1, border_color=COLORS['border'],
            text_color=COLORS['text_light'],
            font=ctk.CTkFont(size=11, weight="bold"),
            command=self.load_backup_history
        )
        refresh_btn.pack(side="right")

        # Table Container
        table_box = ctk.CTkFrame(main_card, fg_color="transparent")
        table_box.pack(fill="both", expand=True, padx=15, pady=(5, 12))

        setup_treeview_style()

        columns = ("id", "filename", "datetime", "size", "type", "status")
        self.tree = ttk.Treeview(table_box, columns=columns, show="headings", selectmode="browse")

        headings = [
            ("id", "#", 50, "center"),
            ("filename", "Backup Filename (.sql)", 330, "w"),
            ("datetime", "Backup Timestamp", 200, "center"),
            ("size", "File Size", 110, "center"),
            ("type", "Backup Trigger", 140, "center"),
            ("status", "Status", 130, "center")
        ]

        for col_id, text, width, align in headings:
            self.tree.heading(col_id, text=text, anchor="center")
            self.tree.column(col_id, width=width, minwidth=width, stretch=False, anchor=align)

        tree_scroll_y = ttk.Scrollbar(table_box, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scroll_y.set)

        self.tree.pack(side="left", fill="both", expand=True)
        tree_scroll_y.pack(side="right", fill="y")

        self.tree.tag_configure("even_row", background="#1E1020")
        self.tree.tag_configure("odd_row", background="#2A1530")

        self.tree.bind("<Double-1>", lambda e: self.restore_selected_backup())
        self.tree.bind("<Button-3>", lambda e: self.show_context_menu(e))

    def _create_kpi_card(self, parent, title, value, val_color, subtitle):
        card = ctk.CTkFrame(parent, fg_color=COLORS['bg_card'], corner_radius=14,
                            border_width=1, border_color=COLORS['border'])
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=15, pady=12)

        ctk.CTkLabel(inner, text=title, font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=COLORS['text_muted'], anchor="w").pack(fill="x")
        val_lbl = ctk.CTkLabel(inner, text=value, font=ctk.CTkFont(size=20, weight="bold"),
                               text_color=val_color, anchor="w")
        val_lbl.pack(fill="x", pady=(3, 2))
        card.val_lbl = val_lbl

        sub_lbl = ctk.CTkLabel(inner, text=subtitle, font=ctk.CTkFont(size=10),
                               text_color=COLORS['text_light'], anchor="w")
        sub_lbl.pack(fill="x")
        card.sub_lbl = sub_lbl
        return card

    def load_backup_history(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        backups = backup_manager.list_backups()
        count = len(backups)

        self.card_total.val_lbl.configure(text=str(count))
        self.table_title.configure(text=f"📋 Backup History Archive ({count} snapshots available)")

        if backups:
            self.card_last.val_lbl.configure(text=backups[0]['datetime'])
            self.card_last.sub_lbl.configure(text=f"Latest: {backups[0]['filename']}")
        else:
            self.card_last.val_lbl.configure(text="No Backups Yet")
            self.card_last.sub_lbl.configure(text="Click Create Backup Now")

        # Scheduler status
        sched_active, sched_info = backup_manager.get_windows_task_status()
        if sched_active:
            self.card_status.val_lbl.configure(text="Auto-Scheduled")
            self.card_status.sub_lbl.configure(text=f"Next: {sched_info}")
        else:
            self.card_status.val_lbl.configure(text="App Startup Active")
            self.card_status.sub_lbl.configure(text="Backups run on app launch")

        for idx, b in enumerate(backups):
            row_tag = "even_row" if idx % 2 == 0 else "odd_row"
            self.tree.insert("", "end", iid=b['filepath'], values=(
                idx + 1,
                b['filename'],
                b['datetime'],
                b['size'],
                f"⚙️ {b['type']}",
                "🟢 Verified"
            ), tags=(row_tag,))

    def trigger_manual_backup(self):
        if self._is_working:
            return

        self._is_working = True
        self.backup_btn.configure(state="disabled", text="⏳ Dumping Database...")

        def _worker():
            success, msg = backup_manager.create_backup(tag="manual")
            self.after(0, lambda: self._on_backup_finished(success, msg))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_backup_finished(self, success, msg):
        self._is_working = False
        self.backup_btn.configure(state="normal", text="⚡ Create Backup Now")
        if success:
            messagebox.showinfo("Backup Successful", f"Full database backup created successfully!\n\nFile: {os.path.basename(msg)}")
            self.load_backup_history()
        else:
            messagebox.showerror("Backup Failed", f"Could not create database backup:\n{msg}")

    def restore_selected_backup(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Select Backup", "Please select a backup file from the list to restore.")
            return

        filepath = selected[0]
        fname = os.path.basename(filepath)

        confirm = messagebox.askyesno(
            "Confirm Database Disaster Recovery / Restore",
            f"⚠️ WARNING: Restoring will overwrite the current database with the selected snapshot:\n\n"
            f"File: {fname}\n\n"
            f"Are you sure you want to proceed?",
            icon="warning"
        )
        if not confirm:
            return

        # Perform restore in background thread
        progress_dialog = ctk.CTkToplevel(self)
        progress_dialog.title("Restoring Database...")
        progress_dialog.geometry("380x160")
        progress_dialog.transient(self)
        progress_dialog.grab_set()
        progress_dialog.configure(fg_color=COLORS['bg_card'])

        ctk.CTkLabel(
            progress_dialog, text="🔄 Restoring Database Snapshot...",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLORS['secondary']
        ).pack(pady=(25, 10))

        p_bar = ctk.CTkProgressBar(progress_dialog, width=280, mode="indeterminate",
                                   progress_color=COLORS['primary'])
        p_bar.pack(pady=10)
        p_bar.start()

        def _restore_worker():
            success, msg = backup_manager.restore_backup(filepath)
            self.after(0, lambda: self._on_restore_finished(progress_dialog, p_bar, success, msg))

        threading.Thread(target=_restore_worker, daemon=True).start()

    def _on_restore_finished(self, dialog, p_bar, success, msg):
        try:
            p_bar.stop()
            dialog.destroy()
        except Exception:
            pass

        if success:
            messagebox.showinfo("Restore Successful", "Database has been restored successfully to the selected snapshot!")
            self.load_backup_history()
        else:
            messagebox.showerror("Restore Failed", f"Failed to restore database:\n{msg}")

    def show_context_menu(self, event):
        iid = self.tree.identify_row(event.y)
        if iid:
            self.tree.selection_set(iid)
            filepath = iid

            menu = tk.Menu(self, tearoff=0, bg="#251528", fg="#FFFFFF", activebackground="#85175F")
            menu.add_command(label="🔄 Restore This Backup", command=self.restore_selected_backup)
            menu.add_command(label="📂 Show in File Explorer", command=lambda: self.open_in_explorer(filepath))
            menu.add_separator()
            menu.add_command(label="🗑️ Delete This Backup", command=lambda: self.delete_backup(filepath))
            menu.post(event.x_root, event.y_root)

    def delete_backup(self, filepath):
        fname = os.path.basename(filepath)
        confirm = messagebox.askyesno("Delete Backup", f"Are you sure you want to permanently delete backup:\n{fname}?")
        if confirm:
            try:
                if os.path.exists(filepath):
                    os.remove(filepath)
                self.load_backup_history()
            except Exception as e:
                messagebox.showerror("Error", f"Could not delete file: {e}")

    def open_backup_directory(self):
        d = backup_manager.ensure_backup_dir()
        os.startfile(d)

    def open_in_explorer(self, filepath):
        if os.path.exists(filepath):
            subprocess.run(f'explorer /select,"{os.path.abspath(filepath)}"', shell=True)

    def show_scheduler_dialog(self):
        """Modal to configure Windows Task Scheduler timer."""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Automated Backup Scheduler Configuration")
        dialog.geometry("460x340")
        dialog.transient(self)
        dialog.grab_set()
        dialog.configure(fg_color=COLORS['bg_card'])

        ctk.CTkLabel(
            dialog, text="⏰  Daily Auto-Backup Scheduler",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=COLORS['text_white']
        ).pack(pady=(18, 5))

        ctk.CTkLabel(
            dialog,
            text="Registers a daily automated background backup with Windows Task Scheduler.\n"
                 "If the PC was closed at the scheduled time, it will automatically\n"
                 "execute as soon as the PC is turned on.",
            font=ctk.CTkFont(size=11),
            text_color=COLORS['text_muted'],
            justify="center"
        ).pack(padx=20, pady=(0, 15))

        form_box = ctk.CTkFrame(dialog, fg_color=COLORS['entry_bg'], corner_radius=10)
        form_box.pack(fill="x", padx=25, pady=10)

        ctk.CTkLabel(form_box, text="Daily Execution Time (24-Hour Format):",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=COLORS['text_light']).pack(pady=(12, 5))

        time_var = ctk.StringVar(value="14:00")
        time_options = ["09:00", "11:00", "13:00", "14:00", "16:00", "18:00", "20:00", "22:00", "23:59"]
        time_menu = ctk.CTkOptionMenu(
            form_box, values=time_options, variable=time_var,
            width=180, height=34, corner_radius=8,
            fg_color=COLORS['primary'], button_color=COLORS['primary_dark'],
            text_color=COLORS['text_white'], font=ctk.CTkFont(size=12, weight="bold")
        )
        time_menu.pack(pady=(0, 15))

        # Status text
        sched_active, sched_info = backup_manager.get_windows_task_status()
        status_txt = f"Current Status: Registered ({sched_info})" if sched_active else "Current Status: Not Registered in Windows Scheduler"
        status_col = COLORS['success'] if sched_active else COLORS['text_muted']
        st_lbl = ctk.CTkLabel(dialog, text=status_txt, font=ctk.CTkFont(size=11, weight="bold"), text_color=status_col)
        st_lbl.pack(pady=(0, 10))

        # Buttons
        btn_bar = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_bar.pack(pady=(5, 15))

        def _save_task():
            t_str = time_var.get()
            success, res_msg = backup_manager.register_windows_task(t_str)
            if success:
                messagebox.showinfo("Scheduler Configured", res_msg)
                dialog.destroy()
                self.load_backup_history()
            else:
                messagebox.showerror("Error", res_msg)

        def _disable_task():
            res = backup_manager.unregister_windows_task()
            if res:
                messagebox.showinfo("Disabled", "Windows Scheduled Task has been removed.")
            else:
                messagebox.showinfo("Status", "Task was not registered or already removed.")
            dialog.destroy()
            self.load_backup_history()

        save_btn = ctk.CTkButton(
            btn_bar, text="💾 Enable / Save Schedule", width=180, height=34,
            corner_radius=17, fg_color=COLORS['primary'], hover_color=COLORS['primary_light'],
            text_color=COLORS['text_white'], font=ctk.CTkFont(size=11, weight="bold"),
            command=_save_task
        )
        save_btn.pack(side="left", padx=5)

        remove_btn = ctk.CTkButton(
            btn_bar, text="🚫 Disable Schedule", width=140, height=34,
            corner_radius=17, fg_color=COLORS['danger'], hover_color="#D32F2F",
            text_color=COLORS['text_white'], font=ctk.CTkFont(size=11, weight="bold"),
            command=_disable_task
        )
        remove_btn.pack(side="left", padx=5)
