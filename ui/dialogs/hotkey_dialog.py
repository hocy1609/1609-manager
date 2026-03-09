import tkinter as tk
from tkinter import messagebox
from ui.ui_base import BaseDialog, ModernButton, COLORS, ToggleSwitch

class HotkeyDialog(BaseDialog):
    """Dialog for creating/editing a Hotkey."""

    def __init__(self, parent, is_new=False, hotkey_data=None, on_save=None):
        title = "Add Hotkey" if is_new else "Edit Hotkey"
        super().__init__(parent, title, 500, 480)
        
        self.on_save = on_save
        self.is_new = is_new
        self.hotkey_data = hotkey_data or {}
        
        # Read from dictionary or object
        self.trigger = self._get_val("trigger", "")
        self.sequence_raw = self._get_val("sequence", [])
        self.right_click = self._get_val("rightClick", False)
        if self._get_val("right_click", None) is not None:
             self.right_click = self._get_val("right_click", False)
        self.comment = self._get_val("comment", "")
        self.enabled = self._get_val("enabled", True)

        self.trigger_var = tk.StringVar(value=self.trigger)
        
        # For sequence, join array into comma-separated string for editing
        if isinstance(self.sequence_raw, list):
             seq_str = ", ".join(self.sequence_raw)
        else:
             seq_str = str(self.sequence_raw)
        self.sequence_var = tk.StringVar(value=seq_str)
        
        self.right_click_var = tk.BooleanVar(value=self.right_click)
        self.comment_var = tk.StringVar(value=self.comment)
        self.enabled_var = tk.BooleanVar(value=self.enabled)
        
        self.create_widgets()
        self.finalize_window(parent)

    def _get_val(self, key, default):
        if isinstance(self.hotkey_data, dict):
            return self.hotkey_data.get(key, default)
        return getattr(self.hotkey_data, key, default)

    def create_widgets(self):
        padding = 20
        content = tk.Frame(self, bg=COLORS["bg_root"])
        content.pack(fill="both", expand=True, padx=padding, pady=padding)

        # Trigger
        tk.Label(content, text="Trigger Key (e.g., 4, Shift+Q):", bg=COLORS["bg_root"], fg=COLORS["fg_dim"], font=("Segoe UI", 10)).pack(anchor="w", pady=(0, 2))
        trigger_entry = tk.Entry(content, textvariable=self.trigger_var, bg=COLORS["bg_input"], fg=COLORS["fg_text"], relief="flat", insertbackground="white", font=("Segoe UI", 11))
        trigger_entry.pack(fill="x", ipady=5, pady=(0, 15))
        
        # Sequence
        tk.Label(content, text="Key Sequence (comma separated keys to press):", bg=COLORS["bg_root"], fg=COLORS["fg_dim"], font=("Segoe UI", 10)).pack(anchor="w", pady=(0, 2))
        tk.Label(content, text="Example: NUMPAD0, NUMPAD3, NUMPAD2", bg=COLORS["bg_root"], fg=COLORS["accent"], font=("Segoe UI", 8)).pack(anchor="w", pady=(0, 2))
        seq_entry = tk.Entry(content, textvariable=self.sequence_var, bg=COLORS["bg_input"], fg=COLORS["fg_text"], relief="flat", insertbackground="white", font=("Segoe UI", 11))
        seq_entry.pack(fill="x", ipady=5, pady=(0, 15))

        # Right Click
        rc_frame = tk.Frame(content, bg=COLORS["bg_root"])
        rc_frame.pack(fill="x", pady=(0, 15))
        tk.Label(rc_frame, text="Right Click before sequence:", bg=COLORS["bg_root"], fg=COLORS["fg_dim"], font=("Segoe UI", 10)).pack(side="left")
        ToggleSwitch(rc_frame, variable=self.right_click_var).pack(side="left", padx=(10, 0))

        # Comment
        tk.Label(content, text="Comment / Label:", bg=COLORS["bg_root"], fg=COLORS["fg_dim"], font=("Segoe UI", 10)).pack(anchor="w", pady=(0, 2))
        comment_entry = tk.Entry(content, textvariable=self.comment_var, bg=COLORS["bg_input"], fg=COLORS["fg_text"], relief="flat", insertbackground="white", font=("Segoe UI", 11))
        comment_entry.pack(fill="x", ipady=5, pady=(0, 15))

        # Enabled
        en_frame = tk.Frame(content, bg=COLORS["bg_root"])
        en_frame.pack(fill="x", pady=(0, 15))
        tk.Label(en_frame, text="Enabled:", bg=COLORS["bg_root"], fg=COLORS["fg_dim"], font=("Segoe UI", 10)).pack(side="left")
        ToggleSwitch(en_frame, variable=self.enabled_var).pack(side="left", padx=(10, 0))

        # Buttons
        btn_frame = tk.Frame(self, bg=COLORS["bg_root"])
        btn_frame.pack(fill="x", padx=padding, pady=(0, 20), side="bottom")

        ModernButton(
            btn_frame, COLORS["success"], COLORS["success_hover"], text="Save",
            font=("Segoe UI", 11, "bold"), command=self.save_and_close
        ).pack(side="right", ipadx=15, ipady=5)

        ModernButton(
            btn_frame, COLORS["bg_panel"], COLORS["border"], text="Cancel",
            font=("Segoe UI", 11), fg=COLORS["fg_text"], command=self.destroy
        ).pack(side="right", padx=10, ipadx=10, ipady=5)

    def save_and_close(self):
        trigger = self.trigger_var.get().strip()
        if not trigger:
            messagebox.showwarning("Validation Error", "Trigger Key is required.", parent=self)
            return
            
        seq_str = self.sequence_var.get().strip()
        if not seq_str:
            messagebox.showwarning("Validation Error", "Key Sequence is required.", parent=self)
            return
            
        seq_list = [s.strip() for s in seq_str.split(",") if s.strip()]
        
        new_data = {
            "trigger": trigger,
            "sequence": seq_list,
            "rightClick": self.right_click_var.get(),
            "comment": self.comment_var.get().strip(),
            "enabled": self.enabled_var.get()
        }
        
        if self.on_save:
            self.on_save(new_data)
        self.destroy()
