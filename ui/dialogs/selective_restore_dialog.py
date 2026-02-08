"""
Selective Restore Dialog for NWN Manager.
Allows users to choose which data categories to restore from a backup file.
"""

import tkinter as tk
from tkinter import messagebox
from ui.ui_base import BaseDialog, ModernButton, COLORS, ToggleSwitch


class SelectiveRestoreDialog(BaseDialog):
    """Dialog for selective restoration of backup data."""
    
    def __init__(self, parent, backup_data: dict, on_restore):
        """
        Initialize the dialog.
        
        Args:
            parent: Parent window
            backup_data: Dictionary containing backup data to restore
            on_restore: Callback function (selected_categories: dict) -> None
        """
        super().__init__(parent, "Restore Backup", 500, 560)
        self.backup_data = backup_data
        self.on_restore = on_restore
        self.category_vars = {}
        
        content = tk.Frame(self, bg=COLORS["bg_root"])
        content.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Header
        tk.Label(
            content,
            text="Select data to restore:",
            bg=COLORS["bg_root"],
            fg=COLORS["fg_text"],
            font=("Segoe UI", 12, "bold"),
        ).pack(anchor="w", pady=(0, 5))
        
        # Backup info
        timestamp = backup_data.get("timestamp", "Unknown")
        version = backup_data.get("version", "1.0")
        tk.Label(
            content,
            text=f"Backup: {timestamp[:19] if len(timestamp) > 19 else timestamp}  •  v{version}",
            bg=COLORS["bg_root"],
            fg=COLORS["fg_dim"],
            font=("Segoe UI", 9),
        ).pack(anchor="w", pady=(0, 15))
        
        # Categories frame
        categories_frame = tk.LabelFrame(
            content,
            text=" Data Categories ",
            bg=COLORS["bg_root"],
            fg=COLORS["fg_dim"],
            bd=1,
            relief="solid",
        )
        categories_frame.pack(fill="x", pady=(0, 10))
        categories_inner = tk.Frame(categories_frame, bg=COLORS["bg_root"])
        categories_inner.pack(fill="x", padx=12, pady=10)
        
        # Define categories with their data keys and display info
        self.categories = []
        
        # Profiles - E9F9 = Contact/Profile icon
        profiles = backup_data.get("profiles", [])
        if profiles:
            self.categories.append({
                "key": "profiles",
                "label": f"\uE9F9 Profiles ({len(profiles)} items)",
                "description": "Account profiles with CD keys and settings",
                "data": profiles,
            })
        
        # Servers - E774 = Globe icon
        servers = backup_data.get("servers", [])
        if servers:
            self.categories.append({
                "key": "servers",
                "label": f"\uE774 Servers ({len(servers)} items)",
                "description": "Server list with IPs and ports",
                "data": servers,
            })
        
        # Hotkeys - E765 = Keyboard icon
        hotkeys = backup_data.get("hotkeys", {})
        if hotkeys and (hotkeys.get("binds") or hotkeys.get("enabled")):
            binds_count = len(hotkeys.get("binds", []))
            self.categories.append({
                "key": "hotkeys",
                "label": f"\uE765 Hotkeys ({binds_count} bindings)",
                "description": "Hotkey configurations and bindings",
                "data": hotkeys,
            })
        
        # Log Monitor - E9D2 = Chart icon
        log_monitor = backup_data.get("log_monitor", {})
        if log_monitor and any(log_monitor.values()):
            self.categories.append({
                "key": "log_monitor",
                "label": "\uE9D2 Log Monitor",
                "description": "Log monitor, Slayer, and Auto-Fog settings",
                "data": log_monitor,
            })
        
        # App Settings - E713 = Settings icon
        app_settings = backup_data.get("app_settings", {})
        if app_settings:
            theme = app_settings.get("theme", "dark")
            self.categories.append({
                "key": "app_settings",
                "label": f"\uE713 App Settings (theme: {theme})",
                "description": "Theme, paths, coordinates, and other preferences",
                "data": app_settings,
            })
        
        # CD Keys (from app_settings) - E8D7 = Key icon
        saved_keys = app_settings.get("saved_keys", [])
        if saved_keys:
            self.categories.append({
                "key": "saved_keys",
                "label": f"\uE8D7 CD Keys ({len(saved_keys)} keys)",
                "description": "Saved CD keys for quick selection",
                "data": saved_keys,
            })
        
        # Create checkboxes for each category
        for cat in self.categories:
            row = tk.Frame(categories_inner, bg=COLORS["bg_root"])
            row.pack(fill="x", pady=4)
            
            var = tk.BooleanVar(value=True)
            self.category_vars[cat["key"]] = var
            
            # Checkbox
            cb = tk.Checkbutton(
                row,
                variable=var,
                bg=COLORS["bg_root"],
                fg=COLORS["fg_text"],
                activebackground=COLORS["bg_root"],
                activeforeground=COLORS["fg_text"],
                selectcolor=COLORS["bg_input"],
                highlightthickness=0,
                bd=0,
            )
            cb.pack(side="left")
            
            # Label
            lbl_frame = tk.Frame(row, bg=COLORS["bg_root"])
            lbl_frame.pack(side="left", fill="x", expand=True)
            
            tk.Label(
                lbl_frame,
                text=cat["label"],
                bg=COLORS["bg_root"],
                fg=COLORS["fg_text"],
                font=("Segoe UI", 10),
                cursor="hand2",
            ).pack(anchor="w")
            
            tk.Label(
                lbl_frame,
                text=cat["description"],
                bg=COLORS["bg_root"],
                fg=COLORS["fg_dim"],
                font=("Segoe UI", 8),
            ).pack(anchor="w")
            
            # Make label clickable
            for widget in lbl_frame.winfo_children():
                widget.bind("<Button-1>", lambda e, v=var: v.set(not v.get()))
        
        # No data message if empty
        if not self.categories:
            tk.Label(
                categories_inner,
                text="No restorable data found in this backup.",
                bg=COLORS["bg_root"],
                fg=COLORS["warning"],
                font=("Segoe UI", 10),
            ).pack(pady=20)
        
        # Select All / None buttons
        btn_row = tk.Frame(content, bg=COLORS["bg_root"])
        btn_row.pack(fill="x", pady=(5, 10))
        
        def select_all():
            for var in self.category_vars.values():
                var.set(True)
        
        def select_none():
            for var in self.category_vars.values():
                var.set(False)
        
        ModernButton(
            btn_row,
            COLORS["bg_input"],
            COLORS["border"],
            text="Select All",
            width=10,
            command=select_all,
        ).pack(side="left", padx=(0, 5))
        
        ModernButton(
            btn_row,
            COLORS["bg_input"],
            COLORS["border"],
            text="Select None",
            width=10,
            command=select_none,
        ).pack(side="left")
        
        # Warning note - E7BA = Warning icon
        tk.Label(
            content,
            text="\uE7BA Selected categories will replace current data",
            bg=COLORS["bg_root"],
            fg=COLORS["warning"],
            font=("Segoe UI", 9),
        ).pack(anchor="w", pady=(5, 10))
        
        # Bottom buttons
        bottom_frame = tk.Frame(content, bg=COLORS["bg_root"])
        bottom_frame.pack(fill="x", side="bottom", pady=(10, 0))
        
        ModernButton(
            bottom_frame,
            COLORS["bg_panel"],
            COLORS["border"],
            text="Cancel",
            width=10,
            command=self.destroy,
        ).pack(side="right")
        
        self.restore_btn = ModernButton(
            bottom_frame,
            COLORS["success"],
            COLORS["success_hover"],
            text="Restore",
            width=10,
            command=self._do_restore,
        )
        self.restore_btn.pack(side="right", padx=(0, 10))
        
        if not self.categories:
            self.restore_btn.config(state="disabled")
        
        self.finalize_window(parent)
    
    def _do_restore(self):
        """Execute the restore with selected categories."""
        selected = {
            key: var.get()
            for key, var in self.category_vars.items()
        }
        
        # Check if anything selected
        if not any(selected.values()):
            messagebox.showwarning(
                "No Selection",
                "Please select at least one category to restore.",
                parent=self,
            )
            return
        
        # Build restore data
        restore_data = {}
        for cat in self.categories:
            if selected.get(cat["key"], False):
                restore_data[cat["key"]] = cat["data"]
        
        # Count what will be restored
        items = []
        if "profiles" in restore_data:
            items.append(f"{len(restore_data['profiles'])} profiles")
        if "servers" in restore_data:
            items.append(f"{len(restore_data['servers'])} servers")
        if "hotkeys" in restore_data:
            items.append("hotkeys")
        if "log_monitor" in restore_data:
            items.append("log monitor settings")
        if "app_settings" in restore_data:
            items.append("app settings")
        if "saved_keys" in restore_data:
            items.append(f"{len(restore_data['saved_keys'])} CD keys")
        
        summary = ", ".join(items) if items else "selected data"
        
        if messagebox.askyesno(
            "Confirm Restore",
            f"Restore the following data?\n\n• {chr(10).join('• ' + i for i in items) if items else 'Nothing selected'}\n\nThis will replace your current settings.",
            parent=self,
        ):
            try:
                self.on_restore(restore_data)
                self.destroy()
            except Exception as e:
                messagebox.showerror(
                    "Restore Error",
                    f"Failed to restore data:\n{e}",
                    parent=self,
                )
