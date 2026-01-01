import os
import json
import ctypes

from core.models import Settings, load_settings, save_settings

from utils.win_automation import (
    kernel32,
    PROCESS_QUERY_INFORMATION,
    STILL_ACTIVE,
)

SETTINGS_FILE = "nwn_settings.json"
SESSIONS_FILE = "nwn_sessions.json"


class SessionManager:
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.sessions: dict[str, int] = self.load()

    def load(self) -> dict:
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def save(self) -> None:
        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(self.sessions, f)
        except Exception:
            pass

    def add(self, key: str, pid: int) -> None:
        self.sessions[key] = pid
        self.save()

    def is_alive(self, pid: int) -> bool:
        try:
            h_process = kernel32.OpenProcess(PROCESS_QUERY_INFORMATION, False, pid)
            if not h_process:
                return False
            exit_code = ctypes.c_ulong()
            kernel32.GetExitCodeProcess(h_process, ctypes.byref(exit_code))
            kernel32.CloseHandle(h_process)
            return exit_code.value == STILL_ACTIVE
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
