import os
import json
import sys
import time
import threading
import subprocess
import stat
import tempfile
import atexit
import ctypes
import ctypes.wintypes
import logging
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional

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
from core.profile_manager import ProfileManager
from core.settings_manager import SettingsManager
from core.ui_state import UIStateManager
from core.server_manager import ServerManager
from core.data_manager import DataManager
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
class LogMonitorState:
    config: dict = field(default_factory=dict)
    monitor: LogMonitor | None = None
    slayer_monitor: LogMonitor | None = None
    slayer_hit_count: int = 0
    enabled_var: tk.BooleanVar | None = None
    spy_enabled_var: tk.BooleanVar | None = None
    log_path_var: tk.StringVar | None = None
    log_match_var: tk.StringVar | None = None
    webhooks_text: tk.Text | None = None
    keywords_text: tk.Text | None = None
    open_wounds_enabled_var: tk.BooleanVar | None = None
    open_wounds_key_var: tk.StringVar | None = None
    auto_fog_enabled_var: tk.BooleanVar | None = None
    # Keybind state for numpad sequence
    keybind_enabled_var: tk.BooleanVar | None = None
    keybind_key_var: tk.StringVar | None = None
    mention_here_var: tk.BooleanVar | None = None
    mention_everyone_var: tk.BooleanVar | None = None


