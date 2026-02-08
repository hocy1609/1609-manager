import os
import json
import sys
import subprocess
import time
import threading
import stat
import shutil
import csv
import tempfile
import atexit
import ctypes
import ctypes.wintypes
import logging
from datetime import datetime
from dataclasses import dataclass, field

import tkinter as tk
from tkinter import messagebox, filedialog

from ui.ui_base import COLORS
from core.storage import SessionManager, SETTINGS_FILE, SESSIONS_FILE
from ui.dialogs import (
    CustomInputDialog,
    RestoreBackupDialog,
)
from utils.win_automation import (
    set_dpi_awareness,
    auto_detect_nwn_path,
    robust_update_settings_tml,
    safe_exit_sequence,
    get_hwnd_from_pid,
    KEYEVENTF_KEYUP,
    load_custom_fonts,
)
from utils.log_monitor import LogMonitor
from core.models import (
    Settings,
    Profile,
    Server,
    LogMonitorConfig,
    HotkeysConfig,
    load_settings,
    save_settings,
)
from core.theme_manager import ThemeManager
from core.log_monitor_manager import LogMonitorManager
from core.keybind_manager import KeybindManager, MultiHotkeyManager, send_numpad_sequence_to_nwn
from core.craft_manager import CraftManager
from core.profile_manager import ProfileManager
from core.settings_manager import SettingsManager
from core.ui_state import UIStateManager
from core.server_manager import ServerManager
from core.error_handler import ErrorHandler
from core.tray_manager import TrayManager
from core.constants import (
    PROCESS_MONITOR_INTERVAL_MS,
    STARTUP_PATH_CHECK_DELAY_MS,
    APPWINDOW_SETUP_DELAY_MS,
    SAVE_DEBOUNCE_DELAY_MS,
    LOG_FILENAME,
    MAX_BACKUPS_PER_FILE,
    GAME_EXIT_TIMEOUT_SECONDS,
    GAME_EXIT_CHECK_INTERVAL,
)


def get_app_dir() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def get_default_log_path(data_dir: str) -> str:
    return os.path.join(data_dir, LOG_FILENAME)


