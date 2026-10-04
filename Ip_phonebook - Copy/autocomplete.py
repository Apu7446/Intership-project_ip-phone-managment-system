"""
SBAC IP Phone Management System — Ultra-Fast Live Autocomplete Engine
Zero-lag, 100% native Python Google-style predictive text suggestions.
Uses an override-redirect floating popup window for 100% visible, non-clipped rendering.
"""

import tkinter as tk
from config import COLORS


class LiveAutocomplete:
    """
    Attaches to a CTkEntry widget to provide real-time Google-style suggestions.
    Floats directly below the entry box at absolute screen coordinates without clipping.
    """
    def __init__(self, parent_window, entry_widget, get_candidates_func, on_select=None, max_items=6):
        self.parent_window = parent_window
        self.entry_widget = entry_widget
        self.get_candidates_func = get_candidates_func
        self.on_select = on_select
        self.max_items = max_items

        self.popup = None
        self.listbox = None

        # Bind events to the inner entry
        target_entry = getattr(self.entry_widget, '_entry', self.entry_widget)
        target_entry.bind("<KeyRelease>", self._on_key_release)
        target_entry.bind("<FocusOut>", self._on_focus_out)
        target_entry.bind("<Down>", self._on_arrow_down)
        target_entry.bind("<Up>", self._on_arrow_up)
        target_entry.bind("<Return>", self._on_enter)
        target_entry.bind("<Escape>", lambda e: self.hide_popup())

    def _get_candidates(self):
        if callable(self.get_candidates_func):
            return self.get_candidates_func()
        return list(self.get_candidates_func)

    def _filter_candidates(self, query):
        if not query or len(query.strip()) < 1:
            return []

        q = query.strip().lower()
        candidates = self._get_candidates()

        prefix_matches = []
        substring_matches = []

        for item in candidates:
            if not item or item == "None" or item.startswith("Select"):
                continue
            item_str = str(item).strip()
            item_lower = item_str.lower()

            if item_lower.startswith(q):
                if item_str not in prefix_matches:
                    prefix_matches.append(item_str)
            elif q in item_lower:
                if item_str not in substring_matches:
                    substring_matches.append(item_str)

        combined = prefix_matches + substring_matches
        return combined[:self.max_items]

    def _on_key_release(self, event):
        if event.keysym in ("Up", "Down", "Return", "Escape", "Tab", "Shift_L", "Shift_R", "Control_L", "Control_R"):
            return

        query = self.entry_widget.get().strip()
        matches = self._filter_candidates(query)

        if matches:
            self._show_popup(matches)
        else:
            self.hide_popup()

    def _show_popup(self, matches):
        try:
            self.entry_widget.update_idletasks()
            x = self.entry_widget.winfo_rootx()
            y = self.entry_widget.winfo_rooty() + self.entry_widget.winfo_height() + 2
            w = max(self.entry_widget.winfo_width(), 260)
            h = min(len(matches) * 30 + 10, 180)
        except Exception:
            return

        if not self.popup or not self.popup.winfo_exists():
            self.popup = tk.Toplevel(self.parent_window)
            self.popup.wm_overrideredirect(True)
            self.popup.wm_attributes("-topmost", True)
            self.popup.configure(bg=COLORS['primary'])

            outer_frame = tk.Frame(self.popup, bg="#240B2B", bd=1, relief="solid")
            outer_frame.pack(fill="both", expand=True, padx=1, pady=1)

            self.listbox = tk.Listbox(
                outer_frame,
                bg="#1F0E24",
                fg="#FFFFFF",
                selectbackground=COLORS['primary'],
                selectforeground="#FFFFFF",
                bd=0,
                highlightthickness=0,
                font=('Segoe UI', 10, 'bold'),
                activestyle="none"
            )
            self.listbox.pack(fill="both", expand=True, padx=2, pady=2)
            self.listbox.bind("<<ListboxSelect>>", self._on_listbox_select)
            self.listbox.bind("<Button-1>", self._on_listbox_click)

        self.popup.wm_geometry(f"{w}x{h}+{x}+{y}")
        self.popup.deiconify()
        self.popup.lift()

        self.listbox.delete(0, tk.END)
        for text in matches:
            self.listbox.insert(tk.END, f"  🔍  {text}")

    def _on_listbox_click(self, event):
        idx = self.listbox.nearest(event.y)
        if idx >= 0:
            raw_text = self.listbox.get(idx)
            val = raw_text.replace("  🔍  ", "").strip()
            self._select_value(val)

    def _on_listbox_select(self, event):
        sel = self.listbox.curselection()
        if sel:
            raw_text = self.listbox.get(sel[0])
            val = raw_text.replace("  🔍  ", "").strip()
            self._select_value(val)

    def _select_value(self, value):
        if hasattr(self.entry_widget, 'delete'):
            self.entry_widget.delete(0, tk.END)
            self.entry_widget.insert(0, value)
        elif hasattr(self.entry_widget, 'set'):
            self.entry_widget.set(value)

        self.hide_popup()

        if self.on_select:
            self.on_select(value)

    def _on_arrow_down(self, event):
        if not self.popup or not self.popup.winfo_exists() or not self.listbox:
            return
        cur = self.listbox.curselection()
        next_idx = 0 if not cur else min(cur[0] + 1, self.listbox.size() - 1)
        self.listbox.selection_clear(0, tk.END)
        self.listbox.selection_set(next_idx)
        self.listbox.see(next_idx)
        return "break"

    def _on_arrow_up(self, event):
        if not self.popup or not self.popup.winfo_exists() or not self.listbox:
            return
        cur = self.listbox.curselection()
        prev_idx = self.listbox.size() - 1 if not cur else max(cur[0] - 1, 0)
        self.listbox.selection_clear(0, tk.END)
        self.listbox.selection_set(prev_idx)
        self.listbox.see(prev_idx)
        return "break"

    def _on_enter(self, event):
        if self.popup and self.popup.winfo_exists() and self.listbox:
            sel = self.listbox.curselection()
            if sel:
                raw_text = self.listbox.get(sel[0])
                val = raw_text.replace("  🔍  ", "").strip()
                self._select_value(val)
                return "break"

    def _on_focus_out(self, event):
        if self.popup and self.popup.winfo_exists():
            self.parent_window.after(200, self.hide_popup)

    def hide_popup(self):
        if self.popup:
            try:
                self.popup.destroy()
            except Exception:
                pass
            self.popup = None
            self.listbox = None
