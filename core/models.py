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
    order: int = 0  # Manual ordering within category
    hotkey_on: bool = False  # Whether hotkeys only work for this profile

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
            order=_clean_int(data.get("order", 0)),
            hotkey_on=_clean_bool(data.get("hotkey_on", False)),
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
    master_toggle_key: str = "CTRL+SHIFT+S"
    binds: List[HotkeyBind] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Any) -> "HotkeysConfig":
        if isinstance(data, cls):
            return data
        data = data if isinstance(data, dict) else {}
        binds_raw = _clean_list(data.get("binds", []))
        return cls(
            enabled=_clean_bool(data.get("enabled", False)),
            master_toggle_key=_clean_str(data.get("master_toggle_key", "CTRL+SHIFT+S")) or "CTRL+SHIFT+S",
            binds=[HotkeyBind.from_dict(b) for b in binds_raw],
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "master_toggle_key": self.master_toggle_key,
            "binds": [b.to_dict() for b in self.binds],
        }


@dataclass
class WebhookConfig:
    url: str
    name: str = "Webhook"
    enabled: bool = True

    @classmethod
    def from_dict(cls, data: Any) -> "WebhookConfig":
        if isinstance(data, cls):
            return data
        if isinstance(data, str):
            return cls(url=data)
        data = data if isinstance(data, dict) else {}
        return cls(
            url=_clean_str(data.get("url", "")),
            name=_clean_str(data.get("name", "Webhook")),
            enabled=_clean_bool(data.get("enabled", True)),
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class LogMonitorConfig:
    enabled: bool = False
    log_path: str = ""
    webhooks: List[WebhookConfig] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    open_wounds: OpenWoundsConfig = field(default_factory=OpenWoundsConfig)
    auto_fog: AutoFogConfig = field(default_factory=AutoFogConfig)
    spy_enabled: bool = False
    mention_here: bool = False
    mention_everyone: bool = False
    spy_profiles: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LogMonitorConfig":
        if isinstance(data, cls):
            return data
        data = data if isinstance(data, dict) else {}
        ow_raw = data.get("open_wounds", {})
        af_raw = data.get("auto_fog", {})
        webhooks_raw = _clean_list(data.get("webhooks", []))
        
        return cls(
            enabled=_clean_bool(data.get("enabled", False)),
            log_path=_clean_str(data.get("log_path", "")),
            webhooks=[WebhookConfig.from_dict(w) for w in webhooks_raw],
            keywords=[_clean_str(k) for k in _clean_list(data.get("keywords", []))],
            open_wounds=OpenWoundsConfig.from_dict(ow_raw),
            auto_fog=AutoFogConfig.from_dict(af_raw),
            spy_enabled=_clean_bool(data.get("spy_enabled", False)),
            mention_here=_clean_bool(data.get("mention_here", False)),
            mention_everyone=_clean_bool(data.get("mention_everyone", False)),
            spy_profiles=[_clean_str(p) for p in _clean_list(data.get("spy_profiles", []))],
        )

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["webhooks"] = [w.to_dict() if hasattr(w, 'to_dict') else w for w in self.webhooks]
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
    # Server groups
    server_group: str = "siala"  # Current active group: "siala" or "cormyr"
    server_groups: Dict[str, List[Server]] = field(default_factory=lambda: {
        "siala": [
            Server(name="Siala Main (play.siala.online)", ip="play.siala.online"),
            Server(name="Siala Test (91.202.25.110:5122)", ip="91.202.25.110:5122"),
        ],
        "cormyr": [
            Server(name="Cormyr Main (91.202.25.110)", ip="91.202.25.110"),
            Server(name="Cormyr Mirror 1 (159.69.240.215:5122)", ip="159.69.240.215:5122"),
            Server(name="Cormyr Mirror 2 (85.198.108.93)", ip="85.198.108.93"),
        ],
    })
    # Saved CD keys for reuse across profiles: [{"name": "Key 1", "key": "XXXXX-..."}]
    saved_keys: List[Dict[str, str]] = field(default_factory=list)
    minimize_to_tray: bool = True
    run_on_startup: bool = False
    # User-defined category order (list of category names)
    category_order: List[str] = field(default_factory=list)
    disable_hotkeys_on_multi_session: bool = False
    collapsed_categories: List[str] = field(default_factory=list)

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
        
        # LogMonitor initialization (restored)
        lm_cfg = LogMonitorConfig.from_dict(data.get("log_monitor", {}))
        
        # Hotkeys migration and loading
        hotkeys_raw = data.get("hotkeys", {})
        # If no hotkeys in top level, check legacy log_monitor
        if not hotkeys_raw and "log_monitor" in data:
            hotkeys_raw = data["log_monitor"].get("hotkeys", {})
        
        hotkeys_cfg = HotkeysConfig.from_dict(hotkeys_raw)
        
        sessions_raw = data.get("sessions", {})
        sessions = {_clean_str(k): _clean_int(v) for k, v in sessions_raw.items()} if isinstance(sessions_raw, dict) else {}
        
        # Server groups migration
        default_groups = {
            "siala": [
                Server(name="Siala Main (play.siala.online)", ip="play.siala.online"),
                Server(name="Siala Test (91.202.25.110:5122)", ip="91.202.25.110:5122"),
            ],
            "cormyr": [
                Server(name="Cormyr Main (91.202.25.110)", ip="91.202.25.110"),
                Server(name="Cormyr Mirror 1 (159.69.240.215:5122)", ip="159.69.240.215:5122"),
                Server(name="Cormyr Mirror 2 (85.198.108.93)", ip="85.198.108.93"),
            ],
        }
        
        server_groups_raw = data.get("server_groups", {})
        server_groups = {}
        if isinstance(server_groups_raw, dict):
            for grp, srvs in server_groups_raw.items():
                if isinstance(srvs, list):
                    server_groups[grp] = [Server.from_dict(s) if isinstance(s, dict) else s for s in srvs]
        
        # Ensure default groups exist
        for grp in default_groups:
            if grp not in server_groups:
                server_groups[grp] = default_groups[grp]
        
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
            server_group=_clean_str(data.get("server_group", "siala")) or "siala",
            server_groups=server_groups,
            saved_keys=_clean_list(data.get("saved_keys", [])),
            minimize_to_tray=_clean_bool(data.get("minimize_to_tray", True)),
            run_on_startup=_clean_bool(data.get("run_on_startup", False)),
            category_order=[_clean_str(c) for c in _clean_list(data.get("category_order", []))],
            disable_hotkeys_on_multi_session=_clean_bool(data.get("disable_hotkeys_on_multi_session", False)),
            collapsed_categories=[_clean_str(c) for c in _clean_list(data.get("collapsed_categories", []))],
        )

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["servers"] = [s.to_dict() for s in self.servers]
        payload["profiles"] = [p.to_dict() for p in self.profiles]
        payload["log_monitor"] = self.log_monitor.to_dict()
        payload["hotkeys"] = self.hotkeys.to_dict()
        payload["sessions"] = self.sessions
        
        # Manual conversion for server_groups
        payload["server_groups"] = {
            grp: [s.to_dict() for s in srvs]
            for grp, srvs in self.server_groups.items()
        }
        return payload

    def get_key_registry(self) -> List[Dict[str, Any]]:
        """
        Returns a list of unique CD keys found in settings and profiles.
        Each entry: { 'key': '...', 'name': '...', 'profiles': ['...', ...] }
        """
        registry = {} # key -> {name, profiles}
        
        # 1. Add keys from all profiles first (most accurate usage info)
        for p in self.profiles:
            key_val = p.cdKey.upper().strip()
            if not key_val:
                continue
                
            if key_val not in registry:
                registry[key_val] = {
                    "key": key_val,
                    "name": f"{key_val[:5]}...{key_val[-5:]}", # Short key representation
                    "profiles": [p.playerName]
                }
            else:
                if p.playerName not in registry[key_val]["profiles"]:
                    registry[key_val]["profiles"].append(p.playerName)
        
        # 2. Add explicitly saved keys from settings if not already there
        for k in self.saved_keys:
            key_val = k.get("key", "").upper().strip()
            if key_val and key_val not in registry:
                registry[key_val] = {
                    "key": key_val,
                    "name": k.get("name", "Unnamed Key"),
                    "profiles": []
                }
            elif key_val in registry:
                # If it's already there, just update the name if the user gave it a pretty name
                custom_name = k.get("name")
                if custom_name and not custom_name.startswith(key_val[:3]):
                    registry[key_val]["name"] = custom_name
                    
        return list(registry.values())


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
