"""
Profile Service and View components for 16:09 Launcher.

Separates data management (CRUD) from UI operations (rendering, dragging).
"""
from typing import List, Optional, Callable
from core.models import Profile

class ProfileService:
    """Manages profile state, CRUD operations, and category logical organization."""
    
    def __init__(self, data_manager):
        self.data_manager = data_manager

    @property
    def profiles(self) -> List[Profile]:
        return getattr(self.data_manager.app, 'profiles', [])

    def save_changes(self):
        """Save current profile structure via data_manager."""
        self.data_manager.save_data()

    def get_unique_categories(self) -> List[str]:
        """Return a sorted list of unique categories, with 'General' first."""
        cats = set()
        for p in self.profiles:
            cats.add(getattr(p, "category", "General"))
        
        res = sorted(list(cats))
        if "General" in res:
            res.remove("General")
            res.insert(0, "General")
        elif not res:
            res = ["General"]
        return res

    def add_profile(self, data: dict) -> Profile:
        p = Profile(
            name=data.get("name", "New Profile"),
            playerName=data.get("playerName", ""),
            cdKey=data.get("cdKey", ""),
            server=data.get("server", ""),
            category=data.get("category", "General") or "General",
            launchArgs=data.get("launchArgs", ""),
            server_group=getattr(self.data_manager.app, 'server_group', "siala"),
        )
        self.profiles.append(p)
        self.save_changes()
        return p

    def update_profile(self, current_profile: Profile, new_data: dict):
        if not current_profile: return
        current_profile.name = new_data.get("name", current_profile.name)
        current_profile.playerName = new_data.get("playerName", current_profile.playerName)
        current_profile.cdKey = new_data.get("cdKey", current_profile.cdKey)
        current_profile.server = new_data.get("server", current_profile.server)
        current_profile.category = new_data.get("category", "General") or "General"
        current_profile.launchArgs = new_data.get("launchArgs", current_profile.launchArgs)
        self.save_changes()

    def delete_profile(self, profile: Profile):
        if profile in self.profiles:
            self.profiles.remove(profile)
            self.save_changes()

    def move_to_group(self, profile: Profile, target_group: str):
        profile.server_group = target_group
        self.save_changes()

    def set_hotkey_exclusive(self, prof: Profile):
        for p in self.profiles:
            p.hotkey_on = False
        prof.hotkey_on = True
        self.save_changes()

    def rename_category(self, old_name: str, new_name: str):
        changed = False
        for p in self.profiles:
            if p.category == old_name:
                p.category = new_name
                changed = True
        if changed:
            self.save_changes()

    def move_category_to_group(self, category_name: str, current_group: str, target_group: str):
        count = 0
        for p in self.profiles:
            if p.category == category_name and p.server_group == current_group:
                p.server_group = target_group
                count += 1
        if count > 0:
            self.save_changes()
        return count
