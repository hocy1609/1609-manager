"""
Hotkeys Screen for NWN Manager.

Provides UI for configuring custom keybindings similar to AutoHotkey.
Redesigned to use scrollable list with per-key toggles.
"""

import tkinter as tk
from tkinter import ttk, messagebox

from ui.ui_base import COLORS, ModernButton, ToggleSwitch, SectionFrame, Separator


def build_hotkeys_screen(app):
    """Build the Hotkeys configuration screen."""
    self = app
    
    hotkeys_frame = tk.Frame(self.content_frame, bg=COLORS["bg_root"])
    self.screens["hotkeys"] = hotkeys_frame
    
    # Header with Global Toggle and Add Button
    header = tk.Frame(hotkeys_frame, bg=COLORS["bg_root"])
    header.pack(fill="x", padx=40, pady=(20, 10))
    
    tk.Label(
        header,
        text="Hotkeys",
        font=("Segoe UI", 24, "bold"),
        bg=COLORS["bg_root"],
        fg=COLORS["fg_text"]
    ).pack(side="left")

    # Right side of header: Add Button + Global Toggle
    header_right = tk.Frame(header, bg=COLORS["bg_root"])
    header_right.pack(side="right")

    def _add_hotkey():
        _open_hotkey_dialog(None)

    ModernButton(
        header_right, 
        COLORS["success"], 
        COLORS["success_hover"], 
        text="➕ Add New", 
        width=12, 
        command=_add_hotkey
    ).pack(side="left", padx=(0, 20))

    # Separator in header
    tk.Frame(header_right, width=1, height=24, bg=COLORS["fg_dim"]).pack(side="left", padx=(0, 20))
    
    # Enable toggle
    hotkeys_cfg = getattr(self, 'hotkeys_config', {"enabled": False, "binds": []})
    self.hotkeys_enabled_var = tk.BooleanVar(value=hotkeys_cfg.get("enabled", False))
    
    tk.Label(header_right, text="Global:", bg=COLORS["bg_root"], fg=COLORS["fg_dim"]).pack(side="left", padx=(0, 10))
    
    def _on_hotkeys_toggle(*args):
        # Apply changes
        _apply_hotkeys()
    
    self.hotkeys_enabled_var.trace_add("write", _on_hotkeys_toggle)
    
    hotkeys_toggle = ToggleSwitch(header_right, variable=self.hotkeys_enabled_var)
    hotkeys_toggle.pack(side="left")

    # Status label (below header)
    self.hotkeys_status_label = tk.Label(
        hotkeys_frame,
        text="",
        bg=COLORS["bg_root"],
        fg=COLORS["fg_dim"],
        font=("Segoe UI", 10)
    )
    self.hotkeys_status_label.pack(anchor="e", padx=40, pady=(0, 10))
    
    # Info Text
    tk.Label(
        hotkeys_frame,
        text="Configure hotkeys to send key sequences to NWN. Works only when game is active.",
        bg=COLORS["bg_root"],
        fg=COLORS["fg_dim"],
        font=("Segoe UI", 10)
    ).pack(anchor="w", padx=40, pady=(0, 10))

    Separator(hotkeys_frame, orient="horizontal", color=COLORS["accent"], thickness=2, padding=0).pack(fill="x", padx=40, pady=(0, 15))

    # Scrollable container for list
    list_container = tk.Frame(hotkeys_frame, bg=COLORS["bg_root"])
    list_container.pack(fill="both", expand=True, padx=40, pady=(0, 20))

    canvas = tk.Canvas(list_container, bg=COLORS["bg_root"], highlightthickness=0, bd=0)
    scrollbar = ttk.Scrollbar(list_container, orient="vertical", command=canvas.yview)
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
    
    # Bind mousewheel to canvas and all children
    def _bind_to_mousewheel(widget):
        widget.bind("<MouseWheel>", _on_mousewheel)
        for child in widget.winfo_children():
            _bind_to_mousewheel(child)

    canvas.bind("<MouseWheel>", _on_mousewheel)
    
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    
    # Hotkeys list management
    def _refresh_hotkeys_list():
        """Refresh the hotkeys list UI."""
        for widget in scrollable_frame.winfo_children():
            widget.destroy()
        
        binds = hotkeys_cfg.get("binds", [])
        
        if not binds:
            tk.Label(
                scrollable_frame, 
                text="No hotkeys added yet.", 
                bg=COLORS["bg_root"], 
                fg=COLORS["fg_dim"],
                font=("Segoe UI", 12)
            ).pack(pady=40)
            return

        for idx, bind in enumerate(binds):
            _create_hotkey_row(idx, bind)
        
        # Ensure scroll works after rebuild
        self.root.after(100, lambda: _bind_to_mousewheel(scrollable_frame))

    def _create_hotkey_row(idx, bind):
        """Create a single row for a hotkey."""
        row_bg = COLORS["bg_panel"] if idx % 2 == 0 else COLORS["bg_input"]
        row = tk.Frame(scrollable_frame, bg=row_bg, pady=8, padx=10)
        row.pack(fill="x", pady=2)
        
        # Enable Toggle (Leftmost)
        enabled_var = tk.BooleanVar(value=bind.get("enabled", True))
        
        def _toggle_bind(*args):
             bind["enabled"] = enabled_var.get()
             _save_hotkeys_config()
             _apply_hotkeys()
        
        enabled_var.trace_add("write", _toggle_bind)
        
        toggle = ToggleSwitch(row, variable=enabled_var, width=36, height=20)
        toggle.pack(side="left", padx=(0, 15))
        # Important: manually set bg for toggle to match row
        toggle.update_colors({"bg_root": row_bg}) 
        
        # Trigger Key
        trigger = bind.get("trigger", "???")
        tk.Label(
            row, text=trigger, 
            bg=row_bg, fg=COLORS["accent"], 
            font=("Segoe UI", 11, "bold"), width=8, anchor="w"
        ).pack(side="left")
        
        # Details (Sequence + Comment)
        details_frame = tk.Frame(row, bg=row_bg)
        details_frame.pack(side="left", fill="x", expand=True)
        
        # Sequence formatting
        sequence = bind.get("sequence", [])
        seq_parts = [s.replace("NUMPAD", "") if s.startswith("NUMPAD") else s for s in sequence]
        seq_str = "-".join(seq_parts)
        if bind.get("rightClick", False):
            seq_str = "R-Click + " + seq_str
            
        tk.Label(
            details_frame, text=seq_str, 
            bg=row_bg, fg=COLORS["fg_text"], 
            font=("Segoe UI", 10), anchor="w"
        ).pack(fill="x")
        
        comment = bind.get("comment", "")
        if comment:
            tk.Label(
                details_frame, text=comment, 
                bg=row_bg, fg=COLORS["fg_dim"], 
                font=("Segoe UI", 9, "italic"), anchor="w"
            ).pack(fill="x")
            
        # Action Buttons (Edit/Delete)
        actions_frame = tk.Frame(row, bg=row_bg)
        actions_frame.pack(side="right")
        
        def _edit_this(i=idx):
            _open_hotkey_dialog(i)
            
        def _delete_this(i=idx):
            if messagebox.askyesno("Delete", "Delete this hotkey?", parent=self.root):
                binds.pop(i)
                _refresh_hotkeys_list()
                _save_hotkeys_config()
                _apply_hotkeys()

        ModernButton(
            actions_frame, COLORS.get("btn_bg", "#444444"), COLORS.get("btn_hover", "#555555"), 
            text="✏️", width=3, command=_edit_this
        ).pack(side="left", padx=2)
        
        ModernButton(
            actions_frame, COLORS["danger"], COLORS["danger_hover"], 
            text="🗑️", width=3, command=_delete_this
        ).pack(side="left", padx=2)

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
            # Filter enabled individual binds
            active_binds = [b for b in binds if b.get("enabled", True)]
            actions = [HotkeyAction.from_dict(b) for b in active_binds]
            
            count = self.multi_hotkey_manager.register_hotkeys(actions)
            self.hotkeys_status_label.config(
                text=f"✓ Active: {count} hotkeys",
                fg=COLORS["success"]
            )
        else:
            self.multi_hotkey_manager.unregister_all()
            status_text = "Disabled (Global)" if not enabled else "No active hotkeys"
            self.hotkeys_status_label.config(
                text=status_text,
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
        try:
            x = self.root.winfo_x() + (self.root.winfo_width() - 450) // 2
            y = self.root.winfo_y() + (self.root.winfo_height() - 350) // 2
            dialog.geometry(f"+{x}+{y}")
        except Exception:
            pass
        
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
        tk.Label(form, text="Action Sequence:", bg=COLORS["bg_root"], fg=COLORS["fg_text"]).grid(row=1, column=0, sticky="w", pady=5)
        
        existing_seq = existing.get("sequence", [])
        seq_parts = []
        for s in existing_seq:
            if s.startswith("NUMPAD"):
                seq_parts.append(s.replace("NUMPAD", ""))
            else:
                seq_parts.append(s)
        seq_str = "-".join(seq_parts)
        sequence_var = tk.StringVar(value=seq_str)
        sequence_entry = tk.Entry(form, textvariable=sequence_var, width=30, bg=COLORS["bg_input"], fg=COLORS["fg_text"])
        sequence_entry.grid(row=1, column=1, sticky="w", pady=5, padx=(10, 0))
        
        tk.Label(form, text="Keys/clicks: F2-LEFTCLICK-F2, 0-9-2", bg=COLORS["bg_root"], fg=COLORS["fg_dim"], font=("Segoe UI", 9)).grid(row=2, column=1, sticky="w", padx=(10, 0))
        
        # Right click
        tk.Label(form, text="Right-click first:", bg=COLORS["bg_root"], fg=COLORS["fg_text"]).grid(row=3, column=0, sticky="w", pady=5)
        rightclick_var = tk.BooleanVar(value=existing.get("rightClick", False))
        global_bg = COLORS["bg_root"]
        rightclick_cb = tk.Checkbutton(form, variable=rightclick_var, bg=global_bg, activebackground=global_bg, selectcolor=COLORS["bg_input"])
        rightclick_cb.grid(row=3, column=1, sticky="w", pady=5, padx=(10, 0))
        
        # Comment
        tk.Label(form, text="Comment:", bg=COLORS["bg_root"], fg=COLORS["fg_text"]).grid(row=4, column=0, sticky="w", pady=5)
        comment_var = tk.StringVar(value=existing.get("comment", ""))
        comment_entry = tk.Entry(form, textvariable=comment_var, width=30, bg=COLORS["bg_input"], fg=COLORS["fg_text"])
        comment_entry.grid(row=4, column=1, sticky="w", pady=5, padx=(10, 0))
        
        # Buttons
        btn_row = tk.Frame(form, bg=COLORS["bg_root"])
        btn_row.grid(row=6, column=0, columnspan=2, pady=(20, 0))
        
        def _save():
            trigger = trigger_var.get().strip().upper()
            seq_raw = sequence_var.get().strip()
            
            if not trigger:
                messagebox.showwarning("Error", "Trigger key is required", parent=dialog)
                return
            
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
                "enabled": existing.get("enabled", True), # Preserve existing enabled state or default True
            }
            
            if is_edit:
                binds[edit_idx] = bind_data
            else:
                binds.append(bind_data)
            
            hotkeys_cfg["binds"] = binds
            _refresh_hotkeys_list()
            _save_hotkeys_config()
            _apply_hotkeys()
            dialog.destroy()
        
        ModernButton(btn_row, COLORS["success"], COLORS["success_hover"], text="Save", width=10, command=_save).pack(side="left", padx=(0, 10))
        ModernButton(btn_row, COLORS["bg_input"], COLORS["border"], text="Cancel", width=10, command=dialog.destroy).pack(side="left")
    
    # Initial load
    _refresh_hotkeys_list()
    _apply_hotkeys() # Ensure state is consistent on load
    
    return hotkeys_frame
