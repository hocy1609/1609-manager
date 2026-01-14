"""
Hotkeys Screen for NWN Manager.

Provides UI for configuring custom keybindings similar to AutoHotkey.
"""

import tkinter as tk
from tkinter import ttk, messagebox

from ui.ui_base import COLORS, ModernButton, ToggleSwitch, ToolTip, SectionFrame, Separator


def build_hotkeys_screen(app):
    """Build the Hotkeys configuration screen."""
    self = app
    
    hotkeys_frame = tk.Frame(self.content_frame, bg=COLORS["bg_root"])
    self.screens["hotkeys"] = hotkeys_frame
    
    # Scrollable container
    canvas = tk.Canvas(hotkeys_frame, bg=COLORS["bg_root"], highlightthickness=0, bd=0)
    scrollbar = ttk.Scrollbar(hotkeys_frame, orient="vertical", command=canvas.yview)
    scrollable_frame = tk.Frame(canvas, bg=COLORS["bg_root"])
    
    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )
    
    canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    
    def _on_canvas_configure(event):
        canvas.itemconfig(canvas_window, width=event.width)
    canvas.bind("<Configure>", _on_canvas_configure)
    
    def _on_mousewheel(event):
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
    canvas.bind_all("<MouseWheel>", _on_mousewheel, add="+")
    
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    
    # Main container
    main = tk.Frame(scrollable_frame, bg=COLORS["bg_root"])
    main.pack(fill="both", expand=True, padx=40, pady=20)
    
    # Header
    header = tk.Frame(main, bg=COLORS["bg_root"])
    header.pack(fill="x", pady=(0, 20))
    
    tk.Label(
        header,
        text="Hotkeys",
        font=("Segoe UI", 24, "bold"),
        bg=COLORS["bg_root"],
        fg=COLORS["fg_text"]
    ).pack(side="left")
    
    # Enable toggle
    hotkeys_cfg = getattr(self, 'hotkeys_config', {"enabled": False, "binds": []})
    self.hotkeys_enabled_var = tk.BooleanVar(value=hotkeys_cfg.get("enabled", False))
    
    enable_frame = tk.Frame(header, bg=COLORS["bg_root"])
    enable_frame.pack(side="right")
    tk.Label(enable_frame, text="Enabled:", bg=COLORS["bg_root"], fg=COLORS["fg_dim"]).pack(side="left", padx=(0, 10))
    
    def _on_hotkeys_toggle(*args):
        _apply_hotkeys()
    
    hotkeys_toggle = ToggleSwitch(enable_frame, variable=self.hotkeys_enabled_var, command=_on_hotkeys_toggle)
    hotkeys_toggle.pack(side="left")
    
    # Status label
    self.hotkeys_status_label = tk.Label(
        header,
        text="",
        bg=COLORS["bg_root"],
        fg=COLORS["fg_dim"],
        font=("Segoe UI", 10)
    )
    self.hotkeys_status_label.pack(side="right", padx=(0, 20))
    
    # Info
    info_frame = tk.Frame(main, bg=COLORS["bg_root"])
    info_frame.pack(fill="x", pady=(0, 15))
    tk.Label(
        info_frame,
        text="Configure hotkeys to send key sequences to NWN. Works only when game is active.",
        bg=COLORS["bg_root"],
        fg=COLORS["fg_dim"],
        font=("Segoe UI", 10)
    ).pack(anchor="w")
    # Header underline
    Separator(main, orient="horizontal", color=COLORS["accent"], thickness=2, padding=5).pack(fill="x", pady=(0, 15))
    
    # Hotkeys list frame - using SectionFrame for better styling
    list_frame = SectionFrame(main, text="Keybinds", accent=self.hotkeys_enabled_var.get())
    list_frame.pack(fill="both", expand=True, pady=(0, 15))
    
    # Treeview for hotkeys
    columns = ("trigger", "sequence", "rightclick", "comment")
    self.hotkeys_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=12)
    
    self.hotkeys_tree.heading("trigger", text="Key")
    self.hotkeys_tree.heading("sequence", text="Action (Numpad Sequence)")
    self.hotkeys_tree.heading("rightclick", text="R-Click")
    self.hotkeys_tree.heading("comment", text="Comment")
    
    self.hotkeys_tree.column("trigger", width=60, anchor="center")
    self.hotkeys_tree.column("sequence", width=300)
    self.hotkeys_tree.column("rightclick", width=60, anchor="center")
    self.hotkeys_tree.column("comment", width=200)
    
    tree_scroll = ttk.Scrollbar(list_frame, orient="vertical", command=self.hotkeys_tree.yview)
    self.hotkeys_tree.configure(yscrollcommand=tree_scroll.set)
    
    self.hotkeys_tree.pack(side="left", fill="both", expand=True, padx=10, pady=10)
    tree_scroll.pack(side="right", fill="y", pady=10)
    
    # Buttons frame
    btn_frame = tk.Frame(main, bg=COLORS["bg_root"])
    btn_frame.pack(fill="x", pady=(0, 15))
    
    def _add_hotkey():
        _open_hotkey_dialog(None)
    
    def _edit_hotkey():
        selected = self.hotkeys_tree.selection()
        if not selected:
            messagebox.showwarning("Edit", "Select a hotkey to edit", parent=self.root)
            return
        item = self.hotkeys_tree.item(selected[0])
        idx = self.hotkeys_tree.index(selected[0])
        _open_hotkey_dialog(idx)
    
    def _delete_hotkey():
        selected = self.hotkeys_tree.selection()
        if not selected:
            messagebox.showwarning("Delete", "Select a hotkey to delete", parent=self.root)
            return
        idx = self.hotkeys_tree.index(selected[0])
        binds = hotkeys_cfg.get("binds", [])
        if 0 <= idx < len(binds):
            binds.pop(idx)
            _refresh_hotkeys_list()
            _save_hotkeys_config()
    
    ModernButton(btn_frame, COLORS["success"], COLORS["success_hover"], text="➕ Add", width=12, command=_add_hotkey, tooltip="Add new keybind").pack(side="left", padx=(0, 10))
    ModernButton(btn_frame, COLORS["accent"], COLORS["accent_hover"], text="✏️ Edit", width=12, command=_edit_hotkey, tooltip="Edit selected keybind").pack(side="left", padx=(0, 10))
    ModernButton(btn_frame, COLORS["danger"], COLORS["danger_hover"], text="🗑️ Delete", width=12, command=_delete_hotkey, tooltip="Delete selected keybind").pack(side="left", padx=(0, 10))
    
    # Separator before apply
    Separator(main, orient="horizontal", padding=10).pack(fill="x")
    
    # Apply button
    apply_frame = tk.Frame(main, bg=COLORS["bg_root"])
    apply_frame.pack(fill="x")
    
    ModernButton(
        apply_frame,
        COLORS["success"],
        COLORS["success_hover"],
        text="💾 Save & Apply",
        width=15,
        command=lambda: (_save_hotkeys_config(), _apply_hotkeys())
    ).pack(side="left", padx=(0, 10))
    
    # Helper functions
    def _refresh_hotkeys_list():
        """Refresh the hotkeys treeview."""
        self.hotkeys_tree.delete(*self.hotkeys_tree.get_children())
        binds = hotkeys_cfg.get("binds", [])
        for bind in binds:
            trigger = bind.get("trigger", "")
            sequence = bind.get("sequence", [])
            seq_str = "-".join(s.replace("NUMPAD", "") for s in sequence)
            right_click = "✓" if bind.get("rightClick", False) else ""
            comment = bind.get("comment", "")
            self.hotkeys_tree.insert("", "end", values=(trigger, seq_str, right_click, comment))
    
    def _save_hotkeys_config():
        """Save hotkeys config to app settings."""
        hotkeys_cfg["enabled"] = self.hotkeys_enabled_var.get()
        self.hotkeys_config = hotkeys_cfg
        self.save_data()
    
    def _apply_hotkeys():
        """Apply hotkeys - register or unregister based on enabled state."""
        from core.keybind_manager import HotkeyAction
        
        enabled = self.hotkeys_enabled_var.get()
        binds = hotkeys_cfg.get("binds", [])
        
        if enabled and binds:
            actions = [HotkeyAction.from_dict(b) for b in binds if b.get("enabled", True)]
            count = self.multi_hotkey_manager.register_hotkeys(actions)
            self.hotkeys_status_label.config(
                text=f"✓ Active: {count} hotkeys",
                fg=COLORS["success"]
            )
        else:
            self.multi_hotkey_manager.unregister_all()
            self.hotkeys_status_label.config(
                text="Disabled",
                fg=COLORS["fg_dim"]
            )
        
        _save_hotkeys_config()
    
    def _open_hotkey_dialog(edit_idx: int = None):
        """Open dialog to add/edit a hotkey."""
        binds = hotkeys_cfg.get("binds", [])
        
        is_edit = edit_idx is not None and 0 <= edit_idx < len(binds)
        existing = binds[edit_idx] if is_edit else {}
        
        dialog = tk.Toplevel(self.root)
        dialog.title("Edit Hotkey" if is_edit else "Add Hotkey")
        dialog.geometry("450x350")
        dialog.configure(bg=COLORS["bg_root"])
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center dialog
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - 450) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - 350) // 2
        dialog.geometry(f"+{x}+{y}")
        
        # Form
        form = tk.Frame(dialog, bg=COLORS["bg_root"])
        form.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Trigger key
        tk.Label(form, text="Trigger Key:", bg=COLORS["bg_root"], fg=COLORS["fg_text"]).grid(row=0, column=0, sticky="w", pady=5)
        trigger_var = tk.StringVar(value=existing.get("trigger", ""))
        trigger_keys = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0",
                        "Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P",
                        "A", "S", "D", "F", "G", "H", "J", "K", "L",
                        "Z", "X", "C", "V", "B", "N", "M",
                        "F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9", "F10", "F11", "F12",
                        "SPACE", "`", "-", "=", ",", "."]
        trigger_cb = ttk.Combobox(form, textvariable=trigger_var, values=trigger_keys, width=15)
        trigger_cb.grid(row=0, column=1, sticky="w", pady=5, padx=(10, 0))
        
        # Sequence
        tk.Label(form, text="Numpad Sequence:", bg=COLORS["bg_root"], fg=COLORS["fg_text"]).grid(row=1, column=0, sticky="w", pady=5)
        seq_str = "-".join(str(s).replace("NUMPAD", "") for s in existing.get("sequence", []))
        sequence_var = tk.StringVar(value=seq_str)
        sequence_entry = tk.Entry(form, textvariable=sequence_var, width=30, bg=COLORS["bg_input"], fg=COLORS["fg_text"])
        sequence_entry.grid(row=1, column=1, sticky="w", pady=5, padx=(10, 0))
        
        tk.Label(form, text="(e.g., 0-9-2-9-8-8)", bg=COLORS["bg_root"], fg=COLORS["fg_dim"], font=("Segoe UI", 9)).grid(row=2, column=1, sticky="w", padx=(10, 0))
        
        # Right click
        tk.Label(form, text="Right-click first:", bg=COLORS["bg_root"], fg=COLORS["fg_text"]).grid(row=3, column=0, sticky="w", pady=5)
        rightclick_var = tk.BooleanVar(value=existing.get("rightClick", False))
        rightclick_cb = tk.Checkbutton(form, variable=rightclick_var, bg=COLORS["bg_root"], activebackground=COLORS["bg_root"])
        rightclick_cb.grid(row=3, column=1, sticky="w", pady=5, padx=(10, 0))
        
        # Comment
        tk.Label(form, text="Comment:", bg=COLORS["bg_root"], fg=COLORS["fg_text"]).grid(row=4, column=0, sticky="w", pady=5)
        comment_var = tk.StringVar(value=existing.get("comment", ""))
        comment_entry = tk.Entry(form, textvariable=comment_var, width=30, bg=COLORS["bg_input"], fg=COLORS["fg_text"])
        comment_entry.grid(row=4, column=1, sticky="w", pady=5, padx=(10, 0))
        
        # Enabled
        tk.Label(form, text="Enabled:", bg=COLORS["bg_root"], fg=COLORS["fg_text"]).grid(row=5, column=0, sticky="w", pady=5)
        enabled_var = tk.BooleanVar(value=existing.get("enabled", True))
        enabled_cb = tk.Checkbutton(form, variable=enabled_var, bg=COLORS["bg_root"], activebackground=COLORS["bg_root"])
        enabled_cb.grid(row=5, column=1, sticky="w", pady=5, padx=(10, 0))
        
        # Buttons
        btn_row = tk.Frame(form, bg=COLORS["bg_root"])
        btn_row.grid(row=6, column=0, columnspan=2, pady=(20, 0))
        
        def _save():
            trigger = trigger_var.get().strip().upper()
            seq_raw = sequence_var.get().strip()
            
            if not trigger:
                messagebox.showwarning("Error", "Trigger key is required", parent=dialog)
                return
            
            # Parse sequence: "0-9-2-9-8-8" -> ["NUMPAD0", "NUMPAD9", ...]
            sequence = []
            if seq_raw:
                parts = seq_raw.replace(" ", "").split("-")
                for p in parts:
                    if p.isdigit():
                        sequence.append(f"NUMPAD{p}")
                    elif p.upper().startswith("NUMPAD"):
                        sequence.append(p.upper())
                    else:
                        sequence.append(p.upper())
            
            bind_data = {
                "trigger": trigger,
                "sequence": sequence,
                "rightClick": rightclick_var.get(),
                "comment": comment_var.get().strip(),
                "enabled": enabled_var.get(),
            }
            
            if is_edit:
                binds[edit_idx] = bind_data
            else:
                binds.append(bind_data)
            
            hotkeys_cfg["binds"] = binds
            _refresh_hotkeys_list()
            _save_hotkeys_config()
            dialog.destroy()
        
        ModernButton(btn_row, COLORS["success"], COLORS["success_hover"], text="Save", width=10, command=_save).pack(side="left", padx=(0, 10))
        ModernButton(btn_row, COLORS["bg_input"], COLORS["border"], text="Cancel", width=10, command=dialog.destroy).pack(side="left")
    
    # Double-click to edit
    self.hotkeys_tree.bind("<Double-1>", lambda e: _edit_hotkey())
    
    # Initial load
    _refresh_hotkeys_list()
    
    # Update status
    if self.hotkeys_enabled_var.get() and hasattr(self, 'multi_hotkey_manager'):
        if self.multi_hotkey_manager.is_active():
            count = self.multi_hotkey_manager.get_registered_count()
            self.hotkeys_status_label.config(text=f"✓ Active: {count} hotkeys", fg=COLORS["success"])
    
    return hotkeys_frame
