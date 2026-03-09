"""
Hotkeys Screen for NWN Manager.

Provides UI for configuring custom keybindings.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from ui.ui_base import COLORS, ModernButton, ToggleSwitch, SectionFrame

def build_hotkeys_screen(app):
    """Hotkeys configuration screen."""
    self = app
    
    # Get config from app state
    # Use settings.hotkeys if available (preferred as it's the object)
    if hasattr(self, 'settings') and hasattr(self.settings, 'hotkeys'):
        hotkeys_cfg = self.settings.hotkeys
    else:
        # Fallback to dictionary if not yet converted
        hotkeys_cfg = getattr(self, 'hotkeys_config', {})

    hotkeys_frame = tk.Frame(self.content_frame, bg=COLORS["bg_root"])
    self.screens["hotkeys"] = hotkeys_frame

    # Header
    header = tk.Frame(hotkeys_frame, bg=COLORS["bg_root"])
    header.pack(fill="x", padx=40, pady=(20, 10))

    tk.Label(
        header,
        text="Global Hotkeys",
        font=("Segoe UI", 24, "bold"),
        bg=COLORS["bg_root"],
        fg=COLORS["fg_text"]
    ).pack(side="left")

    # Master Toggle
    toggle_frame = tk.Frame(header, bg=COLORS["bg_root"])
    toggle_frame.pack(side="right")
    
    tk.Label(toggle_frame, text="Status:", bg=COLORS["bg_root"], fg=COLORS["fg_dim"]).pack(side="left", padx=(0, 10))
    
    def _on_master_toggle():
        # Update underlying config
        val = self.hotkeys_enabled_var.get()
        if isinstance(hotkeys_cfg, dict):
            hotkeys_cfg["enabled"] = val
        else:
            hotkeys_cfg.enabled = val
        
        self.save_data()
        self._apply_saved_hotkeys()
        _refresh_hotkeys_list()

    master_toggle = ToggleSwitch(toggle_frame, variable=self.hotkeys_enabled_var, command=_on_master_toggle)
    master_toggle.pack(side="left")

    # Master Toggle Key Section
    master_key_frame = tk.Frame(hotkeys_frame, bg=COLORS["bg_root"])
    master_key_frame.pack(fill="x", padx=40, pady=(0, 15))

    tk.Label(
        master_key_frame,
        text="Master Toggle Key:",
        bg=COLORS["bg_root"],
        fg=COLORS["fg_dim"],
        font=("Segoe UI", 10)
    ).pack(side="left")

    # Current value
    if isinstance(hotkeys_cfg, dict):
        mt_key = hotkeys_cfg.get("master_toggle_key", "ALT+S")
    else:
        mt_key = hotkeys_cfg.master_toggle_key
        
    self.master_toggle_var = tk.StringVar(value=mt_key)
    
    def _on_master_key_change(*args):
        val = self.master_toggle_var.get().upper().strip()
        if val:
            if isinstance(hotkeys_cfg, dict):
                hotkeys_cfg["master_toggle_key"] = val
            else:
                hotkeys_cfg.master_toggle_key = val
            self.save_data()
            if hasattr(self, "multi_hotkey_manager"):
                self.multi_hotkey_manager.set_master_toggle(val)

    mt_entry = tk.Entry(master_key_frame, textvariable=self.master_toggle_var, width=10, bg=COLORS["bg_input"], fg=COLORS["accent"], relief="flat", font=("Segoe UI", 10, "bold"), justify="center")
    mt_entry.pack(side="left", padx=10)
    self.master_toggle_var.trace_add("write", _on_master_key_change)

    # Hotkeys List Container
    list_section = SectionFrame(hotkeys_frame, text="Configured Binds")
    list_section.pack(fill="both", expand=True, padx=40, pady=(0, 20))
    
    list_inner = tk.Frame(list_section, bg=COLORS["bg_root"])
    list_inner.pack(fill="both", expand=True, padx=1, pady=1)

    # Scrollable area
    canvas = tk.Canvas(list_inner, bg=COLORS["bg_root"], highlightthickness=0)
    scrollbar = ttk.Scrollbar(list_inner, orient="vertical", command=canvas.yview)
    self.hotkeys_list_frame = tk.Frame(canvas, bg=COLORS["bg_root"])

    def _update_hotkey_scroll(e=None):
        canvas.configure(scrollregion=canvas.bbox("all"))

    self.hotkeys_list_frame.bind("<Configure>", _update_hotkey_scroll)

    canvas_window = canvas.create_window((0, 0), window=self.hotkeys_list_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    def _on_canvas_configure(event):
        canvas.itemconfig(canvas_window, width=event.width)
    canvas.bind("<Configure>", _on_canvas_configure)

    canvas.pack(side="left", fill="both", expand=True)

    # Mousewheel scrolling
    def _on_mousewheel(event):
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def bind_mousewheel(widget):
        widget.bind("<MouseWheel>", _on_mousewheel)
        for child in widget.winfo_children():
            bind_mousewheel(child)

    canvas.bind("<MouseWheel>", _on_mousewheel)
    self.hotkeys_list_frame.bind("<MouseWheel>", _on_mousewheel)

    # Recursive bind for mousewheel
    self.root.after(100, lambda: bind_mousewheel(hotkeys_frame))

    def _refresh_hotkeys_list():
        for widget in self.hotkeys_list_frame.winfo_children():
            widget.destroy()
        
        if isinstance(hotkeys_cfg, dict):
            binds = hotkeys_cfg.get("binds", [])
        else:
            binds = hotkeys_cfg.binds
            
        if not binds:
            tk.Label(self.hotkeys_list_frame, text="No hotkeys configured.", bg=COLORS["bg_root"], fg=COLORS["fg_dim"]).pack(pady=20)
            return

        for i, bind in enumerate(binds):
            row = tk.Frame(self.hotkeys_list_frame, bg=COLORS["bg_panel"], padx=15, pady=8)
            row.pack(fill="x", pady=2)

            # Get field values regardless of whether it's dict or object
            is_enabled = bind.enabled if hasattr(bind, 'enabled') else bind.get("enabled", True)
            trigger = bind.trigger if hasattr(bind, 'trigger') else bind.get("trigger", "")
            comment = bind.comment if hasattr(bind, 'comment') else bind.get("comment", "")
            
            # Enable/Disable Bind
            en_var = tk.BooleanVar(value=is_enabled)
            
            def _make_toggle(idx=i, v=en_var):
                def cmd():
                    if isinstance(binds[idx], dict):
                        binds[idx]["enabled"] = v.get()
                    else:
                        binds[idx].enabled = v.get()
                    self.save_data()
                    self._apply_saved_hotkeys()
                return cmd

            ToggleSwitch(row, variable=en_var, command=_make_toggle()).pack(side="left", padx=(0, 15))

            # Bind Info
            info_f = tk.Frame(row, bg=COLORS["bg_panel"])
            info_f.pack(side="left", fill="x", expand=True)
            
            tk.Label(info_f, text=trigger, bg=COLORS["bg_panel"], fg=COLORS["accent"], font=("Segoe UI", 11, "bold")).pack(anchor="w")
            if comment:
                tk.Label(info_f, text=comment, bg=COLORS["bg_panel"], fg=COLORS["fg_dim"], font=("Segoe UI", 8)).pack(anchor="w")

            # Actions
            ModernButton(row, COLORS["bg_input"], COLORS["accent"], text="Edit", width=8, 
                         command=lambda idx=i: _edit_bind(idx)).pack(side="right", padx=(5, 0))
            ModernButton(row, COLORS["bg_input"], COLORS["danger"], text="Delete", width=8, 
                         command=lambda idx=i: _delete_bind(idx)).pack(side="right")

    def _delete_bind(idx):
        if isinstance(hotkeys_cfg, dict):
            binds = hotkeys_cfg.get("binds", [])
        else:
            binds = hotkeys_cfg.binds
            
        if messagebox.askyesno("Confirm", "Delete this hotkey?"):
            binds.pop(idx)
            self.save_data()
            self._apply_saved_hotkeys()
            _refresh_hotkeys_list()

    def _edit_bind(idx):
        from ui.dialogs.hotkey_dialog import HotkeyDialog
        from core.keybind_manager import HotkeyAction
        if isinstance(hotkeys_cfg, dict):
            binds = hotkeys_cfg.get("binds", [])
        else:
            binds = hotkeys_cfg.binds

        def on_save(updated_data):
            if isinstance(binds[idx], dict):
                binds[idx].update(updated_data)
            else:
                binds[idx] = HotkeyAction.from_dict(updated_data)
            self.save_data()
            self._apply_saved_hotkeys()
            _refresh_hotkeys_list()
            
        HotkeyDialog(self.root, is_new=False, hotkey_data=binds[idx], on_save=on_save)

    def _add_hotkey():
        from ui.dialogs.hotkey_dialog import HotkeyDialog
        from core.keybind_manager import HotkeyAction
        if isinstance(hotkeys_cfg, dict):
            binds = hotkeys_cfg.setdefault("binds", [])
        else:
            binds = hotkeys_cfg.binds

        def on_save(new_data):
            if isinstance(hotkeys_cfg, dict):
                binds.append(new_data)
            else:
                binds.append(HotkeyAction.from_dict(new_data))
            self.save_data()
            self._apply_saved_hotkeys()
            _refresh_hotkeys_list()
            
        HotkeyDialog(self.root, is_new=True, on_save=on_save)

    # Bottom Actions
    bottom = tk.Frame(hotkeys_frame, bg=COLORS["bg_root"])
    bottom.pack(fill="x", padx=40, pady=(0, 20))
    
    ModernButton(bottom, COLORS["accent"], COLORS["accent_hover"], text="+ Add Hotkey", width=15, command=_add_hotkey).pack(side="left")
    
    tk.Label(bottom, text="Hotkeys only work when game is focused.", bg=COLORS["bg_root"], fg=COLORS["fg_dim"], font=("Segoe UI", 9)).pack(side="right")

    self._refresh_hotkeys_list = _refresh_hotkeys_list
    _refresh_hotkeys_list()

    return hotkeys_frame
