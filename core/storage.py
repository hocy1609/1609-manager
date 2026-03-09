import os
import json
import ctypes
import tempfile
import logging

from utils.win_automation import (
    kernel32,
    PROCESS_QUERY_INFORMATION,
    STILL_ACTIVE,
)

SETTINGS_FILE = "nwn_settings.json"
SESSIONS_FILE = "nwn_sessions.json"

def read_json(path: str, default: dict | None = None) -> dict | None:
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def write_json_atomic(
    path: str,
    data: dict,
    *,
    indent: int | None = None,
    ensure_ascii: bool = False,
) -> None:
    dir_path = os.path.dirname(path)
    if dir_path:
        os.makedirs(dir_path, exist_ok=True)
    fd = None
    tmp_path = None
    try:
        fd, tmp_path = tempfile.mkstemp(prefix=".tmp", dir=dir_path or None)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent, ensure_ascii=ensure_ascii)
            f.flush()
            os.fsync(f.fileno())
        fd = None
        os.replace(tmp_path, path)
        tmp_path = None
    except Exception:
        logging.exception("Failed to write JSON atomically")
    finally:
        if fd is not None:
            try:
                os.close(fd)
            except Exception:
                pass
        if tmp_path:
            try:
                os.remove(tmp_path)
            except Exception:
                pass


class SessionManager:
    """Manages active game sessions.
    
    Sessions are stored in the main settings file via app.save_data().
    For backward compatibility, can also work with a file path directly.
    """
    def __init__(self, filepath_or_app):
        self._app = None
        self.filepath = None
        self.sessions: dict[str, int] = {}
        
        # Check if it's an app reference or file path
        if hasattr(filepath_or_app, 'save_data'):
            self._app = filepath_or_app
            # Sessions will be loaded from app's settings
        else:
            self.filepath = filepath_or_app
            self.sessions = self.load()

    def init_from_settings(self, sessions_dict: dict):
        """Initialize sessions from loaded settings."""
        self.sessions = sessions_dict or {}

    def load(self) -> dict:
        if self.filepath:
            return read_json(self.filepath, default={}) or {}
        return {}

    def save(self) -> None:
        if self._app:
            # Sync to app's sessions and save
            if hasattr(self._app, '_settings_sessions'):
                self._app._settings_sessions = self.sessions.copy()
            self._app.save_data()
        elif self.filepath:
            write_json_atomic(self.filepath, self.sessions)

    def add(self, key: str, pid: int) -> None:
        self.sessions[key] = pid
        self.save()

    def is_alive(self, pid: int) -> bool:
        try:
            h_process = kernel32.OpenProcess(PROCESS_QUERY_INFORMATION | 0x0010, False, pid)  # 0x0010 = PROCESS_VM_READ
            if not h_process:
                return False
            exit_code = ctypes.c_ulong()
            kernel32.GetExitCodeProcess(h_process, ctypes.byref(exit_code))
            
            if exit_code.value != STILL_ACTIVE:
                kernel32.CloseHandle(h_process)
                return False
                
            # Extra safety: check image name to prevent false positives when PIDs are reused by other programs
            try:
                psapi = ctypes.windll.psapi
                buf = ctypes.create_unicode_buffer(512)
                if psapi.GetProcessImageFileNameW(h_process, buf, 512) > 0:
                    # Get base name of configured executable
                    name = os.path.basename(buf.value).lower()
                    allowed_exes = ["nwmain.exe", "xnwn.exe"]
                    if self._app and hasattr(self._app, 'settings') and self._app.settings.exe_path:
                        conf_exe = os.path.basename(self._app.settings.exe_path).lower()
                        if conf_exe and conf_exe not in allowed_exes:
                            allowed_exes.append(conf_exe)
                    
                    if name not in allowed_exes:
                        kernel32.CloseHandle(h_process)
                        return False
            except Exception:
                pass
                
            kernel32.CloseHandle(h_process)
            return True
        except Exception:
            return False

    def cleanup_dead(self) -> None:
        dead = []
        for key, pid in list(self.sessions.items()):
            if not self.is_alive(pid):
                dead.append(key)
        for k in dead:
            del self.sessions[k]
        if dead:
            self.save()