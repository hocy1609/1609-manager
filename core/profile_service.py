"""
Profile Service and View components for 16:09 Launcher.

Separates data management (CRUD) from UI operations (rendering, dragging).
"""
from typing import List, Optional, Callable
from core.models import Profile

def _get_attr(obj, name: str, default=None):
    """Get attribute from Profile dataclass or dict. Supports transition period."""
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)

def _set_attr(obj, name: str, value):
    """Set attribute on Profile dataclass or dict. Supports transition period."""
    if isinstance(obj, dict):
        obj[name] = value
    else:
        setattr(obj, name, value)

class ProfileService:
    """Manages profile state, CRUD operations, and category logical organization."""
    
    def __init__(self, data_manager):
        self.data_manager = data_manager

    @property
    def profiles(self):
        return getattr(self.data_manager.app, 'profiles', [])

    def save_changes(self):
        """Save current profile structure via data_manager."""
        self.data_manager.save_data()

    def get_unique_categories(self) -> List[str]:
        """Return a sorted list of unique categories, with 'General' first."""
        cats = set()
        for p in self.profiles:
            cats.add(_get_attr(p, "category", "General"))
        
        res = sorted(list(cats))
        if "General" in res:
            res.remove("General")
            res.insert(0, "General")
        elif not res:
            res = ["General"]
        return res

    def add_profile(self, data: dict):
        p = {
            "name": data.get("name", "New Profile"),
            "desc": data.get("desc", ""),
            "playerName": data.get("playerName", ""),
            "cdKey": data.get("cdKey", ""),
            "server": data.get("server", ""),
            "password": data.get("password", ""),
            "category": data.get("category", "General"),
            "launchArgs": data.get("launchArgs", ""),
            "is_crafter": bool(data.get("is_crafter", False)),
            "server_group": getattr(self.data_manager.app, 'server_group', "siala"),
        }
        self.profiles.append(p)
        self.save_changes()
        return p

    def update_profile(self, current_profile: dict, new_data: dict):
        if not current_profile: return
        _set_attr(current_profile, "name", new_data.get("name", ""))
        _set_attr(current_profile, "desc", new_data.get("desc", ""))
        _set_attr(current_profile, "playerName", new_data.get("playerName", ""))
        _set_attr(current_profile, "cdKey", new_data.get("cdKey", ""))
        _set_attr(current_profile, "server", new_data.get("server", ""))
        _set_attr(current_profile, "password", new_data.get("password", ""))
        _set_attr(current_profile, "category", new_data.get("category", "General"))
        _set_attr(current_profile, "launchArgs", new_data.get("launchArgs", ""))
        _set_attr(current_profile, "is_crafter", bool(new_data.get("is_crafter", False)))
        self.save_changes()

    def delete_profile(self, profile):
        if profile in self.profiles:
            self.profiles.remove(profile)
            self.save_changes()

    def move_to_group(self, profile, target_group: str):
        _set_attr(profile, "server_group", target_group)
        self.save_changes()

    def set_hotkey_exclusive(self, prof):
        for p in self.profiles:
            _set_attr(p, "hotkey_on", False)
        _set_attr(prof, "hotkey_on", True)
        self.save_changes()

    def rename_category(self, old_name: str, new_name: str):
        changed = False
        for p in self.profiles:
            if _get_attr(p, "category") == old_name:
                _set_attr(p, "category", new_name)
                changed = True
        if changed:
            self.save_changes()

    def move_category_to_group(self, category_name: str, current_group: str, target_group: str):
        count = 0
        for p in self.profiles:
            p_cat = _get_attr(p, "category", "General")
            p_group = _get_attr(p, "server_group", "siala")
            if p_cat == category_name and p_group == current_group:
                _set_attr(p, "server_group", target_group)
                count += 1
        if count > 0:
            self.save_changes()
        return count
