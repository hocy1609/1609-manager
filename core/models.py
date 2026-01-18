from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any

from core.storage import read_json, write_json_atomic
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
    server_group: str = "siala"  # Which server group this profile uses
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
            server_group=_clean_str(data.get("server_group", "siala")) or "siala",
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
class AutoFogConfig:
    enabled: bool = False
    delay: int = 2

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AutoFogConfig":
        return cls(
            enabled=_clean_bool(data.get("enabled", False)),
            delay=_clean_int(data.get("delay", 2)),
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)



@dataclass
class HotkeyBind:
    trigger: str = ""
    sequence: List[str] = field(default_factory=list)
    rightClick: bool = False
    comment: str = ""
    enabled: bool = True

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HotkeyBind":
        return cls(
            trigger=_clean_str(data.get("trigger", "")),
            sequence=[_clean_str(s) for s in _clean_list(data.get("sequence", []))],
            rightClick=_clean_bool(data.get("rightClick", False)),
            comment=_clean_str(data.get("comment", "")),
            enabled=_clean_bool(data.get("enabled", True)),
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class HotkeysConfig:
    enabled: bool = False
    binds: List[HotkeyBind] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HotkeysConfig":
        data = data if isinstance(data, dict) else {}
        binds_raw = _clean_list(data.get("binds", []))
        return cls(
            enabled=_clean_bool(data.get("enabled", False)),
            binds=[HotkeyBind.from_dict(b) for b in binds_raw],
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "binds": [b.to_dict() for b in self.binds],
        }


@dataclass
class LogMonitorConfig:
    enabled: bool = False
    log_path: str = ""
    webhooks: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    open_wounds: OpenWoundsConfig = field(default_factory=OpenWoundsConfig)
    auto_fog: AutoFogConfig = field(default_factory=AutoFogConfig)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LogMonitorConfig":
        ow_raw = data.get("open_wounds", {}) if isinstance(data, dict) else {}
        af_raw = data.get("auto_fog", {}) if isinstance(data, dict) else {}
        return cls(
            enabled=_clean_bool(data.get("enabled", False) if isinstance(data, dict) else False),
            log_path=_clean_str(data.get("log_path", "") if isinstance(data, dict) else ""),
            webhooks=[_clean_str(w) for w in _clean_list(data.get("webhooks", []))] if isinstance(data, dict) else [],
            keywords=[_clean_str(k) for k in _clean_list(data.get("keywords", []))] if isinstance(data, dict) else [],
            open_wounds=OpenWoundsConfig.from_dict(ow_raw),
            auto_fog=AutoFogConfig.from_dict(af_raw),
        )

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["open_wounds"] = self.open_wounds.to_dict()
        payload["auto_fog"] = self.auto_fog.to_dict()
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
    hotkeys: HotkeysConfig = field(default_factory=HotkeysConfig)
    sessions: Dict[str, int] = field(default_factory=dict)
    exit_speed: float = 0.1
    esc_count: int = 1
    clip_margin: int = 48
    show_tooltips: bool = True
    theme: str = "dark"
    favorite_potions: List[str] = field(default_factory=list)
    # Server groups
    server_group: str = "siala"  # Current active group: "siala" or "cormyr"
    server_groups: Dict[str, List[Dict[str, str]]] = field(default_factory=lambda: {
        "siala": [
            {"name": "Siala Main (play.siala.online)", "ip": "play.siala.online"},
            {"name": "Siala Test (91.202.25.110:5122)", "ip": "91.202.25.110:5122"},
        ],
        "cormyr": [
            {"name": "Cormyr Main (91.202.25.110)", "ip": "91.202.25.110"},
            {"name": "Cormyr Mirror 1 (159.69.240.215:5122)", "ip": "159.69.240.215:5122"},
            {"name": "Cormyr Mirror 2 (85.198.108.93)", "ip": "85.198.108.93"},
        ],
    })
    # Saved CD keys for reuse across profiles: [{"name": "Key 1", "key": "XXXXX-..."}]
    saved_keys: List[Dict[str, str]] = field(default_factory=list)

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
        hotkeys_cfg = HotkeysConfig.from_dict(data.get("hotkeys", {}))
        # Migrate hotkeys from log_monitor if present (backward compatibility)
        if not hotkeys_cfg.binds and "hotkeys" in data.get("log_monitor", {}):
            old_hotkeys = data["log_monitor"].get("hotkeys", {})
            hotkeys_cfg = HotkeysConfig.from_dict(old_hotkeys)
        sessions_raw = data.get("sessions", {})
        sessions = {_clean_str(k): _clean_int(v) for k, v in sessions_raw.items()} if isinstance(sessions_raw, dict) else {}
        # Default server groups
        default_groups = {
            "siala": [
                {"name": "Siala Main (play.siala.online)", "ip": "play.siala.online"},
                {"name": "Siala Test (91.202.25.110:5122)", "ip": "91.202.25.110:5122"},
            ],
            "cormyr": [
                {"name": "Cormyr Main (91.202.25.110)", "ip": "91.202.25.110"},
                {"name": "Cormyr Mirror 1 (159.69.240.215:5122)", "ip": "159.69.240.215:5122"},
                {"name": "Cormyr Mirror 2 (85.198.108.93)", "ip": "85.198.108.93"},
            ],
        }
        server_groups_raw = data.get("server_groups", default_groups)
        if not isinstance(server_groups_raw, dict):
            server_groups_raw = default_groups
        # Ensure both groups exist
        for grp in ["siala", "cormyr"]:
            if grp not in server_groups_raw:
                server_groups_raw[grp] = default_groups[grp]
        
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
            hotkeys=hotkeys_cfg,
            sessions=sessions,
            exit_speed=_clean_float(data.get("exit_speed", 0.1)),
            esc_count=_clean_int(data.get("esc_count", 1)),
            clip_margin=_clean_int(data.get("clip_margin", 48)),
            theme=_clean_str(data.get("theme", "dark")) or "dark",
            favorite_potions=[_clean_str(p) for p in _clean_list(data.get("favorite_potions", []))],
            server_group=_clean_str(data.get("server_group", "siala")) or "siala",
            server_groups=server_groups_raw,
            saved_keys=_clean_list(data.get("saved_keys", [])),
        )

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["servers"] = [s.to_dict() for s in self.servers]
        payload["profiles"] = [p.to_dict() for p in self.profiles]
        payload["log_monitor"] = self.log_monitor.to_dict()
        payload["hotkeys"] = self.hotkeys.to_dict()
        payload["sessions"] = self.sessions
        return payload


def load_settings(path: str, fallback_docs: str, fallback_exe: str) -> Settings:
    data = read_json(path, default=None)
    if data is None:
        return Settings.defaults(fallback_docs, fallback_exe)
    return Settings.from_dict(data, fallback_docs, fallback_exe)


def save_settings(path: str, settings: Settings) -> None:
    try:
        write_json_atomic(path, settings.to_dict(), indent=4, ensure_ascii=False)
    except Exception:
        # Silent failure by design to avoid crashing UI; caller can log
        pass