def configure_logging(log_path: str) -> None:
    try:
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
    except Exception:
        logging.exception("Failed to ensure log directory exists")
    logging.basicConfig(
        filename=log_path,
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    # Configure centralized error handler
    ErrorHandler.configure(log_path)


set_dpi_awareness()
load_custom_fonts()  # Load Mona Sans fonts


@dataclass
class CraftState:
    running: bool = False
    vars: dict[str, tk.Variable] = field(default_factory=dict)
    recorded_macro: list = field(default_factory=list)
    log_path: tk.StringVar | None = None
    log_position: int = 0
    real_count: int = 0
    macro_playback_stop: bool = False
    potions_count: int = 0
    thread: threading.Thread | None = None


@dataclass
class LogMonitorState:
    config: dict = field(default_factory=dict)
    monitor: LogMonitor | None = None
    slayer_monitor: LogMonitor | None = None
    slayer_hit_count: int = 0
    enabled_var: tk.BooleanVar | None = None
    log_path_var: tk.StringVar | None = None
    webhooks_text: tk.Text | None = None
    keywords_text: tk.Text | None = None
    open_wounds_enabled_var: tk.BooleanVar | None = None
    open_wounds_key_var: tk.StringVar | None = None
    # Keybind state for numpad sequence
    keybind_enabled_var: tk.BooleanVar | None = None
    keybind_key_var: tk.StringVar | None = None


class NWNManagerApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.ui_state_manager = UIStateManager(self)
        self.ui_state_manager.configure_root_window()
        self.ui_state_manager.initialize_state()

        self.app_dir = get_app_dir()

        # Set window icon if available
        try:
            # Check bundle dir first (PyInstaller), then app dir
            base_path = getattr(sys, "_MEIPASS", self.app_dir)
            icon_path = os.path.join(base_path, "logo.ico")
            if not os.path.exists(icon_path):
                icon_path = os.path.join(self.app_dir, "logo.ico")
            
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
        except Exception:
            pass

        # Choose a writable data directory for settings/sessions/logs.
        # Use a dedicated subfolder "1609 settings" to keep things organized.
        self.data_dir = os.path.join(self.app_dir, "1609 settings")
        self.backups_dir = os.path.join(self.data_dir, "backups")
        try:
            os.makedirs(self.data_dir, exist_ok=True)
            os.makedirs(self.backups_dir, exist_ok=True)
        except Exception:
            try:
                messagebox.showwarning(
                    "Permissions",
                    f"Cannot write to settings directory:\n{self.data_dir}\n\nPlease move the program to a writable folder or run it with elevated permissions.",
                    parent=self.root,
                )
            except Exception:
                logging.exception("Unhandled exception")

        self.settings_path = os.path.join(self.data_dir, SETTINGS_FILE)
        self.sessions_path = os.path.join(self.data_dir, SESSIONS_FILE)
        self.log_path = get_default_log_path(self.data_dir)

        # Migration: move existing files from old location (app_dir) to new location (data_dir)
        self._migrate_old_settings()

        # If there's a default settings file bundled (ONEDIR: next to exe; ONEFILE: inside _MEIPASS),
        # copy it to the writable data dir on first run for sensible defaults.
        try:
            bundle_dir = getattr(sys, "_MEIPASS", self.app_dir)
            default_settings_src = os.path.join(bundle_dir, "nwn_settings.example.json")
            if os.path.exists(default_settings_src) and not os.path.exists(self.settings_path):
                try:
                    shutil.copyfile(default_settings_src, self.settings_path)
                except Exception:
                    logging.exception("Unhandled exception")
        except Exception:
            logging.exception("Unhandled exception")

        # Temporary working directory: keep it in system temp and remove on exit.
        try:
            self.temp_dir = os.path.join(tempfile.gettempdir(), "nwn_manager_temp")
            os.makedirs(self.temp_dir, exist_ok=True)
        except Exception:
            self.temp_dir = None

        def _cleanup_temp():
            try:
                if self.temp_dir and os.path.exists(self.temp_dir):
                    shutil.rmtree(self.temp_dir, ignore_errors=True)
            except Exception:
                logging.exception("Unhandled exception")

        # Register cleanup on normal interpreter exit
        try:
            atexit.register(_cleanup_temp)
        except Exception:
            logging.exception("Unhandled exception")

        # Initialize sessions with app reference (sessions stored in settings)
        self.sessions = SessionManager(self)
        self._settings_sessions = {}  # Will be populated by load_data

        self.log_monitor_manager = LogMonitorManager(self)
        self.log_monitor_manager.initialize_state()

        self.keybind_manager = KeybindManager(self)
        self.multi_hotkey_manager = MultiHotkeyManager(self)

        self.craft_manager = CraftManager(self)
        self.craft_manager.initialize_state()

        self.profile_manager = ProfileManager(self)
        self.settings_manager = SettingsManager(self)
        self.server_manager = ServerManager(self)
        
        # System tray manager
        self.tray_manager = TrayManager(self)
        self.tray_manager.setup(
            on_show=lambda icon, item: self.root.after(0, self.tray_manager.restore_from_tray),
            on_quit=lambda icon, item: self.root.after(0, self.force_quit)
        )

        self.setup_styles()
        self.load_data()
        
        # Initialize sessions from loaded settings
        self.sessions.init_from_settings(self._settings_sessions)

        # Initialize theme manager after load_data (needs self.theme)
        self.theme_manager = ThemeManager(self)

        self.create_ui()
        self.refresh_list()
        
        # Auto-select first profile if none selected and list not empty
        def _initial_select():
            try:
                if not self.current_profile and self.view_map:
                    # Check if view_map[0] is a profile (skip group headers if any)
                    first_idx = 0
                    for idx, item in enumerate(self.view_map):
                        if item.get("type") == "profile":
                            first_idx = idx
                            break
                    
                    self.lb.focus_set()
                    self.lb.selection_set(first_idx)
                    self.lb.activate(first_idx)
                    self.on_select(None)
            except Exception:
                pass
        
        self.root.after(200, _initial_select)

        self.sessions.cleanup_dead()
        # Try to detect a game already started outside the manager
        try:
            self.detect_existing_session()
        except Exception:
            logging.exception("Unhandled exception")
        # Start slayer monitor if slayer is enabled and game is running
        try:
            if getattr(self.sessions, "sessions", None) and self.sessions.sessions:
                self._ensure_slayer_if_enabled()
        except Exception as e:
            self.log_error("start_slayer_if_enabled", e)
        self.monitor_processes()
        self.check_server_status()

        self.root.after(STARTUP_PATH_CHECK_DELAY_MS, self.check_paths_silent)
        self.root.after(APPWINDOW_SETUP_DELAY_MS, self.set_appwindow)
        
        # Auto-register hotkeys if enabled in settings
        self.root.after(500, self._apply_saved_hotkeys)

    @property
    def nav_buttons(self):
        return self.nav_bar_comp.buttons if self.nav_bar_comp else {}

    @property
    def status_bar_labels(self):
        return self.status_bar_comp.labels if self.status_bar_comp else {}

    def apply_theme(self):
        """Reapply current theme across all widgets. Delegates to ThemeManager."""
        if hasattr(self, 'theme_manager'):
            self.theme_manager.apply_theme()
    
    def _rebuild_current_screen(self):
        """Rebuild the current screen with new theme colors. Delegates to ThemeManager."""
        if hasattr(self, 'theme_manager'):
            self.theme_manager._rebuild_current_screen()
    
    def _update_all_nav_buttons(self):
        """Update all navigation buttons. Delegates to ThemeManager."""
        if hasattr(self, 'theme_manager'):
            self.theme_manager._update_all_nav_buttons()
    
    def _update_nav_bar_theme(self):
        """Update navigation bar colors. Delegates to ThemeManager."""
        if hasattr(self, 'theme_manager'):
            self.theme_manager._update_nav_bar_theme()
    
    def _update_sidebar_theme(self):
        """Update sidebar colors. Delegates to ThemeManager."""
        if hasattr(self, 'theme_manager'):
            self.theme_manager._update_sidebar_theme()
    
    def _update_widget_tree_bg(self, widget, bg_color):
        """Update widget tree background. Delegates to ThemeManager."""
        if hasattr(self, 'theme_manager'):
            self.theme_manager._update_widget_tree_bg(widget, bg_color)
    
    def _update_widget_colors_recursive(self, widget):
        """Update widget colors recursively. Delegates to ThemeManager."""
        if hasattr(self, 'theme_manager'):
            self.theme_manager._update_widget_colors_recursive(widget)
    
    def _update_status_bar_theme(self):
        """Update status bar colors. Delegates to ThemeManager."""
        if hasattr(self, 'theme_manager'):
            self.theme_manager._update_status_bar_theme()
    
    def _update_canvas_widgets(self, widget):
        """Update Canvas widgets. Delegates to ThemeManager."""
        if hasattr(self, 'theme_manager'):
            self.theme_manager._update_canvas_widgets(widget)

    # === ЛОГГЕР ОШИБОК ===

    def log_error(self, context: str, exc: Exception) -> None:
        """Пишем ошибку в простой текстовый лог рядом с exe."""
        try:
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(f"[{ts}] {context}: {exc}\n")
        except Exception:
            # Логгер не должен ломать приложение
            logging.exception("Failed to write to error log")

    # === СТИЛИ / ОКНО ===

    def setup_styles(self):
        if hasattr(self, "ui_state_manager"):
            self.ui_state_manager.setup_styles()

    def set_appwindow(self):
        if hasattr(self, "ui_state_manager"):
            self.ui_state_manager.set_appwindow()

    def start_move(self, event):
        if hasattr(self, "ui_state_manager"):
            self.ui_state_manager.start_move(event)

    def do_move(self, event):
        if hasattr(self, "ui_state_manager"):
            self.ui_state_manager.do_move(event)

    def minimize_window(self):
        if hasattr(self, "ui_state_manager"):
            self.ui_state_manager.minimize_window()

    def close_app_window(self):
        # Minimize to tray if enabled
        should_minimize = getattr(self, "minimize_to_tray", True)
        
        # Debug logging for tray issues
        if not hasattr(self, 'tray_manager'):
             self.log_error("close_window", Exception("No tray_manager"))
        elif not self.tray_manager.is_available():
             # Only log if we expect it to be available (minimize is on)
             if should_minimize:
                self.log_error("close_window", Exception("Tray manager not available (Import failed?)"))

        if should_minimize and hasattr(self, 'tray_manager') and self.tray_manager.is_available():
            if self.tray_manager.minimize_to_tray():
                return
        
        # Fallback: actually close
        if hasattr(self, "ui_state_manager"):
            self.ui_state_manager.close_app_window()
    
    def force_quit(self):
        """Force quit the application (from tray menu)."""
        if hasattr(self, 'tray_manager'):
            self.tray_manager.stop()
        if hasattr(self, "ui_state_manager"):
            self.ui_state_manager.close_app_window()

    # === МИГРАЦИЯ И БЭКАПЫ ===

    def _migrate_old_settings(self):
        """Migrate settings files from old location (app_dir) to new location (data_dir/1609 settings)."""
        try:
            old_settings = os.path.join(self.app_dir, SETTINGS_FILE)
            old_sessions = os.path.join(self.app_dir, SESSIONS_FILE)
            old_log = os.path.join(self.app_dir, LOG_FILENAME)
            
            # Migrate settings
            if os.path.exists(old_settings) and not os.path.exists(self.settings_path):
                try:
                    shutil.move(old_settings, self.settings_path)
                    logging.info(f"Migrated {SETTINGS_FILE} to new location")
                except Exception as e:
                    logging.exception(f"Failed to migrate {SETTINGS_FILE}")
            
            # Migrate sessions
            if os.path.exists(old_sessions) and not os.path.exists(self.sessions_path):
                try:
                    shutil.move(old_sessions, self.sessions_path)
                    logging.info(f"Migrated {SESSIONS_FILE} to new location")
                except Exception as e:
                    logging.exception(f"Failed to migrate {SESSIONS_FILE}")
            
            # Migrate log (copy instead of move - log file may be in use)
            if os.path.exists(old_log) and not os.path.exists(self.log_path):
                try:
                    shutil.copy2(old_log, self.log_path)
                    logging.info(f"Copied {LOG_FILENAME} to new location")
                except PermissionError:
                    pass  # Log file in use, skip silently
                except Exception as e:
                    pass  # Non-critical, skip
        except Exception as e:
            logging.exception("Error during settings migration")

    def _backup_settings(self):
        """Create a timestamped backup of nwn_settings.json in the backups folder."""
        try:
            if not os.path.exists(self.settings_path):
                return  # Nothing to backup
            
            # Only backup once per minute to avoid excessive backups
            last_backup_time = getattr(self, '_last_backup_time', 0)
            current_time = time.time()
            if current_time - last_backup_time < 60:
                return  # Skip backup if less than 1 minute since last
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"nwn_settings_{timestamp}.json"
            backup_path = os.path.join(self.backups_dir, backup_name)
            
            shutil.copy2(self.settings_path, backup_path)
            self._last_backup_time = current_time
            
            # Cleanup old backups (keep only last 10)
            self._cleanup_old_backups()
        except Exception as e:
            logging.exception("Failed to create settings backup")

    def _cleanup_old_backups(self, max_backups: int = 10):
        """Remove old backups keeping only the most recent ones."""
        try:
            backup_files = [
                os.path.join(self.backups_dir, f)
                for f in os.listdir(self.backups_dir)
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

    # === ЗАГРУЗКА / СОХРАНЕНИЕ ===

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
            settings = load_settings(self.settings_path, default_docs, default_exe)
        except Exception as e:
            self.log_error("load_settings", e)
            settings = Settings.defaults(default_docs, default_exe)

        # Load server groups
        self.server_group = settings.server_group
        self.server_groups = settings.server_groups
        
        # Set servers from current group
        if self.server_group in self.server_groups:
            self.servers = self.server_groups[self.server_group]
        else:
            self.servers = self.server_groups.get("siala", [])
        
        self.profiles = [p.to_dict() for p in settings.profiles]
        # Fix doc_path if it contains USER placeholder
        doc_path = settings.doc_path
        if "USER" in doc_path or not os.path.exists(doc_path):
            doc_path = default_docs
        self.doc_path_var.set(doc_path)
        self.exe_path_var.set(settings.exe_path if os.path.exists(settings.exe_path) else default_exe)
        self.use_server_var.set(settings.auto_connect)

        self.exit_x = settings.exit_coords_x
        self.exit_y = settings.exit_coords_y
        self.confirm_x = settings.confirm_coords_x
        self.confirm_y = settings.confirm_coords_y
        self.exit_speed = settings.exit_speed
        self.esc_count = settings.esc_count
        self.clip_margin = settings.clip_margin
        self.show_tooltips = settings.show_tooltips
        self.theme = settings.theme
        self._loaded_favorite_potions = settings.favorite_potions
        
        self.minimize_to_tray = settings.minimize_to_tray
        self.run_on_startup = settings.run_on_startup
        self.category_order = list(settings.category_order)  # User-defined category order

        try:
            import ui.ui_base as _uib

            _uib.TOOLTIPS_ENABLED = self.show_tooltips
            try:
                _uib.set_theme(self.theme, root=self.root)
            except Exception:
                _uib.set_theme(self.theme)
        except Exception:
            logging.exception("Unhandled exception")

        try:
            if self.servers:
                srv_names = [s["name"] for s in self.servers]
                last_srv = settings.last_server
                if last_srv in srv_names:
                    self.server_var.set(last_srv)
                else:
                    self.server_var.set(srv_names[0])
        except Exception:
            logging.exception("Unhandled exception")

        # Log monitor path should always use real user's Documents folder
        real_docs_path = os.path.join(os.path.expanduser("~"), "Documents", "Neverwinter Nights")
        lm_default_path = os.path.join(real_docs_path, "logs", "nwclientLog1.txt")
        lm_cfg = settings.log_monitor
        if lm_cfg.log_path == "" or "USER" in lm_cfg.log_path:
            lm_cfg.log_path = lm_default_path
        self.log_monitor_state.config = lm_cfg.to_dict()
        self.log_monitor_state.config.setdefault("open_wounds", {"enabled": False, "key": "F1"})
        self.log_monitor_state.config.setdefault("keybind", {"enabled": False, "key": "F10"})

        # Load hotkeys config from top-level settings
        self.hotkeys_config = settings.hotkeys.to_dict()
        
        # Load sessions from settings
        self._settings_sessions = dict(settings.sessions)
        
        # Load saved CD keys
        self.saved_keys = list(settings.saved_keys)
        
        # Auto-import key from cdkey.ini if no saved keys exist
        if not self.saved_keys:
            cdkey_path = os.path.join(doc_path, "nwncdkey.ini")
            if os.path.exists(cdkey_path):
                try:
                    with open(cdkey_path, "r", encoding="utf-8", errors="ignore") as f:
                        for line in f:
                            if line.strip().startswith("Key1="):
                                key_value = line.strip().split("=", 1)[1].strip()
                                if key_value and len(key_value) > 10:
                                    self.saved_keys.append({"name": "Main Key", "key": key_value})
                                break
                except Exception:
                    pass

        if not os.path.exists(self.settings_path):
            try:
                self.save_data()
            except Exception:
                logging.exception("Unhandled exception")

    def save_data(self):
        try:
            # Create backup of existing settings before saving
            self._backup_settings()
            
            servers = [Server.from_dict(s) if isinstance(s, dict) else s for s in self.servers]
            profiles = [Profile.from_dict(p) if isinstance(p, dict) else p for p in self.profiles]
            lm_cfg = LogMonitorConfig.from_dict(self.log_monitor_state.config or {})
            hotkeys_cfg = HotkeysConfig.from_dict(getattr(self, "hotkeys_config", {}))
            # Get current sessions from SessionManager
            sessions_data = self.sessions.sessions if hasattr(self, 'sessions') else {}
            
            # Update current group's servers before saving
            if hasattr(self, 'server_groups') and hasattr(self, 'server_group'):
                self.server_groups[self.server_group] = self.servers
            
            settings = Settings(
                doc_path=self.doc_path_var.get(),
                exe_path=self.exe_path_var.get(),
                servers=servers,
                profiles=profiles,
                auto_connect=self.use_server_var.get(),
                last_server=self.server_var.get(),
                exit_coords_x=self.exit_x,
                exit_coords_y=self.exit_y,
                confirm_coords_x=self.confirm_x,
                confirm_coords_y=self.confirm_y,
                log_monitor=lm_cfg,
                hotkeys=hotkeys_cfg,
                sessions=sessions_data,
                exit_speed=getattr(self, "exit_speed", 0.1),
                esc_count=getattr(self, "esc_count", 1),
                clip_margin=getattr(self, "clip_margin", 48),
                show_tooltips=getattr(self, "show_tooltips", True),
                theme=getattr(self, "theme", "dark"),
                favorite_potions=list(getattr(self, "favorite_potions", set())),
                server_group=getattr(self, "server_group", "siala"),
                server_groups=getattr(self, "server_groups", {}),
                saved_keys=getattr(self, "saved_keys", []),
                minimize_to_tray=getattr(self, "minimize_to_tray", True),
                run_on_startup=getattr(self, "run_on_startup", False),
                category_order=getattr(self, "category_order", []),
            )
            
            # Sync startup registry (failsafe)
            try:
                from utils.win_automation import set_run_on_startup
                set_run_on_startup(getattr(self, "run_on_startup", False))
            except Exception:
                pass
                
            save_settings(self.settings_path, settings)
        except Exception as e:
            self.log_error("save_data", e)
            print(f"SAVE ERROR: {e}")

        # DEBUG: Print what we just saved
        try:
            print(f"DEBUG: Saved keys count: {len(getattr(self, 'saved_keys', []))}")
            if getattr(self, 'saved_keys', []):
                print(f"DEBUG: Saved keys content: {self.saved_keys}")
            
            hk = getattr(self, 'hotkeys_config', {})
            print(f"DEBUG: Hotkeys config: {hk}")
        except Exception as e:
            print(f"DEBUG ERROR: {e}")

    def schedule_save(self, delay_ms: int = SAVE_DEBOUNCE_DELAY_MS):
        """Debounced save: schedule `save_data` after `delay_ms` milliseconds, cancelling previous schedule.

        Default delay chosen as a conservative slower debounce to reduce writes
        while still keeping settings reasonably responsive.
        """
        try:
            if hasattr(self, "_save_after_id") and self._save_after_id:
                try:
                    self.root.after_cancel(self._save_after_id)
                except Exception:
                    logging.exception("Unhandled exception")
            self._save_after_id = self.root.after(delay_ms, lambda: (setattr(self, '_save_after_id', None), self.save_data()))
        except Exception as e:
            self.log_error("schedule_save", e)

    def export_data(self, parent=None):
        parent = parent or self.root
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
            "profiles": self.profiles,
            "servers": self.servers,
            "hotkeys": getattr(self, "hotkeys_config", {}),
            "log_monitor": self.log_monitor_state.config if hasattr(self, 'log_monitor_state') else {},
            "app_settings": {
                "theme": getattr(self, "theme", "dark"),
                "auto_connect": self.use_server_var.get(),
                "doc_path": self.doc_path_var.get(),
                "exe_path": self.exe_path_var.get(),
                "exit_coords_x": getattr(self, "exit_x", 0),
                "exit_coords_y": getattr(self, "exit_y", 0),
                "confirm_coords_x": getattr(self, "confirm_x", 0),
                "confirm_coords_y": getattr(self, "confirm_y", 0),
                "exit_speed": getattr(self, "exit_speed", 0.1),
                "esc_count": getattr(self, "esc_count", 1),
                "clip_margin": getattr(self, "clip_margin", 48),
                "favorite_potions": list(getattr(self, "favorite_potions", set())),
                "server_group": getattr(self, "server_group", "siala"),
                "saved_keys": getattr(self, "saved_keys", []),
                "minimize_to_tray": getattr(self, "minimize_to_tray", True),
                "run_on_startup": getattr(self, "run_on_startup", False),
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
            self.log_error("export_data", e)
            messagebox.showerror("Export Error", str(e), parent=parent)

    def import_data(self, parent=None):
        """Import backup data with selective restore dialog."""
        from ui.dialogs import SelectiveRestoreDialog
        
        parent = parent or self.root

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
                    # Restore Profiles
                    if "profiles" in selected_data:
                        self.profiles = selected_data["profiles"]
                    
                    # Restore Servers
                    if "servers" in selected_data:
                        self.servers = selected_data["servers"]
                        # Clean up invalid entries
                        self.servers = [
                            s for s in self.servers
                            if s.get("ip") and s.get("name") != "Без авто-подключения (Меню)"
                        ]
                    
                    # Restore Hotkeys
                    if "hotkeys" in selected_data:
                        self.hotkeys_config = selected_data["hotkeys"]
                        if self.hotkeys_config.get("enabled", False):
                            self._apply_saved_hotkeys()
                        else:
                            if hasattr(self, 'multi_hotkey_manager'):
                                self.multi_hotkey_manager.unregister_all()
                    
                    # Restore Log Monitor
                    if "log_monitor" in selected_data:
                        self.log_monitor_state.config = selected_data["log_monitor"]
                    
                    # Restore App Settings
                    if "app_settings" in selected_data:
                        app_settings = selected_data["app_settings"]
                        self.theme = app_settings.get("theme", self.theme)
                        self.use_server_var.set(app_settings.get("auto_connect", False))
                        self.doc_path_var.set(app_settings.get("doc_path", self.doc_path_var.get()))
                        self.exe_path_var.set(app_settings.get("exe_path", self.exe_path_var.get()))
                        
                        self.exit_x = app_settings.get("exit_coords_x", self.exit_x)
                        self.exit_y = app_settings.get("exit_coords_y", self.exit_y)
                        self.confirm_x = app_settings.get("confirm_coords_x", self.confirm_x)
                        self.confirm_y = app_settings.get("confirm_coords_y", self.confirm_y)
                        self.exit_speed = app_settings.get("exit_speed", self.exit_speed)
                        self.esc_count = app_settings.get("esc_count", self.esc_count)
                        self.clip_margin = app_settings.get("clip_margin", self.clip_margin)
                        
                        self._loaded_favorite_potions = set(app_settings.get("favorite_potions", []))
                        self.favorite_potions = self._loaded_favorite_potions
                        self.server_group = app_settings.get("server_group", self.server_group)
                        
                        self.minimize_to_tray = app_settings.get("minimize_to_tray", getattr(self, "minimize_to_tray", True))
                        self.run_on_startup = app_settings.get("run_on_startup", getattr(self, "run_on_startup", False))
                        
                        # Apply Theme immediately
                        if hasattr(self, 'theme_manager'):
                            self.theme_manager.apply_theme()
                    
                    # Restore CD Keys
                    if "saved_keys" in selected_data:
                        self.saved_keys = selected_data["saved_keys"]
                    
                    self.save_data()
                    self.refresh_list()
                    self.refresh_server_list()
                    
                    messagebox.showinfo(
                        "Restore Complete",
                        "Selected data has been restored successfully!",
                        parent=parent,
                    )
                except Exception as e:
                    self.log_error("import_data.on_restore", e)
                    raise
            
            # Open selective restore dialog
            SelectiveRestoreDialog(parent, backup_data, on_restore)
            
        except Exception as e:
            self.log_error("import_data", e)
            messagebox.showerror(
                "Import Error",
                f"Failed to load file: {e}",
                parent=parent,
            )
    # === ИМПОРТ ИЗ xNwN.ini ===
    def import_xnwn_ini(self):
        """Импортирует аккаунты, ключи и сервера из конфиг-файла xNwN.ini.

        Формат ожидается как набор секций:
        [AccountN] account=NAME cdkey=KEY
        [IPN] ip=HOST:PORT description=DESC
        [Path] NwnExePath=... (папка или файл)
        Не создаёт дубликаты: проверяет совпадение playerName+cdKey для профилей и ip для серверов.
        """
        try:
            ini_path = filedialog.askopenfilename(
                title="Select xNwN.ini",
                filetypes=[("INI Files", "*.ini"), ("All Files", "*")],
                parent=self.root,
            )
            if not ini_path:
                return
            try:
                with open(ini_path, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
            except Exception as e:
                messagebox.showerror("Read Error", f"Cannot read file: {e}", parent=self.root)
                return

            section = None
            data_map: dict[str, dict[str, str]] = {}
            for raw in lines:
                line = raw.strip()
                if not line or line.startswith('#'):
                    continue
                if line.startswith('[') and line.endswith(']'):
                    section = line[1:-1].strip()
                    data_map.setdefault(section, {})
                    continue
                if '=' in line and section:
                    k, v = line.split('=', 1)
                    data_map[section][k.strip()] = v.strip()

            added_profiles = 0
            added_servers = 0

            # Existing sets for duplicate checks
            existing_profile_keys = {(p.get('playerName'), p.get('cdKey')) for p in self.profiles}
            existing_server_ips = {s.get('ip') for s in self.servers}

            for sec, kv in data_map.items():
                lsec = sec.lower()
                if lsec.startswith('account'):
                    name = kv.get('account', '').strip()
                    cdkey = kv.get('cdkey', '').strip()
                    if not name or not cdkey:
                        continue
                    key_tuple = (name, cdkey)
                    if key_tuple in existing_profile_keys:
                        continue
                    profile = {
                        'name': name,
                        'playerName': name,
                        'cdKey': cdkey,
                        'category': 'General',
                        'launchArgs': '',
                    }
                    self.profiles.append(profile)
                    existing_profile_keys.add(key_tuple)
                    added_profiles += 1
                elif lsec.startswith('ip'):
                    ip = kv.get('ip', '').strip()
                    desc = kv.get('description', '').strip() or ip
                    if not ip or ip in existing_server_ips:
                        continue
                    server_name = f"{desc} ({ip})" if desc not in ip else f"{desc}"
                    self.servers.append({'name': server_name, 'ip': ip})
                    existing_server_ips.add(ip)
                    added_servers += 1
                elif lsec == 'path':
                    raw_path = kv.get('NwnExePath', '').strip()
                    if raw_path:
                        # Accept both direct exe path and directory ending with separator
                        if os.path.isdir(raw_path):
                            exe_candidate = os.path.join(raw_path, 'nwmain.exe')
                        else:
                            exe_candidate = raw_path
                        if exe_candidate.lower().endswith('nwmain.exe') and os.path.exists(exe_candidate):
                            try:
                                self.exe_path_var.set(exe_candidate)
                            except Exception:
                                logging.exception("Unhandled exception")

            # If no server selected yet and servers present, select first
            if not self.server_var.get() and self.servers:
                try:
                    self.server_var.set(self.servers[0]['name'])
                except Exception:
                    logging.exception("Unhandled exception")

            self.save_data()
            self.refresh_list()
            self.refresh_server_list()

            try:
                messagebox.showinfo(
                    "xNwN Import",
                    f"Imported profiles: {added_profiles}\nImported servers: {added_servers}",
                    parent=self.root,
                )
            except Exception:
                logging.exception("Unhandled exception")
        except Exception as e:
            self.log_error('import_xnwn_ini', e)
            try:
                messagebox.showerror("Import Error", str(e), parent=self.root)
            except Exception:
                logging.exception("Unhandled exception")

    def export_accounts_txt(self):
        """Export account profiles to a simple accounts.txt file for easy sharing."""
        try:
            accounts_path = os.path.join(self.data_dir, "accounts.txt")
            
            with open(accounts_path, "w", encoding="utf-8") as f:
                f.write("# 1609 Manager Accounts Export\n")
                f.write("# Format: PlayerName|CDKey\n")
                f.write("# ---\n")
                
                for profile in self.profiles:
                    name = profile.get("playerName", "")
                    cdkey = profile.get("cdKey", "")
                    if name and cdkey:
                        f.write(f"{name}|{cdkey}\n")
            
            messagebox.showinfo(
                "Export Complete",
                f"Accounts exported to:\n{accounts_path}\n\nTotal: {len(self.profiles)} profiles",
                parent=self.root,
            )
        except Exception as e:
            self.log_error("export_accounts_txt", e)
            messagebox.showerror("Export Error", str(e), parent=self.root)

    def import_accounts_txt(self):
        """Import accounts from accounts.txt file."""
        try:
            accounts_path = os.path.join(self.data_dir, "accounts.txt")
            
            if not os.path.exists(accounts_path):
                # Ask user to select file
                accounts_path = filedialog.askopenfilename(
                    title="Select accounts.txt",
                    filetypes=[("Text Files", "*.txt"), ("All Files", "*")],
                    initialdir=self.data_dir,
                    parent=self.root,
                )
                if not accounts_path:
                    return
            
            with open(accounts_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            
            existing_keys = {(p.get("playerName"), p.get("cdKey")) for p in self.profiles}
            added = 0
            
            for line in lines:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                
                parts = line.split("|", 1)
                if len(parts) != 2:
                    continue
                
                name, cdkey = parts[0].strip(), parts[1].strip()
                if not name or not cdkey:
                    continue
                
                key_tuple = (name, cdkey)
                if key_tuple in existing_keys:
                    continue
                
                profile = {
                    "name": name,
                    "playerName": name,
                    "cdKey": cdkey,
                    "category": "Imported",
                    "launchArgs": "",
                }
                self.profiles.append(profile)
                existing_keys.add(key_tuple)
                added += 1
            
            if added > 0:
                self.save_data()
                self.refresh_list()
            
            messagebox.showinfo(
                "Import Complete",
                f"Imported {added} new accounts",
                parent=self.root,
            )
        except Exception as e:
            self.log_error("import_accounts_txt", e)
            messagebox.showerror("Import Error", str(e), parent=self.root)

    def open_settings(self):
        """Delegate to SettingsManager."""
        if hasattr(self, 'settings_manager'):
            self.settings_manager.open_settings()

    # Old backup_files method removed - now using _backup_settings() which only
    # backs up program settings (nwn_settings.json), not game files

    def open_restore_dialog(self):
        """Open dialog to restore settings from backup."""
        try:
            # Use the backups directory in data_dir (1609 settings/backups/)
            if not os.path.exists(self.backups_dir):
                os.makedirs(self.backups_dir, exist_ok=True)
            
            RestoreBackupDialog(
                self.root,
                self.backups_dir,
                self.settings_path,
                on_export=self.export_data,
                on_import=self.import_data,
            )
        except Exception as e:
            self.log_error("open_restore_dialog", e)
            messagebox.showerror(
                "Error", f"Cannot access backups: {e}", parent=self.root
            )

    # === ЛОГ‑МОНИТОР ===

    def on_log_match(self, text: str):
        """Callback when LogMonitor finds a keyword. Delegates to LogMonitorManager."""
        if hasattr(self, 'log_monitor_manager'):
            self.log_monitor_manager.on_log_match(text)

    def on_log_line(self, line: str):
        """Callback for every new line in log. Delegates to LogMonitorManager."""
        if hasattr(self, 'log_monitor_manager'):
            self.log_monitor_manager.on_log_line(line)

    def ensure_log_monitor(self):
        """Create or update LogMonitor. Delegates to LogMonitorManager."""
        if hasattr(self, 'log_monitor_manager'):
            self.log_monitor_manager.ensure_log_monitor()

    def start_log_monitor(self):
        """Start log monitor. Delegates to LogMonitorManager."""
        if hasattr(self, 'log_monitor_manager'):
            self.log_monitor_manager.start_log_monitor()

    def stop_log_monitor(self):
        """Stop log monitor. Delegates to LogMonitorManager."""
        if hasattr(self, 'log_monitor_manager'):
            self.log_monitor_manager.stop_log_monitor()

    def _ensure_slayer_if_enabled(self):
        """Ensure slayer monitor. Delegates to LogMonitorManager."""
        if hasattr(self, 'log_monitor_manager'):
            self.log_monitor_manager._ensure_slayer_if_enabled()

    def _start_slayer_monitor(self):
        """Start slayer monitor. Delegates to LogMonitorManager."""
        if hasattr(self, 'log_monitor_manager'):
            self.log_monitor_manager._start_slayer_monitor()

    def _stop_slayer_monitor(self):
        """Stop slayer monitor. Delegates to LogMonitorManager."""
        if hasattr(self, 'log_monitor_manager'):
            self.log_monitor_manager._stop_slayer_monitor()

    def update_log_monitor_status_label(self):
        """Update status label. Delegates to LogMonitorManager."""
        if hasattr(self, 'log_monitor_manager'):
            self.log_monitor_manager.update_log_monitor_status_label()

    def _handle_open_wounds_detection(self, line: str):
        """Handle Open Wounds detection. Delegates to LogMonitorManager."""
        if hasattr(self, 'log_monitor_manager'):
            self.log_monitor_manager._handle_open_wounds_detection(line)
    
    def _update_slayer_hit_counter_ui(self):
        """Update slayer hit counter. Delegates to LogMonitorManager."""
        if hasattr(self, 'log_monitor_manager'):
            self.log_monitor_manager._update_slayer_hit_counter_ui()

    def _send_function_key_to_active_session(self, key_name: str):
        """Send function key. Delegates to LogMonitorManager."""
        if hasattr(self, 'log_monitor_manager'):
            self.log_monitor_manager._send_function_key_to_active_session(key_name)

    def _send_key_via_sendinput(self, vk: int, fkey_num: int):
        """Send key via SendInput. Delegates to LogMonitorManager."""
        if hasattr(self, 'log_monitor_manager'):
            self.log_monitor_manager._send_key_via_sendinput(vk, fkey_num)

    def _test_open_wounds_key(self):
        """Test Open Wounds key."""
        try:
            key_var = self.log_monitor_state.open_wounds_key_var
            if not key_var:
                return
            key = str(key_var.get() or "F1")
            self._send_function_key_to_active_session(key)
            messagebox.showinfo("Test", f"Sent {key} to active session (if any).", parent=self.root)
        except Exception as e:
            self.log_error("test_open_wounds", e)

    def _apply_saved_hotkeys(self):
        """Auto-register hotkeys from saved config on app startup."""
        try:
            print("[DEBUG] _apply_saved_hotkeys called")
            hotkeys_cfg = getattr(self, 'hotkeys_config', {})
            print(f"[DEBUG] hotkeys_config: {hotkeys_cfg}")
            
            if not hotkeys_cfg.get("enabled", False):
                print("[DEBUG] Hotkeys not enabled, skipping")
                return
            
            binds = hotkeys_cfg.get("binds", [])
            print(f"[DEBUG] Binds count: {len(binds)}")
            if not binds:
                print("[DEBUG] No binds, skipping")
                return
            
            from core.keybind_manager import HotkeyAction
            actions = [HotkeyAction.from_dict(b) for b in binds if b.get("enabled", True)]
            print(f"[DEBUG] Actions to register: {len(actions)}")
            if actions:
                count = self.multi_hotkey_manager.register_hotkeys(actions)
                print(f"[DEBUG] Registered {count} hotkeys")
                logging.info(f"Auto-registered {count} hotkeys on startup")
        except Exception as e:
            print(f"[DEBUG] Error in _apply_saved_hotkeys: {e}")
            self.log_error("_apply_saved_hotkeys", e)

    def _on_sessions_started(self):
        """Called when game sessions appear (went from 0 to >0).
        Starts log monitor if it was enabled (waiting for game).
        Also applies saved hotkeys.
        """
        try:
            # Start log monitor if it was enabled (waiting for game)
            if hasattr(self, 'log_monitor_manager'):
                if self.log_monitor_state.config.get("enabled", False):
                    print("[Auto] Starting log monitor (was waiting for game)...")
                    self.log_monitor_manager.start_log_monitor()
            
            # Apply saved hotkeys
            print("[Auto] Applying saved hotkeys...")
            self._apply_saved_hotkeys()
            
        except Exception as e:
            self.log_error("_on_sessions_started", e)

    def _on_sessions_ended(self):
        """Called when all game sessions end (went from >0 to 0).
        Stops log monitor (but keeps it enabled for next session).
        Unregisters hotkeys.
        """
        try:
            # Stop log monitor thread but keep enabled config (will wait for next game)
            if hasattr(self, 'log_monitor_manager'):
                if self.log_monitor_state.monitor and self.log_monitor_state.monitor.is_running():
                    print("[Auto] Stopping log monitor (waiting for next game)...")
                    self.log_monitor_manager.stop_log_monitor()
                # Keep config enabled - just update UI to show "waiting" status
                if self.log_monitor_state.config.get("enabled", False):
                    self.log_monitor_manager.update_log_monitor_status_label(waiting=True)
            
            # Unregister hotkeys
            print("[Auto] Unregistering hotkeys...")
            if hasattr(self, 'multi_hotkey_manager'):
                self.multi_hotkey_manager.unregister_all()
            
        except Exception as e:
            self.log_error("_on_sessions_ended", e)

    def toggle_log_monitor_enabled(self):
        """Toggle log monitor. Delegates to LogMonitorManager."""
        if hasattr(self, 'log_monitor_manager'):
            self.log_monitor_manager.toggle_log_monitor_enabled()

    def open_log_monitor_dialog(self):
        """Open log monitor dialog. Delegates to LogMonitorManager."""
        if hasattr(self, 'log_monitor_manager'):
            self.log_monitor_manager.open_log_monitor_dialog()

    # === СЕРВЕРЫ / ПИНГ ===

    def _on_server_selected(self):
        """Called when user selects a server from combobox - save to current profile."""
        if hasattr(self, "server_manager"):
            self.server_manager.on_server_selected()

    def check_server_status(self):
        if hasattr(self, "server_manager"):
            self.server_manager.check_server_status()

    # === UI ===

    def create_ui(self):
        """Build main UI layout."""
        if hasattr(self, "ui_state_manager"):
            self.ui_state_manager.create_ui()
    
        def _update_status_bar_loop(self):
    
            """Periodically update status bar information."""
    
            if hasattr(self, "ui_state_manager"):
    
                self.ui_state_manager._update_status_bar_loop()
    
        
    
        def _update_status_bar(self):
    
            """Update all status bar labels."""
    
            if hasattr(self, "ui_state_manager"):
    
                self.ui_state_manager._update_status_bar()
    
    
    
    def _update_nav_indicators(self):
        """Update navigation button indicators."""
        if hasattr(self, "ui_state_manager"):
            self.ui_state_manager._update_nav_indicators()
    
    def _update_nav_btn_style(self, btn, screen_name):
        """Update button style based on whether it's the active screen."""
        if hasattr(self, "ui_state_manager"):
            self.ui_state_manager._update_nav_btn_style(btn, screen_name)
    
    def show_screen(self, screen_name):
        """Switch to specified screen."""
        if hasattr(self, "ui_state_manager"):
            self.ui_state_manager.show_screen(screen_name)
    
    def create_home_screen(self):
        """Original main UI as home screen (delegated)."""
        if hasattr(self, "ui_state_manager"):
            return self.ui_state_manager.create_home_screen()
        return None

    # === Adaptive Layout Helpers ===
    def on_root_resize(self, event):
        """Listen to root size changes and switch layout mode when crossing threshold."""
        if hasattr(self, "ui_state_manager"):
            self.ui_state_manager.on_root_resize(event)

    def apply_layout_mode(self, mode: str):
        """Adaptive outer spacing only (simplified)."""
        if hasattr(self, "ui_state_manager"):
            self.ui_state_manager.apply_layout_mode(mode)

    def update_spacing(self, mode: str):
        """Scale paddings smoothly based on window width and mode."""
        if hasattr(self, "ui_state_manager"):
            self.ui_state_manager.update_spacing(mode)

    def create_craft_screen(self):
        """Craft screen with integrated craft UI - delegated."""
        if hasattr(self, "ui_state_manager"):
            return self.ui_state_manager.create_craft_screen()
        return None
    
    def _craft_row(self, parent, row, label, var):
        """Create a settings row in grid. Delegates to CraftManager."""
        if hasattr(self, 'craft_manager'):
            self.craft_manager._craft_row(parent, row, label, var)
    
    def _populate_potion_list(self):
        """Populate the potion list. Delegates to CraftManager."""
        if hasattr(self, 'craft_manager'):
            self.craft_manager._populate_potion_list()
    
    def _toggle_favorite(self, potion_name):
        """Toggle favorite status. Delegates to CraftManager."""
        if hasattr(self, 'craft_manager'):
            self.craft_manager._toggle_favorite(potion_name)
    
    def _select_potion(self, potion_name):
        """Select a potion. Delegates to CraftManager."""
        if hasattr(self, 'craft_manager'):
            self.craft_manager._select_potion(potion_name)
    
    def _on_potion_selected(self, event=None):
        """Handle potion selection. Delegates to CraftManager."""
        if hasattr(self, 'craft_manager'):
            self.craft_manager._on_potion_selected(event)
    
    def craft_start(self):
        """Start crafting. Delegates to CraftManager."""
        if hasattr(self, 'craft_manager'):
            self.craft_manager.craft_start()
    
    def craft_stop(self):
        """Stop crafting. Delegates to CraftManager."""
        if hasattr(self, 'craft_manager'):
            self.craft_manager.craft_stop()
    
    def _craft_loop(self):
        """Main craft loop. Delegates to CraftManager."""
        if hasattr(self, 'craft_manager'):
            self.craft_manager._craft_loop()
    
    def _craft_sleep(self, seconds):
        """Sleep with interrupt. Delegates to CraftManager."""
        if hasattr(self, 'craft_manager'):
            return self.craft_manager._craft_sleep(seconds)
        return False
    
    def _craft_reset_ui(self):
        """Reset craft UI. Delegates to CraftManager."""
        if hasattr(self, 'craft_manager'):
            self.craft_manager._craft_reset_ui()
    
    def _check_craft_log(self, log_path):
        """Check craft log. Delegates to CraftManager."""
        if hasattr(self, 'craft_manager'):
            return self.craft_manager._check_craft_log(log_path)
        return 0
    
    def _browse_craft_log(self):
        """Browse for log file. Delegates to CraftManager."""
        if hasattr(self, 'craft_manager'):
            self.craft_manager._browse_craft_log()
    
    def _open_craft_settings(self):
        """Open craft settings. Delegates to CraftManager."""
        if hasattr(self, 'craft_manager'):
            self.craft_manager._open_craft_settings()

    def craft_start_recording(self):
        """Start macro recording. Delegates to CraftManager."""
        if hasattr(self, 'craft_manager'):
            self.craft_manager.craft_start_recording()
    
    def craft_clear_macro(self):
        """Clear recorded macro. Delegates to CraftManager."""
        if hasattr(self, 'craft_manager'):
            self.craft_manager.craft_clear_macro()
    
    def craft_save_macro(self):
        """Save macro. Delegates to CraftManager."""
        if hasattr(self, 'craft_manager'):
            self.craft_manager.craft_save_macro()
    
    def craft_load_selected_macro(self, event=None):
        """Load selected macro. Delegates to CraftManager."""
        if hasattr(self, 'craft_manager'):
            self.craft_manager.craft_load_selected_macro(event)
    
    def craft_delete_macro(self):
        """Delete selected macro. Delegates to CraftManager."""
        if hasattr(self, 'craft_manager'):
            self.craft_manager.craft_delete_macro()
    
    def _refresh_macro_list(self):
        """Refresh macro list. Delegates to CraftManager."""
        if hasattr(self, 'craft_manager'):
            self.craft_manager._refresh_macro_list()
    
    def craft_drag_potions(self):
        """Play drag macro. Delegates to CraftManager."""
        if hasattr(self, 'craft_manager'):
            self.craft_manager.craft_drag_potions()
    
    def _play_macro_interruptible(self, events, speed_multiplier, target_hwnd):
        """Play macro with interrupt. Delegates to CraftManager."""
        if hasattr(self, 'craft_manager'):
            self.craft_manager._play_macro_interruptible(events, speed_multiplier, target_hwnd)

    def create_settings_screen(self):
        """Settings screen - delegated."""
        if hasattr(self, "ui_state_manager"):
            return self.ui_state_manager.create_settings_screen()
        return None
    
    def _browse_doc_path(self):
        path = filedialog.askdirectory(title="Select Documents Folder")
        if path:
            self.doc_path_var.set(path)
    
    def _browse_exe_path(self):
        path = filedialog.askopenfilename(title="Select NWN Executable", filetypes=[("Executable", "*.exe")])
        if path:
            self.exe_path_var.set(path)
    
    def _save_settings_from_screen(self):
        """Save settings from embedded settings screen"""
        try:
            self.exit_x = int(self.settings_exit_x.get())
            self.exit_y = int(self.settings_exit_y.get())
            self.confirm_x = int(self.settings_confirm_x.get())
            self.confirm_y = int(self.settings_confirm_y.get())
            self.exit_speed = float(self.settings_exit_speed.get())
            self.esc_count = int(self.settings_esc_count.get())
            self.clip_margin = int(self.settings_clip_margin.get())
            
            # UI Settings
            self.show_tooltips = bool(self.settings_show_tooltips.get())
            new_theme = self.settings_theme.get()
            theme_changed = (new_theme != self.theme)
            self.theme = new_theme
            
            # Apply tooltips setting
            try:
                import ui.ui_base as _uib
                _uib.TOOLTIPS_ENABLED = self.show_tooltips
                _uib.set_tooltips_enabled(self.show_tooltips)
            except Exception:
                pass
            
            # Apply theme if changed
            if theme_changed:
                try:
                    import ui.ui_base as _uib
                    _uib.set_theme(self.theme, root=self.root)
                except Exception:
                    pass
            
            self.save_data()
            messagebox.showinfo("Success", "Settings saved!")
            
            # Rebuild UI if theme changed
            if theme_changed:
                try:
                    self.apply_theme()
                except Exception as e:
                    self.log_error("apply_theme_in_settings", e)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save: {e}")
    
    def create_log_monitor_screen(self):
        """Log monitor screen - delegated."""
        if hasattr(self, "ui_state_manager"):
            return self.ui_state_manager.create_log_monitor_screen()
        return None

    def _on_log_monitor_toggle(self):
        """Handle toggle switch change - auto apply."""
        if hasattr(self, "log_monitor_manager"):
            self.log_monitor_manager.on_log_monitor_toggle()

    def _update_slayer_ui_state(self):
        """Update slayer (Open Wounds) UI elements based on slayer state."""
        if hasattr(self, "log_monitor_manager"):
            self.log_monitor_manager.update_slayer_ui_state()

    def _browse_log_path(self):
        if hasattr(self, "log_monitor_manager"):
            self.log_monitor_manager.browse_log_path()

    def _save_log_monitor_settings(self):
        """Save log monitor settings."""
        if hasattr(self, "log_monitor_manager"):
            self.log_monitor_manager.save_log_monitor_settings()

    def create_help_screen(self):
        """Help screen - delegated."""
        if hasattr(self, "ui_state_manager"):
            return self.ui_state_manager.create_help_screen()
        return None

    # === СЕРВЕРЫ: CRUD ===

    def add_server(self):
        if hasattr(self, "server_manager"):
            self.server_manager.add_server()

    def remove_server(self):
        if hasattr(self, "server_manager"):
            self.server_manager.remove_server()

    def refresh_server_list(self):
        if hasattr(self, "server_manager"):
            self.server_manager.refresh_server_list()

    # === СПИСОК ПРОФИЛЕЙ / DND ===

    def on_right_click(self, event):
        idx = self.lb.nearest(event.y)
        if idx < 0 or idx >= len(self.view_map):
            return

        self.lb.selection_clear(0, tk.END)
        self.lb.selection_set(idx)
        self.on_select(None)

        item = self.view_map[idx]
        if item["type"] == "header":
            self.show_header_menu(event, item["data"])
        else:
            self.show_profile_menu(event)

    def show_header_menu(self, event, category_name: str):
        menu = tk.Menu(
            self.root,
            tearoff=0,
            bg=COLORS["bg_panel"],
            fg=COLORS["fg_text"],
            activebackground=COLORS["accent"],
        )
        menu.add_command(
            label=f"Rename '{category_name}'",
            command=lambda: self.rename_category(category_name),
        )
        menu.post(event.x_root, event.y_root)

    def show_profile_menu(self, event):
        menu = tk.Menu(
            self.root,
            tearoff=0,
            bg=COLORS["bg_panel"],
            fg=COLORS["fg_text"],
            activebackground=COLORS["accent"],
        )
        menu.add_command(label="Launch", command=self.launch_game)
        menu.add_separator()
        
        # Crafter toggle
        is_crafter = bool(self.current_profile.get("is_crafter", False)) if self.current_profile else False
        crafter_label = "✓ Crafter" if is_crafter else "Set as Crafter"
        menu.add_command(label=crafter_label, command=self.toggle_crafter)
        
        menu.add_separator()
        menu.add_command(label="Edit", command=self.edit_profile)
        menu.add_command(label="Delete", command=self.delete_profile)
        menu.post(event.x_root, event.y_root)
    
    def toggle_crafter(self):
        """Toggle crafter status for current profile"""
        if not self.current_profile:
            return
        
        # Toggle current
        was_crafter = bool(self.current_profile.get("is_crafter", False))
        is_now = not was_crafter
        self.current_profile["is_crafter"] = is_now
        
        if is_now:
            name = self.current_profile.get("playerName", "Profile")
            self.craft_status_lbl.config(text=f"Crafter: {name}", fg=COLORS["accent"])
        else:
            # Check if there are other crafters to update label
            other_crafters = [p.get("playerName", "???") for p in self.profiles 
                              if p.get("is_crafter", False) and p != self.current_profile]
            if other_crafters:
                self.craft_status_lbl.config(text=f"Crafter: {other_crafters[0]}", fg=COLORS["accent"])
            else:
                self.craft_status_lbl.config(text="No crafter set", fg=COLORS["fg_dim"])
        
        self.schedule_save()
        self.refresh_list()
    
    def get_crafter_profile(self):
        """Get the profile marked as crafter"""
        for p in self.profiles:
            if p.get("is_crafter", False):
                return p
        return None
    
    def get_crafter_hwnd(self):
        """Get window handle of crafter's NWN process"""
        crafter = self.get_crafter_profile()
        if not crafter:
            return None
        
        cd_key = crafter.get("cdKey")
        if not cd_key or cd_key not in self.sessions.sessions:
            return None
        
        pid = self.sessions.sessions[cd_key]
        if not self.sessions.is_alive(pid):
            return None
        
        from utils.win_automation import user32
        
        # Enumerate all windows and find one with matching PID
        found_hwnd = [None]
        
        @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
        def callback(hwnd, lParam):
            window_pid = ctypes.c_ulong()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(window_pid))
            
            if window_pid.value == pid and user32.IsWindowVisible(hwnd):
                length = user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    found_hwnd[0] = hwnd
                    return False
            return True
        
        user32.EnumWindows(callback, 0)
        return found_hwnd[0]
    
    def activate_crafter_window(self):
        """Activate crafter's NWN window, returns True if successful"""
        hwnd = self.get_crafter_hwnd()
        if not hwnd:
            return False
        
        from utils.win_automation import user32
        
        try:
            # Restore if minimized
            if user32.IsIconic(hwnd):
                user32.ShowWindow(hwnd, 9)  # SW_RESTORE
            
            # Bring to foreground
            user32.SetForegroundWindow(hwnd)
            time.sleep(0.3)
            
            # Verify it's now foreground
            return user32.GetForegroundWindow() == hwnd
        except Exception:
            return False

    def rename_category(self, old_name: str):
        dialog = CustomInputDialog(
            self.root,
            "Rename Category",
            f"Enter new name for '{old_name}':",
            old_name,
        )
        self.root.wait_window(dialog)
        if dialog.result:
            new_name = dialog.result.strip()
            if new_name and new_name != old_name:
                for p in self.profiles:
                    if p.get("category") == old_name:
                        p["category"] = new_name
                self.save_data()
                self.refresh_list()

    def toggle_server_ui(self):
        """Refresh server combobox and status."""
        if hasattr(self, "server_manager"):
            self.server_manager.toggle_server_ui()

    def monitor_processes(self):
        self.sessions.cleanup_dead()
        # Only refresh list if session count changed (avoid constant redraws)
        current_count = len(self.sessions.sessions) if hasattr(self.sessions, "sessions") else 0
        previous_count = getattr(self, "_last_session_count", 0)
        
        if current_count != previous_count:
            self._last_session_count = current_count
            self.refresh_list()
            
            # Sessions appeared (went from 0 to >0) - auto-enable features
            if current_count > 0 and previous_count == 0:
                print(f"[Monitor] Game session started! Auto-enabling features...")
                self._on_sessions_started()
            
            # No sessions remain - auto-disable features
            if current_count == 0 and previous_count > 0:
                print(f"[Monitor] All sessions ended. Auto-disabling features...")
                self._on_sessions_ended()
                
        # Очистка контролирующих профилей для ключей, которые больше не активны
        try:
            inactive = [k for k in self.controller_profile_by_cdkey.keys() if k not in self.sessions.sessions]
            for k in inactive:
                self.controller_profile_by_cdkey.pop(k, None)
        except Exception:
            logging.exception("Unhandled exception")
        # Update launch buttons (update_launch_buttons itself skips redundant layout ops)
        try:
            self.update_launch_buttons()
        except Exception:
            logging.exception("Unhandled exception")
        self.root.after(PROCESS_MONITOR_INTERVAL_MS, self.monitor_processes)

    def is_current_running(self) -> bool:
        if not self.current_profile:
            return False
        key = self.current_profile.get("cdKey")
        return key in self.sessions.sessions

    def detect_existing_session(self):
        """Detect an existing nwmain.exe process and add it to sessions if matches a profile."""
        exe_path = (self.exe_path_var.get() or "").strip()
        # If exe path not configured, fallback to default NWN executable name
        if exe_path:
            exe_name = os.path.basename(exe_path)
        else:
            exe_name = "nwmain.exe"
        try:
            out = subprocess.check_output(
                ["tasklist", "/FI", f"IMAGENAME eq {exe_name}", "/FO", "CSV"],
                creationflags=subprocess.CREATE_NO_WINDOW,
            ).decode("cp1251", errors="ignore").strip().splitlines()

            if len(out) <= 1:
                return

            # Find first non-header line with a PID
            # CSV fields: "Image Name","PID","Session Name","Session#","Mem Usage"
            for line in out[1:]:
                parts = list(filter(None, [p.strip() for p in line.split('","')]))
                if len(parts) >= 2:
                    pid_str = parts[1].replace('"', '').strip()
                    try:
                        pid = int(pid_str)
                    except Exception:
                        continue
                    # Read current cdkey from possible ini files
                    doc = self.doc_path_var.get()
                    current_key = None
                    for ini_name in ["nwncdkey.ini", "cdkey.ini"]:
                        p = os.path.join(doc, ini_name)
                        if os.path.exists(p):
                            try:
                                with open(p, encoding="utf-8", errors="ignore") as f:
                                    for l in f:
                                        if l.strip().startswith("YourKey="):
                                            current_key = l.split("=", 1)[1].strip()
                                            break
                            except Exception:
                                self.log_error("detect_existing_session.read_cdkey", Exception("read error"))
                        if current_key:
                            break

                    if not current_key:
                        return

                    # Find profile with same cdKey
                    for prof in self.profiles:
                        if prof.get("cdKey") == current_key:
                            # Add to sessions and refresh UI
                            try:
                                self.sessions.add(current_key, pid)
                            except Exception:
                                logging.exception("Unhandled exception")
                            try:
                                self.refresh_list()
                                self.update_launch_buttons()
                            except Exception:
                                logging.exception("Unhandled exception")
                            return
        except Exception as e:
            self.log_error("detect_existing_session.tasklist", e)

    def update_launch_buttons(self):
        running = self.is_current_running()

        # Если текущий профиль запущен, но он не контролирующий для своего cdKey, скрываем все элементы управления.
        if running:
            try:
                cdkey = self.current_profile.get("cdKey")
                controller = self.controller_profile_by_cdkey.get(cdkey)
                if controller and controller != self.current_profile.get("playerName"):
                    # Не управляющий профиль: убрать и play, и ctrl_frame.
                    try:
                        self.btn_play.pack_forget()
                    except Exception:
                        logging.exception("Unhandled exception")
                    try:
                        self.ctrl_frame.pack_forget()
                    except Exception:
                        logging.exception("Unhandled exception")
                    self._last_running_state = running  # зафиксировать состояние
                    return
            except Exception:
                logging.exception("Unhandled exception")
        # If nothing changed — don't touch layout (avoids flashing)
        if running == self._last_running_state:
            return
        self._last_running_state = running

        # Всегда показываем панель; только состояние кнопок меняем.
        try:
            self.btn_play.pack(side="left", padx=(0,6))
        except Exception:
            logging.exception("Unhandled exception")
        try:
            self.ctrl_frame.pack(side="left")
        except Exception:
            logging.exception("Unhandled exception")

        if running:
            try:
                self.btn_play.configure(state="disabled")
            except Exception:
                logging.exception("Unhandled exception")
            try:
                self.btn_restart.configure(state="normal")
            except Exception:
                logging.exception("Unhandled exception")
            try:
                self.btn_close.configure(state="normal")
            except Exception:
                logging.exception("Unhandled exception")
        else:
            try:
                self.btn_play.configure(state="normal")
            except Exception:
                logging.exception("Unhandled exception")
            try:
                self.btn_restart.configure(state="disabled")
            except Exception:
                logging.exception("Unhandled exception")
            try:
                self.btn_close.configure(state="disabled")
            except Exception:
                logging.exception("Unhandled exception")
        # Состояние редактирования/удаления обновляется в on_select.

    def refresh_list(self):
        """Delegate to ProfileManager."""
        if hasattr(self, 'profile_manager'):
            self.profile_manager.refresh_list()

    def on_profile_list_motion(self, event):
        """Delegate to ProfileManager."""
        if hasattr(self, 'profile_manager'):
            self.profile_manager.on_profile_list_motion(event)

    def on_profile_list_leave(self, event):
        """Delegate to ProfileManager."""
        if hasattr(self, 'profile_manager'):
            self.profile_manager.on_profile_list_leave(event)

    def on_profile_list_scroll(self, event):
        """Delegate to ProfileManager."""
        if hasattr(self, 'profile_manager'):
            self.profile_manager.on_profile_list_scroll(event)

    def _show_inline_actions(self, idx, bbox=None):
        """Delegate to ProfileManager."""
        if hasattr(self, 'profile_manager'):
            self.profile_manager._show_inline_actions(idx, bbox)

    def hide_inline_actions(self):
        """Delegate to ProfileManager."""
        if hasattr(self, 'profile_manager'):
            self.profile_manager.hide_inline_actions()

    def _schedule_inline_hide(self, delay=150):
        """Delegate to ProfileManager."""
        if hasattr(self, 'profile_manager'):
            self.profile_manager._schedule_inline_hide(delay)

    def _cancel_inline_hide(self):
        """Delegate to ProfileManager."""
        if hasattr(self, 'profile_manager'):
            self.profile_manager._cancel_inline_hide()

    def _select_profile_by_index(self, idx):
        """Delegate to ProfileManager."""
        if hasattr(self, 'profile_manager'):
            return self.profile_manager._select_profile_by_index(idx)
        return False

    def _inline_edit_profile(self):
        """Delegate to ProfileManager."""
        if hasattr(self, 'profile_manager'):
            self.profile_manager._inline_edit_profile()

    def _inline_delete_profile(self):
        """Delegate to ProfileManager."""
        if hasattr(self, 'profile_manager'):
            self.profile_manager._inline_delete_profile()

    def on_drag_start(self, event):
        """Delegate to ProfileManager."""
        if hasattr(self, 'profile_manager'):
            return self.profile_manager.on_drag_start(event)

    def on_drag_drop(self, event):
        """Delegate to ProfileManager."""
        if hasattr(self, 'profile_manager'):
            self.profile_manager.on_drag_drop(event)

    def _side_launch(self):
        """Helper for side launch button."""
        if not self.current_profile:
            try:
                messagebox.showinfo("Info", "Select a profile first.", parent=self.root)
            except Exception:
                logging.exception("Unhandled exception")
            return
        try:
            self.launch_game()
        except Exception:
            logging.exception("Unhandled exception")
        try:
            self.update_launch_buttons()
        except Exception:
            logging.exception("Unhandled exception")

    def toggle_cdkey_visibility(self):
        """Toggle cdkey visibility and update info fields."""
        self.show_key = not self.show_key
        if self.current_profile and hasattr(self, 'profile_manager'):
            self.profile_manager.update_info_fields(self.current_profile)

    # Backward compatibility for existing UI button wiring
    def toggle_key_visibility(self):
        self.toggle_cdkey_visibility()
    
    def update_info_fields(self, p):
        """Delegate to ProfileManager."""
        if hasattr(self, 'profile_manager'):
            self.profile_manager.update_info_fields(p)

    def on_select(self, event):
        """Delegate to ProfileManager."""
        if hasattr(self, 'profile_manager'):
            self.profile_manager.on_select(event)

    def edit_profile(self):
        """Delegate to ProfileManager."""
        if hasattr(self, 'profile_manager'):
            self.profile_manager.edit_profile()

    def delete_profile(self):
        """Delegate to ProfileManager."""
        if hasattr(self, 'profile_manager'):
            self.profile_manager.delete_profile()

    def get_unique_categories(self):
        """Delegate to ProfileManager."""
        if hasattr(self, 'profile_manager'):
            return self.profile_manager.get_unique_categories()
        return ["General"]

    def add_profile(self):
        """Delegate to ProfileManager."""
        if hasattr(self, 'profile_manager'):
            self.profile_manager.add_profile()

    def check_paths_silent(self):
        changed = False
        exe = self.exe_path_var.get()
        if not os.path.exists(exe):
            detected = auto_detect_nwn_path()
            if detected:
                self.exe_path_var.set(detected)
                changed = True
        if changed:
            self.save_data()

    # === ЗАПУСК / ЗАКРЫТИЕ ИГРЫ ===

    def launch_game(self):
        if not self.current_profile:
            messagebox.showwarning(
                "Error", "Select a profile!", parent=self.root
            )
            return

        # Backups are now handled automatically by save_data() via _backup_settings()

        doc = self.doc_path_var.get()
        exe = self.exe_path_var.get()
        key = self.current_profile["cdKey"]

        try:
            content = f"[NWN1]\nYourKey={key}\n"
            for ini_name in ["nwncdkey.ini", "cdkey.ini"]:
                p = os.path.join(doc, ini_name)
                if os.path.exists(p):
                    os.chmod(p, stat.S_IWRITE)
                    tmp = p + ".tmp"
                    with open(tmp, "w", encoding="utf-8") as f:
                        f.write(content)
                    from utils.win_automation import safe_replace

                    safe_replace(tmp, p)

            tml_path = os.path.join(doc, "settings.tml")
            if os.path.exists(tml_path):
                os.chmod(tml_path, stat.S_IWRITE)
            robust_update_settings_tml(
                tml_path, self.current_profile["playerName"]
            )
        except Exception as e:
            self.log_error("launch_game.file_update", e)
            messagebox.showerror(
                "File Error",
                f"Could not update files:\n{e}",
                parent=self.root,
            )
            return

        cmd = [exe]

        if self.use_server_var.get():
            srv_val = self.server_var.get().strip()
            srv_ip = next(
                (s["ip"] for s in self.servers if s["name"] == srv_val),
                srv_val,
            )
            if srv_ip:
                cmd.extend(["+connect", srv_ip])

        args = self.current_profile.get("launchArgs", "").strip()
        if args:
            cmd.extend(args.split())

        try:
            proc = subprocess.Popen(cmd, cwd=os.path.dirname(exe))
            self.sessions.add(key, proc.pid)
            # Назначаем контролирующий профиль для ключа, если еще не назначен.
            try:
                if key not in self.controller_profile_by_cdkey:
                    self.controller_profile_by_cdkey[key] = self.current_profile.get("playerName", "")
            except Exception:
                logging.exception("Unhandled exception")
            self.refresh_list()
            self.update_launch_buttons()
            # можно включать лог-монитор вместе с игрой
            self.start_log_monitor()
        except Exception as e:
            self.log_error("launch_game.Popen", e)
            messagebox.showerror("Launch Error", str(e), parent=self.root)

    def close_game(self):
        if not self.current_profile:
            return
        key = self.current_profile["cdKey"]
        if key in self.sessions.sessions:
            pid = self.sessions.sessions[key]
            def _safe_exit_wrapper():
                try:
                    safe_exit_sequence(
                        pid,
                        self.exit_x,
                        self.exit_y,
                        self.confirm_x,
                        self.confirm_y,
                        speed=getattr(self, "exit_speed", None),
                        esc_count=getattr(self, "esc_count", None),
                        clip_margin=getattr(self, "clip_margin", None),
                    )
                except Exception as e:
                    self.log_error("close_game.safe_exit", e)
                # Ensure sessions cleaned and UI updated on main thread
                try:
                    self.sessions.cleanup_dead()
                except Exception:
                    logging.exception("Unhandled exception")
                try:
                    self.root.after(0, self.update_launch_buttons)
                except Exception:
                    logging.exception("Unhandled exception")

            threading.Thread(target=_safe_exit_wrapper, daemon=True).start()
        # остановим монитор при закрытии
        self.stop_log_monitor()

    def restart_game(self):
        if not self.current_profile:
            return
        key = self.current_profile.get("cdKey")
        self.close_game()
        # Запускаем новый процесс, как только старый действительно выгружен,
        # вместо фиксированной задержки. Таймаут ~30 сек на случай зависания.
        def _wait_and_launch():
            max_iterations = int(GAME_EXIT_TIMEOUT_SECONDS / GAME_EXIT_CHECK_INTERVAL)
            for _ in range(max_iterations):
                try:
                    if key not in self.sessions.sessions:
                        break
                except Exception:
                    break
                time.sleep(GAME_EXIT_CHECK_INTERVAL)
            try:
                self.root.after(0, self.launch_game)
            except Exception:
                logging.exception("Unhandled exception")
        threading.Thread(target=_wait_and_launch, daemon=True).start()

# === SINGLE INSTANCE CHECK ===
LOCK_FILE_NAME = "1609_manager.lock"

def _get_lock_file_path():
    """Get path to lock file in temp directory."""
    return os.path.join(tempfile.gettempdir(), LOCK_FILE_NAME)

def _is_process_running(pid: int) -> bool:
    """Check if a process with given PID is running."""
    try:
        kernel32 = ctypes.windll.kernel32
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        STILL_ACTIVE = 259
        
        handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not handle:
            return False
        
        exit_code = ctypes.wintypes.DWORD()
        result = kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code))
        kernel32.CloseHandle(handle)
        
        if result and exit_code.value == STILL_ACTIVE:
            return True
        return False
    except Exception:
        return False

def acquire_single_instance_lock():
    """Try to acquire a file-based lock to ensure only one instance runs."""
    lock_file = _get_lock_file_path()
    current_pid = os.getpid()
    
    try:
        # Check if lock file exists
        if os.path.exists(lock_file):
            try:
                with open(lock_file, 'r') as f:
                    old_pid = int(f.read().strip())
                
                # Check if that process is still running
                if _is_process_running(old_pid):
                    # Another instance is running
                    return False
                else:
                    # Old process is dead, remove stale lock
                    os.remove(lock_file)
            except (ValueError, OSError):
                # Corrupted lock file, remove it
                try:
                    os.remove(lock_file)
                except Exception:
                    pass
        
        # Create new lock file with our PID
        with open(lock_file, 'w') as f:
            f.write(str(current_pid))
        
        return True
    except Exception as e:
        # On error, allow running
        print(f"Lock check failed: {e}")
        return True

def release_lock():
    """Remove lock file on exit."""
    try:
        lock_file = _get_lock_file_path()
        if os.path.exists(lock_file):
            with open(lock_file, 'r') as f:
                pid = int(f.read().strip())
            # Only remove if it's our lock
            if pid == os.getpid():
                os.remove(lock_file)
    except Exception:
        pass


if __name__ == "__main__":
    # CRITICAL: Change CWD away from _MEIPASS FIRST before anything else
    # This prevents "Failed to remove temporary directory" warning
    app_dir = get_app_dir()
    try:
        if getattr(sys, "frozen", False):
            os.chdir(app_dir)
            # Also close any inherited file handles that might lock the temp dir
            try:
                import gc
                gc.collect()
            except Exception:
                pass
    except Exception:
        pass
    
    # Check for single instance (file-based lock)
    if not acquire_single_instance_lock():
        # Another instance is running - show message and exit
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showwarning(
            "16:09 Manager",
            "Программа уже запущена!\n\n"
            "Проверьте системный трей (область уведомлений)."
        )
        root.destroy()
        sys.exit(0)
    
    # Register cleanup for lock file
    atexit.register(release_lock)
    
    # Use '1609 settings' subfolder for all data files including logs
    data_dir = os.path.join(app_dir, "1609 settings")
    os.makedirs(data_dir, exist_ok=True)
    log_path = get_default_log_path(data_dir)
    configure_logging(log_path)
    
    root = tk.Tk()
    app = NWNManagerApp(root)
    root.mainloop()
