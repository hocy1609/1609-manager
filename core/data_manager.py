import os
import time
import json
import shutil
import logging
from datetime import datetime
from tkinter import filedialog, messagebox

from core.models import Settings, Server, Profile, LogMonitorConfig, HotkeysConfig, load_settings, save_settings
from core.storage import SETTINGS_FILE, SESSIONS_FILE
from core.constants import LOG_FILENAME
from utils.win_automation import auto_detect_nwn_path


class DataManager:
    """Handles loading, saving, importing, and exporting application data."""
    
    def __init__(self, app):
        self.app = app

    def migrate_old_settings(self):
        """Migrate settings files from old location (app_dir) to new location (data_dir/1609 settings)."""
        try:
            old_settings = os.path.join(self.app.app_dir, SETTINGS_FILE)
            old_sessions = os.path.join(self.app.app_dir, SESSIONS_FILE)
            old_log = os.path.join(self.app.app_dir, LOG_FILENAME)
            
            # Migrate settings
            if os.path.exists(old_settings) and not os.path.exists(self.app.settings_path):
                try:
                    shutil.move(old_settings, self.app.settings_path)
                    logging.info(f"Migrated {SETTINGS_FILE} to new location")
                except Exception as e:
                    logging.exception(f"Failed to migrate {SETTINGS_FILE}")
            
            # Migrate sessions
            if os.path.exists(old_sessions) and not os.path.exists(self.app.sessions_path):
                try:
                    shutil.move(old_sessions, self.app.sessions_path)
                    logging.info(f"Migrated {SESSIONS_FILE} to new location")
                except Exception as e:
                    logging.exception(f"Failed to migrate {SESSIONS_FILE}")
            
            # Migrate log (copy instead of move - log file may be in use)
            if os.path.exists(old_log) and not os.path.exists(self.app.log_path):
                try:
                    shutil.copy2(old_log, self.app.log_path)
                    logging.info(f"Copied {LOG_FILENAME} to new location")
                except PermissionError:
                    pass  # Log file in use, skip silently
                except Exception as e:
                    pass  # Non-critical, skip
        except Exception as e:
            logging.exception("Error during settings migration")

    def backup_settings(self):
        """Create a timestamped backup of nwn_settings.json in the backups folder."""
        try:
            if not os.path.exists(self.app.settings_path):
                return  # Nothing to backup
            
            # Only backup once per minute to avoid excessive backups
            last_backup_time = getattr(self.app, '_last_backup_time', 0)
            current_time = time.time()
            if current_time - last_backup_time < 60:
                return  # Skip backup if less than 1 minute since last
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"nwn_settings_{timestamp}.json"
            backup_path = os.path.join(self.app.backups_dir, backup_name)
            
            shutil.copy2(self.app.settings_path, backup_path)
            self.app._last_backup_time = current_time
            
            # Cleanup old backups (keep only last 10)
            self.cleanup_old_backups()
        except Exception as e:
            logging.exception("Failed to create settings backup")

    def cleanup_old_backups(self, max_backups: int = 10):
        """Remove old backups keeping only the most recent ones."""
        try:
            backup_files = [
                os.path.join(self.app.backups_dir, f)
                for f in os.listdir(self.app.backups_dir)
                if f.startswith("nwn_settings_") and f.endswith(".json")
            ]
            backup_files.sort(key=os.path.getmtime, reverse=True)
            
            # Remove excess backups
            for old_backup in backup_files[max_backups:]:
                try:
                    os.remove(old_backup)
                except Exception:
                    pass
        except Exception:
            pass

    def load_data(self):
        default_docs = os.path.join(
            os.path.expanduser("~"), "Documents", "Neverwinter Nights"
        )
        detected_exe = auto_detect_nwn_path()
        default_exe = (
            detected_exe
            if detected_exe
            else r"C:\Program Files (x86)\Steam\steamapps\common\Neverwinter Nights\bin\win32\nwmain.exe"
        )

        try:
            settings = load_settings(self.app.settings_path, default_docs, default_exe)
        except Exception as e:
            self.app.log_error("load_settings", e)
            settings = Settings.defaults(default_docs, default_exe)

        # Load server groups
        self.app.server_group = settings.server_group
        self.app.server_groups = settings.server_groups
        
        # Set servers from current group
        if self.app.server_group in self.app.server_groups:
            self.app.servers = self.app.server_groups[self.app.server_group]
        else:
            self.app.servers = self.app.server_groups.get("siala", [])
        
        self.app.profiles = list(settings.profiles)  # Store as List[Profile], not List[Dict]
        # Fix doc_path if it contains USER placeholder
        doc_path = settings.doc_path
        if "USER" in doc_path or not os.path.exists(doc_path):
            doc_path = default_docs
        self.app.doc_path_var.set(doc_path)
        self.app.exe_path_var.set(settings.exe_path if os.path.exists(settings.exe_path) else default_exe)
        self.app.use_server_var.set(settings.auto_connect)

        self.app.exit_x = settings.exit_coords_x
        self.app.exit_y = settings.exit_coords_y
        self.app.confirm_x = settings.confirm_coords_x
        self.app.confirm_y = settings.confirm_coords_y
        self.app.exit_speed = settings.exit_speed
        self.app.esc_count = settings.esc_count
        self.app.clip_margin = settings.clip_margin
        self.app.show_tooltips = settings.show_tooltips
        self.app.theme = settings.theme
        self.app.category_order = list(settings.category_order)  # User-defined category order

        try:
            import ui.ui_base as _uib

            _uib.TOOLTIPS_ENABLED = self.app.show_tooltips
            try:
                _uib.set_theme(self.app.theme, root=self.app.root)
            except Exception:
                _uib.set_theme(self.app.theme)
        except Exception:
            logging.exception("Unhandled exception")

        try:
            if self.app.servers:
                srv_names = [s["name"] for s in self.app.servers]
                last_srv = settings.last_server
                if last_srv in srv_names:
                    self.app.server_var.set(last_srv)
                else:
                    self.app.server_var.set(srv_names[0])
        except Exception:
            logging.exception("Unhandled exception")

        # Log monitor path should always use real user's Documents folder
        real_docs_path = os.path.join(os.path.expanduser("~"), "Documents", "Neverwinter Nights")
        lm_default_path = os.path.join(real_docs_path, "logs", "nwclientLog1.txt")
        lm_cfg = settings.log_monitor
        if lm_cfg.log_path == "" or "USER" in lm_cfg.log_path:
            lm_cfg.log_path = lm_default_path
        self.app.log_monitor_state.config = lm_cfg.to_dict()
        self.app.log_monitor_state.config.setdefault("open_wounds", {"enabled": False, "key": "F1"})
        self.app.log_monitor_state.config.setdefault("keybind", {"enabled": False, "key": "F10"})

        # Load hotkeys config from top-level settings
        self.app.hotkeys_config = settings.hotkeys.to_dict()
        
        # Load sessions from settings
        self.app._settings_sessions = dict(settings.sessions)
        
        # Load saved CD keys
        self.app.saved_keys = list(settings.saved_keys)
        
        # Store settings for easier access by other components
        self.app.settings = settings
        
        # Auto-import key from cdkey.ini if no saved keys exist
        if not self.app.saved_keys:
            cdkey_path = os.path.join(doc_path, "nwncdkey.ini")
            if os.path.exists(cdkey_path):
                try:
                    with open(cdkey_path, "r", encoding="utf-8", errors="ignore") as f:
                        for line in f:
                            if line.strip().startswith("Key1="):
                                key_value = line.strip().split("=", 1)[1].strip()
                                if key_value and len(key_value) > 10:
                                    self.app.saved_keys.append({"name": "Main Key", "key": key_value})
                                break
                except Exception:
                    pass

        if not os.path.exists(self.app.settings_path):
            try:
                self.save_data()
            except Exception:
                logging.exception("Unhandled exception")

    def save_data(self):
        try:
            # Create backup of existing settings before saving
            self.backup_settings()
            
            servers = [Server.from_dict(s) if isinstance(s, dict) else s for s in self.app.servers]
            profiles = [Profile.from_dict(p) if isinstance(p, dict) else p for p in self.app.profiles]
            lm_cfg = LogMonitorConfig.from_dict(self.app.log_monitor_state.config or {})
            hotkeys_cfg = HotkeysConfig.from_dict(getattr(self.app, "hotkeys_config", {}))
            # Get current sessions from SessionManager
            sessions_data = self.app.sessions.sessions if hasattr(self.app, 'sessions') else {}
            
            # Update current group's servers before saving
            if hasattr(self.app, 'server_groups') and hasattr(self.app, 'server_group'):
                self.app.server_groups[self.app.server_group] = self.app.servers
            
            settings = Settings(
                doc_path=self.app.doc_path_var.get(),
                exe_path=self.app.exe_path_var.get(),
                servers=servers,
                profiles=profiles,
                auto_connect=self.app.use_server_var.get(),
                last_server=self.app.server_var.get(),
                exit_coords_x=self.app.exit_x,
                exit_coords_y=self.app.exit_y,
                confirm_coords_x=self.app.confirm_x,
                confirm_coords_y=self.app.confirm_y,
                log_monitor=lm_cfg,
                hotkeys=hotkeys_cfg,
                sessions=sessions_data,
                exit_speed=getattr(self.app, "exit_speed", 0.1),
                esc_count=getattr(self.app, "esc_count", 1),
                clip_margin=getattr(self.app, "clip_margin", 48),
                show_tooltips=getattr(self.app, "show_tooltips", True),
                theme=getattr(self.app, "theme", "dark"),
                category_order=getattr(self.app, "category_order", []),
                disable_hotkeys_on_multi_session=getattr(self.app.settings, "disable_hotkeys_on_multi_session", False),
            )
            
            # Sync startup registry (failsafe)
            try:
                from utils.win_automation import set_run_on_startup
                set_run_on_startup(getattr(self.app, "run_on_startup", False))
            except Exception:
                pass
                
            save_settings(self.app.settings_path, settings)
        except Exception as e:
            self.app.log_error("save_data", e)
            print(f"SAVE ERROR: {e}")

        # DEBUG: Print what we just saved
        try:
            print(f"DEBUG: Saved keys count: {len(getattr(self.app, 'saved_keys', []))}")
            if getattr(self.app, 'saved_keys', []):
                print(f"DEBUG: Saved keys content: {self.app.saved_keys}")
            
            hk = getattr(self.app, 'hotkeys_config', {})
            print(f"DEBUG: Hotkeys config: {hk}")
        except Exception as e:
            print(f"DEBUG ERROR: {e}")

    def export_data(self, parent=None):
        parent = parent or self.app.root
        timestamp = datetime.now().strftime("%Y%m%d")
        default_name = f"nwn_manager_profiles_{timestamp}.json"

        f = filedialog.asksaveasfilename(
            defaultextension=".json",
            initialfile=default_name,
            filetypes=[("JSON Files", "*.json")],
            title="Export Profiles",
            parent=parent,
        )
        if not f:
            return

        data_to_export = {
            "version": "1.0",
            "timestamp": datetime.now().isoformat(),
            "profiles": [p.to_dict() if hasattr(p, 'to_dict') else p for p in self.app.profiles],
            "servers": self.app.servers,
            "hotkeys": getattr(self.app, "hotkeys_config", {}),
            "log_monitor": self.app.log_monitor_state.config if hasattr(self.app, 'log_monitor_state') else {},
            "app_settings": {
                "theme": getattr(self.app, "theme", "dark"),
                "auto_connect": self.app.use_server_var.get(),
                "doc_path": self.app.doc_path_var.get(),
                "exe_path": self.app.exe_path_var.get(),
                "exit_coords_x": getattr(self.app, "exit_x", 0),
                "exit_coords_y": getattr(self.app, "exit_y", 0),
                "confirm_coords_x": getattr(self.app, "confirm_x", 0),
                "confirm_coords_y": getattr(self.app, "confirm_y", 0),
                "exit_speed": getattr(self.app, "exit_speed", 0.1),
                "esc_count": getattr(self.app, "esc_count", 1),
                "clip_margin": getattr(self.app, "clip_margin", 48),
                "server_group": getattr(self.app, "server_group", "siala"),
                "saved_keys": getattr(self.app, "saved_keys", []),
                "minimize_to_tray": getattr(self.app, "minimize_to_tray", True),
                "run_on_startup": getattr(self.app, "run_on_startup", False),
            }
        }

        try:
            with open(f, "w", encoding="utf-8") as outfile:
                json.dump(data_to_export, outfile, indent=4, ensure_ascii=False)
            messagebox.showinfo(
                "Export Success",
                f"Data saved to:\n{f}",
                parent=parent,
            )
        except Exception as e:
            self.app.log_error("export_data", e)
            messagebox.showerror("Export Error", str(e), parent=parent)

    def import_data(self, parent=None):
        """Import backup data with selective restore dialog."""
        from ui.dialogs import SelectiveRestoreDialog
        
        parent = parent or self.app.root

        f = filedialog.askopenfilename(
            filetypes=[("JSON Files", "*.json")],
            title="Restore Backup",
            parent=parent,
        )
        if not f:
            return

        try:
            with open(f, "r", encoding="utf-8") as infile:
                backup_data = json.load(infile)
            
            # Check if it's a valid backup or legacy profiles-only file
            if isinstance(backup_data, list):
                # Legacy format: just a list of profiles
                backup_data = {"profiles": backup_data, "version": "legacy"}
            
            def on_restore(selected_data: dict):
                """Apply selected data categories."""
                try:
                    from core.models import Profile
                    
                    merge_mode = selected_data.pop("_merge", False)
                    
                    # Restore Profiles
                    if "profiles" in selected_data:
                        imported = []
                        for p in selected_data["profiles"]:
                            if isinstance(p, dict):
                                try:
                                    imported.append(Profile.from_dict(p))
                                except Exception:
                                    imported.append(p)
                            else:
                                imported.append(p)
                        
                        if merge_mode:
                            # Build set of existing profile identifiers
                            existing_ids = set()
                            for ep in self.app.profiles:
                                name = ep.playerName if hasattr(ep, 'playerName') else ep.get("playerName", "")
                                key = ep.cdKey if hasattr(ep, 'cdKey') else ep.get("cdKey", "")
                                existing_ids.add((name, key))
                            
                            added = 0
                            for ip in imported:
                                name = ip.playerName if hasattr(ip, 'playerName') else ip.get("playerName", "")
                                key = ip.cdKey if hasattr(ip, 'cdKey') else ip.get("cdKey", "")
                                if (name, key) not in existing_ids:
                                    self.app.profiles.append(ip)
                                    existing_ids.add((name, key))
                                    added = added + 1
                        else:
                            self.app.profiles = imported
                    
                    # Restore Servers
                    if "servers" in selected_data:
                        self.app.servers = selected_data["servers"]
                        # Clean up invalid entries
                        self.app.servers = [
                            s for s in self.app.servers
                            if s.get("ip") and s.get("name") != "Без авто-подключения (Меню)"
                        ]
                    
                    # Restore Hotkeys
                    if "hotkeys" in selected_data:
                        self.app.hotkeys_config = selected_data["hotkeys"]
                        if self.app.hotkeys_config.get("enabled", False):
                            self.app._apply_saved_hotkeys()
                        else:
                            if hasattr(self.app, 'multi_hotkey_manager'):
                                self.app.multi_hotkey_manager.unregister_session_keys()
                        # Refresh UI if the method is available (hotkeys screen was built)
                        if hasattr(self.app, '_refresh_hotkeys_list'):
                            self.app._refresh_hotkeys_list()
                    
                    # Restore Log Monitor
                    if "log_monitor" in selected_data:
                        self.app.log_monitor_state.config = selected_data["log_monitor"]
                    
                    # Restore App Settings
                    if "app_settings" in selected_data:
                        app_settings = selected_data["app_settings"]
                        self.app.theme = app_settings.get("theme", self.app.theme)
                        self.app.use_server_var.set(app_settings.get("auto_connect", False))
                        self.app.doc_path_var.set(app_settings.get("doc_path", self.app.doc_path_var.get()))
                        self.app.exe_path_var.set(app_settings.get("exe_path", self.app.exe_path_var.get()))
                        
                        self.app.exit_x = app_settings.get("exit_coords_x", self.app.exit_x)
                        self.app.exit_y = app_settings.get("exit_coords_y", self.app.exit_y)
                        self.app.confirm_x = app_settings.get("confirm_coords_x", self.app.confirm_x)
                        self.app.confirm_y = app_settings.get("confirm_coords_y", self.app.confirm_y)
                        self.app.exit_speed = app_settings.get("exit_speed", self.app.exit_speed)
                        self.app.esc_count = app_settings.get("esc_count", self.app.esc_count)
                        self.app.clip_margin = app_settings.get("clip_margin", self.app.clip_margin)
                        
                        self.app.server_group = app_settings.get("server_group", self.app.server_group)
                        
                    self.save_data()
                    self.app.profile_manager.refresh_list()
                    messagebox.showinfo("Success", "Backup restored successfully!", parent=parent)
                except Exception as e:
                    self.app.log_error("on_restore", e)
                    messagebox.showerror("Error", f"Failed to apply backup:\n{e}", parent=parent)
            
            SelectiveRestoreDialog(parent, backup_data, on_restore)
            
        except Exception as e:
            self.app.log_error("import_data", e)
            messagebox.showerror("Error", f"Failed to read backup file:\n{e}", parent=parent)
