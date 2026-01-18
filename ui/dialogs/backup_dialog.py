import os
import shutil
import tkinter as tk
from tkinter import messagebox
from datetime import datetime
from ui.ui_base import BaseDialog, ModernButton, COLORS


class RestoreBackupDialog(BaseDialog):
    """Dialog for restoring program settings from backup files."""
    
    def __init__(self, parent, backup_dir, settings_path, on_export=None, on_import=None):
        super().__init__(parent, "Restore Settings Backup", 500, 420)
        self.backup_dir = backup_dir
        self.settings_path = settings_path  # Path to current nwn_settings.json

        content = tk.Frame(self, bg=COLORS["bg_root"])
        content.pack(fill="both", expand=True, padx=20, pady=10)

        # Header
        tk.Label(
            content,
            text="Select a backup to restore:",
            bg=COLORS["bg_root"],
            fg=COLORS["fg_text"],
            font=("Segoe UI", 11, "bold"),
        ).pack(anchor="w", pady=(0, 5))
        
        tk.Label(
            content,
            text="Backups are created automatically when settings are saved.",
            bg=COLORS["bg_root"],
            fg=COLORS["fg_dim"],
            font=("Segoe UI", 9),
        ).pack(anchor="w", pady=(0, 10))

        # Listbox with scrollbar
        list_frame = tk.Frame(content, bg=COLORS["bg_root"])
        list_frame.pack(fill="both", expand=True, pady=5)
        
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")
        
        self.lb = tk.Listbox(
            list_frame,
            bg=COLORS["bg_input"],
            fg=COLORS["fg_text"],
            bd=0,
            highlightthickness=1,
            highlightbackground=COLORS["border"],
            selectbackground=COLORS["accent"],
            selectforeground=COLORS["text_dark"],
            font=("Segoe UI", 10),
            yscrollcommand=scrollbar.set,
        )
        self.lb.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.lb.yview)

        # Load backup files
        self.files: list[str] = []
        self.backup_info: dict[str, str] = {}  # filename -> display text
        
        if os.path.exists(backup_dir):
            try:
                # Look for nwn_settings_*.json backup files
                all_files = [
                    f for f in os.listdir(backup_dir)
                    if f.startswith("nwn_settings_") and f.endswith(".json")
                ]
                # Sort by modification time, newest first
                all_files.sort(
                    key=lambda x: os.path.getmtime(os.path.join(backup_dir, x)),
                    reverse=True,
                )
                self.files = all_files
                
                for f in self.files:
                    # Parse timestamp from filename: nwn_settings_YYYYMMDD_HHMMSS.json
                    try:
                        timestamp_str = f.replace("nwn_settings_", "").replace(".json", "")
                        dt = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                        display_text = dt.strftime("%Y-%m-%d %H:%M:%S")
                    except:
                        display_text = f
                    
                    self.backup_info[f] = display_text
                    self.lb.insert(tk.END, f"  📄 {display_text}")
                    
            except Exception as e:
                print(f"Error listing backups: {e}")
        
        if not self.files:
            self.lb.insert(tk.END, "  No backups available")
            self.lb.config(state="disabled")

        # Import/Export integration row
        ie_frame = tk.LabelFrame(
            content,
            text=" Import / Export Profiles ",
            bg=COLORS["bg_root"],
            fg=COLORS["fg_dim"],
            bd=1,
            relief="solid",
        )
        ie_frame.pack(fill="x", pady=(10, 10))
        ie_inner = tk.Frame(ie_frame, bg=COLORS["bg_root"])
        ie_inner.pack(fill="x", padx=8, pady=6)
        ModernButton(
            ie_inner,
            COLORS["bg_input"],
            COLORS["border"],
            text="Export",
            width=10,
            command=lambda: on_export(self) if on_export else None,
            tooltip="Export profiles to JSON file",
        ).pack(side="left", padx=(0, 6))
        ModernButton(
            ie_inner,
            COLORS["bg_input"],
            COLORS["border"],
            text="Import",
            width=10,
            command=lambda: on_import(self) if on_import else None,
            tooltip="Import profiles from JSON file",
        ).pack(side="left")

        # Bottom buttons
        btn_frame = tk.Frame(content, bg=COLORS["bg_root"])
        btn_frame.pack(fill="x", pady=4, side="bottom")
        
        self.restore_btn = ModernButton(
            btn_frame,
            COLORS["warning"],
            COLORS["warning_hover"],
            text="Restore",
            width=10,
            command=self.restore,
            tooltip="Restore selected backup",
        )
        self.restore_btn.pack(side="right", padx=(10, 0))
        
        if not self.files:
            self.restore_btn.config(state="disabled")
        
        ModernButton(
            btn_frame,
            COLORS["bg_panel"],
            COLORS["border"],
            text="Close",
            width=10,
            command=self.destroy,
        ).pack(side="right")

        self.finalize_window(parent)

    def restore(self):
        """Restore selected backup file."""
        idx = self.lb.curselection()
        if not idx:
            messagebox.showwarning(
                "No Selection",
                "Please select a backup to restore.",
                parent=self
            )
            return

        if idx[0] >= len(self.files):
            return
            
        filename = self.files[idx[0]]
        src = os.path.join(self.backup_dir, filename)
        
        if not os.path.exists(src):
            messagebox.showerror(
                "Error",
                f"Backup file not found:\n{filename}",
                parent=self
            )
            return
        
        display_time = self.backup_info.get(filename, filename)
        
        if messagebox.askyesno(
            "Confirm Restore",
            f"Restore settings from backup?\n\n"
            f"Backup date: {display_time}\n\n"
            f"Current settings will be replaced.\n"
            f"The application will need to restart for changes to take effect.",
            parent=self,
        ):
            try:
                # Create a backup of current settings before restoring
                if os.path.exists(self.settings_path):
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    pre_restore_backup = os.path.join(
                        self.backup_dir,
                        f"nwn_settings_{timestamp}_pre_restore.json"
                    )
                    shutil.copy2(self.settings_path, pre_restore_backup)
                
                # Restore the backup
                shutil.copy2(src, self.settings_path)
                
                messagebox.showinfo(
                    "Success",
                    "Settings restored successfully!\n\n"
                    "Please restart the application for changes to take effect.",
                    parent=self,
                )
                self.destroy()
            except Exception as e:
                messagebox.showerror(
                    "Error",
                    f"Failed to restore backup:\n{e}",
                    parent=self
                )