class NWNManagerApp:
    # Type hints for linter to resolve dynamic attributes
    root: tk.Tk
    ui_state_manager: UIStateManager
    app_dir: str
    data_dir: str
    backups_dir: str
    settings_path: str
    sessions_path: str
    log_path: str
    temp_dir: str | None
    sessions: SessionManager
    _settings_sessions: dict
    log_monitor_manager: LogMonitorManager
    log_monitor_state: LogMonitorState
    keybind_manager: KeybindManager
    multi_hotkey_manager: MultiHotkeyManager
    profile_manager: ProfileManager
    settings_manager: SettingsManager
    server_manager: ServerManager
    tray_manager: TrayManager
    theme_manager: ThemeManager
    settings: Settings
    
    # State attributes initialized in ui_state.py or load_data
    doc_path_var: tk.StringVar
    exe_path_var: tk.StringVar
    server_var: tk.StringVar
    use_server_var: tk.BooleanVar
    exit_x: int
    exit_y: int
    confirm_x: int
    confirm_y: int
    exit_speed: float
    esc_count: int
    clip_margin: int
    show_tooltips: bool
    btn_play: tk.Button
    btn_restart: tk.Button
    btn_close: tk.Button
    lbl_selected_count: tk.Label
    ctrl_frame: tk.Frame
    profiles: list[Profile]
    servers: list[dict]
    server_group: str
    server_groups: dict[str, list[dict]]
    theme: str
    category_order: list[str]
    current_profile: Profile | None
    hotkeys_config: dict
    saved_keys: list[dict]
    minimize_to_tray: bool
    run_on_startup: bool
    show_key: bool
    _last_backup_time: float
    _last_session_count: int
    _last_running_state: bool
    _save_after_id: str | Optional[str]

    # Dynamic attributes from screen builders (monkey-patched at runtime)
    settings_exit_x: tk.StringVar
    settings_exit_y: tk.StringVar
    settings_confirm_x: tk.StringVar
    settings_confirm_y: tk.StringVar
    settings_exit_speed: tk.StringVar
    settings_esc_count: tk.StringVar
    settings_clip_margin: tk.StringVar
    settings_show_tooltips: tk.BooleanVar
    settings_theme: tk.StringVar
    minimize_to_tray_var: tk.BooleanVar
    run_on_startup_var: tk.BooleanVar
    content_frame: tk.Frame
    screens: dict[str, tk.Frame]

    def __init__(self, root: tk.Tk):
        self.root = root
        self.ui_state_manager = UIStateManager(self)
        self.data_manager = DataManager(self)
        self.ui_state_manager.configure_root_window()
        self.ui_state_manager.initialize_state()

        self.app_dir = get_app_dir()

        # Set window icon if available
        try:
            # Check bundle dir first (PyInstaller), then app dir
            base_path = getattr(sys, "_MEIPASS", self.app_dir)
            icon_path = os.path.join(base_path, "Assets", "logo.ico")
            if not os.path.exists(icon_path):
                icon_path = os.path.join(self.app_dir, "Assets", "logo.ico")
            
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
                    import shutil
                    shutil.copyfile(default_settings_src, self.settings_path)
                except Exception:
                    logging.exception("Unhandled exception")
        except Exception:
            logging.exception("Unhandled exception")

            # Temporary working directory: keep it in system temp and remove on exit.
        try:
            self.temp_dir = os.path.join(tempfile.gettempdir(), "nwn_manager_temp")
            path = self.temp_dir
            if path:
                os.makedirs(path, exist_ok=True)
        except Exception:
            self.temp_dir = None

        def _cleanup_temp():
            import shutil

            try:
                path = self.temp_dir
                if path and os.path.exists(path):
                    shutil.rmtree(path, ignore_errors=True)
            except Exception:
                logging.exception("Unhandled exception")

        # Register cleanup on normal interpreter exit
        def _cleanup_wrapper(*args, **kwargs):
            _cleanup_temp()

        # Register cleanup on normal interpreter exit
        try:
            atexit.register(_cleanup_wrapper)
        except Exception:
            logging.exception("Unhandled exception")

        # Initialize sessions with app reference (sessions stored in settings)
        self.sessions = SessionManager(self)
        self._settings_sessions = {}  # Will be populated by load_data

        self.log_monitor_manager = LogMonitorManager(self)
        self.log_monitor_manager.initialize_state()

        self.keybind_manager = KeybindManager(self)
        self.multi_hotkey_manager = MultiHotkeyManager(self)

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
        
        # Re-apply ttk styles after load_data, because load_data calls set_theme()
        # which updates COLORS. The initial setup_styles() above used default colors.
        self.setup_styles()
        
        # Initialize sessions from loaded settings
        self.sessions.init_from_settings(self._settings_sessions)

        # Initialize theme manager after load_data (needs self.theme)
        self.theme_manager = ThemeManager(self)
        self.theme_manager.apply_theme()

        # Multi-profile launch queue
        self._launch_queue = []
        self._processing_launch_queue = False
        
        # UI is already created by apply_theme() above (via rebuild_ui)
        # So we just need to ensure initial selection and cleanup
        
        # Auto-select first profile if none selected and list not empty
        def _initial_select():
            self.profile_manager.select_initial_profile()
        
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

        self.root.after(STARTUP_PATH_CHECK_DELAY_MS, self.check_paths_silent)
        self.root.after(APPWINDOW_SETUP_DELAY_MS, self.set_appwindow)
        
        # Standardize on hotkeys_enabled_var
        hotkeys_cfg = getattr(self, 'hotkeys_config', None)
        is_on = False
        if hotkeys_cfg:
            if isinstance(hotkeys_cfg, dict):
                is_on = hotkeys_cfg.get("enabled", False)
            else:
                is_on = getattr(hotkeys_cfg, "enabled", False)
        self.hotkeys_enabled_var = tk.BooleanVar(value=is_on)
        
        def _on_hotkey_toggle_change(*args):
            self._apply_saved_hotkeys()
        
        self.hotkeys_enabled_var.trace_add("write", _on_hotkey_toggle_change)

    @property
    def nav_buttons(self):
        return self.nav_bar_comp.buttons if self.nav_bar_comp else {}

    @property
    def status_bar_labels(self):
        return self.status_bar_comp.labels if self.status_bar_comp else {}

    # Methods delegated to ThemeManager dynamically via __getattr__
    _THEME_MANAGER_METHODS = {
        "apply_theme",
        "_rebuild_current_screen",
        "_update_all_nav_buttons",
        "_update_nav_bar_theme",
        "_update_sidebar_theme",
        "_update_widget_tree_bg",
        "_update_widget_colors_recursive",
        "_update_status_bar_theme",
        "_update_canvas_widgets",
    }

    def __getattr__(self, name):
        """Delegate theme-related methods to ThemeManager."""
        if name in NWNManagerApp._THEME_MANAGER_METHODS:
            if hasattr(self, 'theme_manager'):
                return getattr(self.theme_manager, name)
            return lambda *args, **kwargs: None  # No-op if theme_manager not ready
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
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
        self.data_manager.migrate_old_settings()

    def _backup_settings(self):
        self.data_manager.backup_settings()

    def _cleanup_old_backups(self, max_backups: int = 10):
        self.data_manager.cleanup_old_backups(max_backups)

    # === ЗАГРУЗКА / СОХРАНЕНИЕ ===

    def load_data(self):
        self.data_manager.load_data()

    def save_data(self):
        self.data_manager.save_data()

    def schedule_save(self, delay_ms: int = SAVE_DEBOUNCE_DELAY_MS):
        """Debounced save: schedule `save_data` after `delay_ms` milliseconds, cancelling previous schedule.

        Default delay chosen as a conservative slower debounce to reduce writes
        while still keeping settings reasonably responsive.
        """
        try:
            after_id = getattr(self, "_save_after_id", None)
            if after_id is not None:
                try:
                    self.root.after_cancel(after_id)
                except Exception:
                    logging.exception("Unhandled exception")
            def _do_save_callback(*args):
                self._save_after_id = None
                self.save_data()
            self._save_after_id = self.root.after(delay_ms, _do_save_callback)
        except Exception as e:
            self.log_error("schedule_save", e)

    def export_data(self, parent=None):
        self.data_manager.export_data(parent)

    def import_data(self, parent=None):
        self.data_manager.import_data(parent)
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
            existing_profile_keys = {(p.playerName, p.cdKey) for p in self.profiles}
            existing_server_ips = {s.ip for s in self.servers}


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
                    self.server_var.set(self.servers[0].name)
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
                    name = getattr(profile, "playerName", "")
                    cdkey = getattr(profile, "cdKey", "")
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
            
            existing_keys = {(p.playerName, p.cdKey) for p in self.profiles}
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
                
                # Use Profile class instead of dict
                profile = Profile(
                    name=name,
                    playerName=name,
                    cdKey=cdkey,
                    category="Imported",
                    launchArgs="",
                    server_group=self.server_group if hasattr(self, 'server_group') else "siala"
                )
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
        """Auto-register hotkeys from saved config on app startup or toggle."""
        try:
            print("[DEBUG] _apply_saved_hotkeys called")
            
            # Sync config enabled state
            if hasattr(self, 'settings') and hasattr(self.settings, 'hotkeys'):
                hotkeys_cfg = self.settings.hotkeys
            else:
                hotkeys_cfg = getattr(self, 'hotkeys_config', None)
                
            if hotkeys_cfg is None:
                return

            is_enabled = self.hotkeys_enabled_var.get()
            if isinstance(hotkeys_cfg, dict):
                hotkeys_cfg["enabled"] = is_enabled
                master_key = hotkeys_cfg.get("master_toggle_key", "ALT+S")
                binds = hotkeys_cfg.get("binds", [])
            else:
                hotkeys_cfg.enabled = is_enabled
                master_key = hotkeys_cfg.master_toggle_key
                binds = hotkeys_cfg.binds

            print(f"[DEBUG] hotkeys enabled: {is_enabled}")
            
            # 1. Update master toggle key
            if hasattr(self, "multi_hotkey_manager"):
                self.multi_hotkey_manager.set_master_toggle(master_key)

            if not is_enabled:
                print("[DEBUG] Hotkeys not enabled, unregistering session keys")
                if hasattr(self, "multi_hotkey_manager"):
                    self.multi_hotkey_manager.unregister_session_keys()
                return
            
            print(f"[DEBUG] Binds count: {len(binds)}")
            if not binds:
                print("[DEBUG] No binds, skipping registration")
                if hasattr(self, "multi_hotkey_manager"):
                    self.multi_hotkey_manager.unregister_session_keys()
                return
            
            from core.keybind_manager import HotkeyAction
            actions = []
            for b in binds:
                # Handle both dict and object
                if isinstance(b, dict):
                    if b.get("enabled", True):
                        actions.append(HotkeyAction.from_dict(b))
                else:
                    if b.enabled:
                        # Map HotkeyBind to HotkeyAction
                        actions.append(HotkeyAction(
                            trigger=b.trigger,
                            sequence=b.sequence,
                            right_click=b.rightClick,
                            comment=b.comment,
                            enabled=b.enabled
                        ))

            print(f"[DEBUG] Actions to register: {len(actions)}")
            if actions:
                count = self.multi_hotkey_manager.register_hotkeys(actions)
                print(f"[DEBUG] Registered {count} hotkeys")
                logging.info(f"Auto-registered {count} hotkeys")
            else:
                if hasattr(self, "multi_hotkey_manager"):
                    self.multi_hotkey_manager.unregister_session_keys()
            
            # 4. Immediate UI updates
            if hasattr(self, 'status_bar_comp') and self.status_bar_comp:
                try:
                    self.status_bar_comp.update()
                except Exception: pass
            
            # Refresh hotkeys screen if active
            current_screen_name = getattr(self, 'current_screen', '')
            if current_screen_name == 'hotkeys' and hasattr(self, '_refresh_hotkeys_list'):
                self._refresh_hotkeys_list()

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
                self.multi_hotkey_manager.unregister_session_keys()
            
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
        """Handle right click on profile list."""
        self.profile_manager.show_profile_menu(event)
    
    def on_middle_click(self, event):
        """Handle middle click on profile list."""
        if hasattr(self, 'profile_manager'):
            return self.profile_manager.on_middle_click(event)


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
                    if getattr(p, "category", "General") == old_name:
                        p.category = new_name
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
        key = self.current_profile.cdKey
        return key in self.sessions.sessions

    def detect_existing_session(self):
        import subprocess

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
                        if prof.cdKey == current_key:
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
                cdkey = self.current_profile.cdKey
                controller = self.controller_profile_by_cdkey.get(cdkey)
                if controller and controller != self.current_profile.playerName:
                    # Не управляющий профиль: убрать и play, и ctrl_frame.
                    if hasattr(self, 'btn_play'):
                        try:
                            self.btn_play.pack_forget()
                        except Exception:
                            logging.exception("Unhandled exception")
                    if hasattr(self, 'ctrl_frame'):
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
        if hasattr(self, 'btn_play'):
            try:
                self.btn_play.pack(side="left", padx=(0,6))
            except Exception:
                logging.exception("Unhandled exception")
        
        if hasattr(self, 'ctrl_frame'):
            try:
                self.ctrl_frame.pack(side="left")
            except Exception:
                logging.exception("Unhandled exception")

        if running:
            if hasattr(self, 'btn_play'):
                try:
                    self.btn_play.configure(state="disabled")
                except Exception:
                    logging.exception("Unhandled exception")
            if hasattr(self, 'btn_restart'):
                try:
                    self.btn_restart.configure(state="normal")
                except Exception:
                    logging.exception("Unhandled exception")
            if hasattr(self, 'btn_close'):
                try:
                    self.btn_close.configure(state="normal")
                except Exception:
                    logging.exception("Unhandled exception")
        else:
            if hasattr(self, 'btn_play'):
                try:
                    self.btn_play.configure(state="normal")
                except Exception:
                    logging.exception("Unhandled exception")
            if hasattr(self, 'btn_restart'):
                try:
                    self.btn_restart.configure(state="disabled")
                except Exception:
                    logging.exception("Unhandled exception")
            if hasattr(self, 'btn_close'):
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

    def launch_selected(self):
        """Delegate to ProfileManager."""
        if hasattr(self, "profile_manager"):
            self.profile_manager.launch_selected()

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

    def _select_profile_by_id(self, item_id):
        """Delegate to ProfileManager."""
        if hasattr(self, 'profile_manager'):
            return self.profile_manager._select_profile_by_id(item_id)
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

    def smart_launch_profiles(self, profiles: list):
        """Add multiple profiles to the launch queue and start processing."""
        if not profiles:
            return
            
        self._launch_queue.extend(profiles)
        
        if not self._processing_launch_queue:
            self._processing_launch_queue = True
            threading.Thread(target=self._process_launch_queue, daemon=True).start()

    def _process_launch_queue(self):
        """Process the launch queue one by one with a delay."""
        try:
            while self._launch_queue:
                profile = self._launch_queue.pop(0)
                
                # Use after() to ensure launch_game runs on main thread for UI safety
                self.root.after(0, lambda p=profile: self.launch_game(p))
                
                # Wait for settings.tml to be safely processed by the game before next launch
                # 3 seconds is a reasonable default for slow disk/updates
                if self._launch_queue:
                    time.sleep(3)
        finally:
            self._processing_launch_queue = False

    def launch_game(self, profile=None):
        import subprocess

        # If profile not provided, use current selection
        target_profile = profile or self.current_profile

        if not target_profile:
            messagebox.showwarning(
                "Error", "Select a profile!", parent=self.root
            )
            return

        # Backups are now handled automatically by save_data() via _backup_settings()

        doc = self.doc_path_var.get()
        exe = self.exe_path_var.get()
        key = target_profile.cdKey

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
                tml_path, target_profile.playerName
            )
        except Exception as e:
            self.log_error("launch_game.file_update", e)
            if not profile: # Only show error dialog if manual single launch
                messagebox.showerror(
                    "File Error",
                    f"Could not update files:\n{e}",
                    parent=self.root,
                )
            return

        cmd = [exe]

        if self.use_server_var.get():
            # If we are launching a specific profile, we might want to use its saved server
            # instead of the currently selected one in the UI.
            srv_val = getattr(target_profile, "server", self.server_var.get()).strip()
            srv_ip = next(
                (s.ip for s in self.app.servers if s.name == srv_val) if hasattr(self, 'app') and hasattr(self.app, 'servers') else
                (s.ip for s in self.servers if s.name == srv_val),
                srv_val,
            )
            if srv_ip:
                cmd.extend(["+connect", srv_ip])

        args = getattr(target_profile, "launchArgs", "").strip()
        if args:
            cmd.extend(args.split())

        try:
            # Launch game detached so it survives launcher exit
            creationflags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
            proc = subprocess.Popen(cmd, cwd=os.path.dirname(exe), creationflags=creationflags)
            self.sessions.add(key, proc.pid)
            # Назначаем контролирующий профиль для ключа, если еще не назначен.
            try:
                if key not in self.controller_profile_by_cdkey:
                    self.controller_profile_by_cdkey[key] = target_profile.playerName
            except Exception:
                logging.exception("Unhandled exception")
            
            # Update UI on main thread
            self.root.after(0, self.refresh_list)
            self.root.after(0, self.update_launch_buttons)
            
            # Note: Log monitor activation is handled by _on_sessions_started 
            # based on user config, we do not force it here.
        except Exception as e:
            self.log_error("launch_game.Popen", e)
            if not profile:
                messagebox.showerror("Launch Error", str(e), parent=self.root)

    def close_game(self):
        if not self.current_profile:
            return
        self.close_game_for_profile(self.current_profile)

    def close_game_for_profile(self, profile):
        """Close a specific profile's game session."""
        key = getattr(profile, "cdKey", None)
        if not key or key not in self.sessions.sessions:
            return
        pid = self.sessions.sessions[key]

        def _safe_exit_wrapper():
            try:
                # Retry up to 5 times
                for attempt in range(5):
                    # Check if game window still exists
                    if not get_hwnd_from_pid(pid):
                        break

                    # Determine speed multiplier
                    # If exit_speed is 0.1 (default fast), allow it.
                    # safe_exit_sequence handles defaults if None.
                    current_speed = getattr(self, "exit_speed", None)
                    
                    safe_exit_sequence(
                        pid,
                        self.exit_x,
                        self.exit_y,
                        self.confirm_x,
                        self.confirm_y,
                        speed=current_speed,
                        esc_count=getattr(self, "esc_count", None),
                        clip_margin=getattr(self, "clip_margin", None),
                    )

                    # Wait up to 0.5 seconds for the window to close (speeded up)
                    # Check every 0.1s
                    for _ in range(5):
                        time.sleep(0.1)
                        if not get_hwnd_from_pid(pid):
                            break
                    
                    # If window is gone, stop retrying
                    if not get_hwnd_from_pid(pid):
                        break
                    
                    # Otherwise continue to next attempt
                    
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
        self.restart_game_for_profile(self.current_profile)

    def restart_game_for_profile(self, profile):
        """Restart a specific profile's game session."""
        key = getattr(profile, "cdKey", None)
        if not key:
            return
        self.close_game_for_profile(profile)
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
        
            # Check if session is still active (close failed)
            if key in self.sessions.sessions:
                self.log_error("restart_game", Exception("Failed to close game within timeout. Aborting restart."))
                return

            try:
                self.root.after(0, lambda: self.smart_launch_profiles([profile]))
            except Exception:
                logging.exception("Unhandled exception")
        threading.Thread(target=_wait_and_launch, daemon=True).start()


