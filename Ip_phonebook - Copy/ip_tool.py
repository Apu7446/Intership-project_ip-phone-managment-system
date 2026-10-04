"""
SBAC IP Phone Management System — Real-Time IP Ping & Subnet Tool
Single IP Ping + Bulk Subnet Loop Scan directly in Command Prompt / PowerShell
Official SBAC Bank PLC Theme
"""

import os
import customtkinter as ctk
from tkinter import messagebox
from config import COLORS


class IPToolDialog(ctk.CTkToplevel):
    def __init__(self, parent, default_ip=""):
        super().__init__(parent)
        self.parent = parent
        self.default_ip = default_ip

        self.title("🌐 SBAC Bank — Real-Time IP Ping & Subnet Scanner Tool")
        self.geometry("540x440")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.configure(fg_color=COLORS['bg_dark'])

        # Center window
        self.update_idletasks()
        x = (self.winfo_screenwidth() - 540) // 2
        y = (self.winfo_screenheight() - 440) // 2
        self.geometry(f"+{x}+{y}")

        self.build_ui()

    def build_ui(self):
        self.tabview = ctk.CTkTabview(
            self, fg_color=COLORS['bg_card'],
            segmented_button_selected_color=COLORS['primary'],
            segmented_button_selected_hover_color=COLORS['primary_light'],
            segmented_button_unselected_color=COLORS['entry_bg'],
            text_color=COLORS['text_white']
        )
        self.tabview.pack(fill="both", expand=True, padx=15, pady=15)

        self.tab_single = self.tabview.add("💻 Single IP Ping")
        self.tab_bulk = self.tabview.add("🚀 Bulk Subnet Scan")

        self.build_single_ping_tab()
        self.build_bulk_scanner_tab()

    def build_single_ping_tab(self):
        tab = self.tab_single

        ctk.CTkLabel(
            tab, text="🌐 Real-Time Single IP Ping",
            font=ctk.CTkFont(size=17, weight="bold"),
            text_color=COLORS['secondary']
        ).pack(pady=(15, 5))

        ctk.CTkLabel(
            tab, text="Enter Target IP Address to launch continuous live ping:",
            font=ctk.CTkFont(size=12),
            text_color=COLORS['text_light']
        ).pack(pady=(0, 15))

        self.ip_entry = ctk.CTkEntry(
            tab, placeholder_text="e.g. 172.19.102.204",
            width=320, height=40, font=ctk.CTkFont(size=13),
            corner_radius=10,
            fg_color=COLORS['entry_bg'], border_color=COLORS['border']
        )
        if self.default_ip:
            self.ip_entry.insert(0, self.default_ip)
        self.ip_entry.pack(pady=5)
        self.ip_entry.focus()

        btn_frame = ctk.CTkFrame(tab, fg_color="transparent")
        btn_frame.pack(pady=20)

        cmd_btn = ctk.CTkButton(
            btn_frame, text="💻 Open in CMD", width=145, height=40,
            corner_radius=10,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=COLORS['primary'], hover_color=COLORS['primary_light'],
            command=lambda: self.start_single_ping("cmd")
        )
        cmd_btn.pack(side="left", padx=8)

        ps_btn = ctk.CTkButton(
            btn_frame, text="⚡ Open PowerShell", width=155, height=40,
            corner_radius=10,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=COLORS['secondary'], hover_color=COLORS['secondary_hover'],
            text_color="#000000",
            command=lambda: self.start_single_ping("powershell")
        )
        ps_btn.pack(side="left", padx=8)

    def start_single_ping(self, tool="cmd"):
        ip = self.ip_entry.get().strip()
        if not ip:
            messagebox.showwarning("Warning", "Please enter a valid IP address first!", parent=self)
            return

        if tool == "powershell":
            cmd = f'start powershell -NoExit -Command "Write-Host \'=== Continuous Ping to {ip} ===\' -ForegroundColor Green; ping {ip} -t"'
        else:
            cmd = f'start cmd /k "title Ping {ip} && echo === Continuous Ping to {ip} === && ping {ip} -t"'

        os.system(cmd)

    def build_bulk_scanner_tab(self):
        tab = self.tab_bulk

        ctk.CTkLabel(
            tab, text="🚀 Subnet Range Scan in CMD Window",
            font=ctk.CTkFont(size=17, weight="bold"),
            text_color=COLORS['secondary']
        ).pack(pady=(15, 5))

        ctk.CTkLabel(
            tab, text="Executes fast loop ping (1 to 254) directly in Command Prompt\nshowing live active replying IPs on the network.",
            font=ctk.CTkFont(size=12), text_color=COLORS['text_light'], justify="center"
        ).pack(pady=(0, 15))

        default_prefix = "172.19.100"
        if self.default_ip and len(self.default_ip.split('.')) == 4:
            default_prefix = '.'.join(self.default_ip.split('.')[:3])

        input_frame = ctk.CTkFrame(tab, fg_color="transparent")
        input_frame.pack(pady=10)

        ctk.CTkLabel(
            input_frame, text="Subnet Prefix:",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLORS['text_white']
        ).pack(side="left", padx=(0, 8))

        self.subnet_entry = ctk.CTkEntry(
            input_frame, placeholder_text="e.g. 172.19.100",
            width=170, height=40, font=ctk.CTkFont(size=13),
            corner_radius=10,
            fg_color=COLORS['entry_bg'], border_color=COLORS['border']
        )
        self.subnet_entry.insert(0, default_prefix)
        self.subnet_entry.pack(side="left")

        ctk.CTkLabel(
            input_frame, text=". (1-254)",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=COLORS['text_muted']
        ).pack(side="left", padx=(5, 0))

        btn_frame = ctk.CTkFrame(tab, fg_color="transparent")
        btn_frame.pack(pady=20)

        run_cmd_btn = ctk.CTkButton(
            btn_frame, text="💻 Run Bulk Scan in CMD Window", width=260, height=42,
            corner_radius=10,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=COLORS['secondary'], hover_color=COLORS['secondary_hover'],
            text_color="#000000",
            command=self.run_bulk_cmd_ping
        )
        run_cmd_btn.pack(pady=5)

    def run_bulk_cmd_ping(self):
        prefix = self.subnet_entry.get().strip().rstrip('.')
        if not prefix or len(prefix.split('.')) < 3:
            messagebox.showwarning("Warning", "Enter a valid 3-octet subnet prefix!\nExample: 172.19.100", parent=self)
            return

        cmd = f'start cmd /k "title Scanning Subnet {prefix}.1-254 && echo ========================================================== && echo   LIVE PING SCAN FOR SUBNET: {prefix}.1 to {prefix}.254 && echo ========================================================== && echo Searching for active replying IPs... Please wait... && echo. && for /l %i in (1,1,254) do @ping {prefix}.%i -w 10 -n 1 | find \"Reply\""'
        os.system(cmd)
        self.destroy()


def open_ip_tool(parent, default_ip=""):
    """Global helper function to open IP Tools dialog."""
    IPToolDialog(parent, default_ip)
