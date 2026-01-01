from __future__ import annotations

import os
import re
import json
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any

CDKEY_PATTERN = re.compile(r"^[A-Z0-9]{5}(?:-[A-Z0-9]{5}){6}$")


def _clean_str(val: Any, default: str = "") -> str:
    if val is None:
        return default
    try:
        return str(val)
    except Exception:
        return default


def _clean_bool(val: Any, default: bool = False) -> bool:
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.lower() == "true"
    try:
        return bool(val)
    except Exception:
        return default


def _clean_int(val: Any, default: int = 0) -> int:
    try:
        return int(val)
    except Exception:
        return default


def _clean_float(val: Any, default: float = 0.0) -> float:
    try:
        return float(val)
    except Exception:
        return default


def _clean_list(val: Any) -> list:
    return val if isinstance(val, list) else []


def validate_cdkey(raw: str) -> str:
    key = _clean_str(raw).upper()
    if not key:
        return ""
    if CDKEY_PATTERN.match(key):
        return key
    # allow keys without dashes, auto-insert
    key_no_dash = re.sub(r"[^A-Z0-9]", "", key)
    if len(key_no_dash) == 35:
        groups = [key_no_dash[i:i+5] for i in range(0, 35, 5)]
        candidate = "-".join(groups)
        if CDKEY_PATTERN.match(candidate):
            return candidate
    return key  # return cleaned but not validated to avoid data loss


@dataclass
class Server:
    name: str
    ip: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Server":
        return cls(
            name=_clean_str(data.get("name", "")),
            ip=_clean_str(data.get("ip", "")),
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Profile:
    name: str
    cdKey: str
    playerName: str
    category: str = "General"
    launchArgs: str = ""
    server: str = ""
    is_crafter: bool = False

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Profile":
        return cls(
            name=_clean_str(data.get("name", "")) or "New Profile",
            cdKey=validate_cdkey(data.get("cdKey", "")),
            playerName=_clean_str(data.get("playerName", "")),
            category=_clean_str(data.get("category", "General")) or "General",
            launchArgs=_clean_str(data.get("launchArgs", "")),
            server=_clean_str(data.get("server", "")),
            is_crafter=_clean_bool(data.get("is_crafter", False)),
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class OpenWoundsConfig:
    enabled: bool = False
    key: str = "F1"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OpenWoundsConfig":
        return cls(
            enabled=_clean_bool(data.get("enabled", False)),
            key=_clean_str(data.get("key", "F1")) or "F1",
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class LogMonitorConfig:
    enabled: bool = False
    log_path: str = ""
    webhooks: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    open_wounds: OpenWoundsConfig = field(default_factory=OpenWoundsConfig)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LogMonitorConfig":
        ow_raw = data.get("open_wounds", {}) if isinstance(data, dict) else {}
        return cls(
            enabled=_clean_bool(data.get("enabled", False) if isinstance(data, dict) else False),
            log_path=_clean_str(data.get("log_path", "") if isinstance(data, dict) else ""),
            webhooks=[_clean_str(w) for w in _clean_list(data.get("webhooks", []))] if isinstance(data, dict) else [],
            keywords=[_clean_str(k) for k in _clean_list(data.get("keywords", []))] if isinstance(data, dict) else [],
            open_wounds=OpenWoundsConfig.from_dict(ow_raw),
        )

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["open_wounds"] = self.open_wounds.to_dict()
        return payload


@dataclass
class Settings:
    doc_path: str
    exe_path: str
    servers: List[Server] = field(default_factory=list)
    profiles: List[Profile] = field(default_factory=list)
    auto_connect: bool = False
    last_server: str = ""
    exit_coords_x: int = 950
    exit_coords_y: int = 640
    confirm_coords_x: int = 802
    confirm_coords_y: int = 613
    log_monitor: LogMonitorConfig = field(default_factory=LogMonitorConfig)
    exit_speed: float = 0.1
    esc_count: int = 1
    clip_margin: int = 48
    show_tooltips: bool = True
    theme: str = "dark"
    favorite_potions: List[str] = field(default_factory=list)

    @classmethod
    def defaults(cls, docs: str, exe: str) -> "Settings":
        return cls(doc_path=docs, exe_path=exe)

    @classmethod
    def from_dict(cls, data: Dict[str, Any], fallback_docs: str, fallback_exe: str) -> "Settings":
        data = data or {}
        servers = [Server.from_dict(s) for s in _clean_list(data.get("servers", [])) if s.get("ip")]
        profiles = [Profile.from_dict(p) for p in _clean_list(data.get("profiles", []))]
        last_server = _clean_str(data.get("last_server", ""))
        # filter legacy empty servers
        servers = [s for s in servers if s.ip]
        lm_cfg = LogMonitorConfig.from_dict(data.get("log_monitor", {}))
        return cls(
            doc_path=_clean_str(data.get("doc_path", fallback_docs)) or fallback_docs,
            exe_path=_clean_str(data.get("exe_path", fallback_exe)) or fallback_exe,
            servers=servers,
            profiles=profiles,
            auto_connect=_clean_bool(data.get("auto_connect", False)),
            last_server=last_server,
            exit_coords_x=_clean_int(data.get("exit_coords_x", 950)),
            exit_coords_y=_clean_int(data.get("exit_coords_y", 640)),
            confirm_coords_x=_clean_int(data.get("confirm_coords_x", 802)),
            confirm_coords_y=_clean_int(data.get("confirm_coords_y", 613)),
            log_monitor=lm_cfg,
            exit_speed=_clean_float(data.get("exit_speed", 0.1)),
            esc_count=_clean_int(data.get("esc_count", 1)),
            clip_margin=_clean_int(data.get("clip_margin", 48)),
            show_tooltips=_clean_bool(data.get("show_tooltips", True)),
            theme=_clean_str(data.get("theme", "dark")) or "dark",
            favorite_potions=[_clean_str(p) for p in _clean_list(data.get("favorite_potions", []))],
        )

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["servers"] = [s.to_dict() for s in self.servers]
        payload["profiles"] = [p.to_dict() for p in self.profiles]
        payload["log_monitor"] = self.log_monitor.to_dict()
        return payload


def load_settings(path: str, fallback_docs: str, fallback_exe: str) -> Settings:
    if not os.path.exists(path):
        return Settings.defaults(fallback_docs, fallback_exe)
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return Settings.from_dict(data, fallback_docs, fallback_exe)
    except Exception:
        return Settings.defaults(fallback_docs, fallback_exe)


def save_settings(path: str, settings: Settings) -> None:
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(settings.to_dict(), f, indent=4, ensure_ascii=False)
    except Exception:
        # Silent failure by design to avoid crashing UI; caller can log
        pass