# === SINGLE INSTANCE CHECK ===
LOCK_FILE_NAME = "1609_manager.lock"

def _get_lock_file_path():
    """Get path to lock file in temp directory."""
    return os.path.join(tempfile.gettempdir(), LOCK_FILE_NAME)

def _is_process_running(pid: int) -> bool:
    """Check if a process with given PID is running and matches our application."""
    try:
        kernel32 = ctypes.windll.kernel32
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        STILL_ACTIVE = 259
        
        handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not handle:
            return False
        
        exit_code = ctypes.wintypes.DWORD()
        result = kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code))
        
        is_running = False
        if result and exit_code.value == STILL_ACTIVE:
            # PID is active, now verify the process name to avoid collisions
            # (e.g., if a system process reused the PID from a stale lock file)
            try:
                # Get the process image name
                MAX_PATH = 260
                buf = ctypes.create_unicode_buffer(MAX_PATH)
                size = ctypes.wintypes.DWORD(MAX_PATH)
                if kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size)):
                    executable_path = buf.value.lower()
                    executable_name = os.path.basename(executable_path)
                    
                    # Check if the name matches common patterns for our app
                    valid_names = {"python.exe", "pythonw.exe", "1609manager.exe", "1609_manager.exe"}
                    if executable_name in valid_names:
                        is_running = True
                    else:
                        # PID collision with unrelated process
                        is_running = False
                else:
                    # Could not get name, fallback to True to be safe
                    is_running = True
            except Exception:
                # Fallback on name check failure
                is_running = True
                
        kernel32.CloseHandle(handle)
        return is_running
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
