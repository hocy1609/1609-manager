import os
import json
import ctypes
import tempfile

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
        pass
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
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.sessions: dict[str, int] = self.load()

    def load(self) -> dict:
        return read_json(self.filepath, default={}) or {}

    def save(self) -> None:
        write_json_atomic(self.filepath, self.sessions)

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
