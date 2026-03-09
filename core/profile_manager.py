"""
Profile Manager for 16:09 Launcher.

Handles all profile-related operations including:
- Profile list management and rendering with categories
- CRUD operations (Create, Read, Update, Delete)
- Inline actions (edit/delete buttons on hover)
- Category management
- Profile selection handling
"""

import tkinter as tk
from tkinter import ttk, messagebox
import logging
from typing import Dict, List, Optional, Any

from ui.ui_base import COLORS, ModernButton, bind_hover_effects
from core.models import Profile
from ui.dialogs import EditDialog
from core.profile_service import ProfileService

class ProfileManager:
    """
    Manages profile operations and UI interactions.
    
    Takes a reference to the main app to access its state (profiles, settings) 
    and UI elements (listbox, labels, buttons).
    """
    
    def __init__(self, app):
        """
        Initialize the ProfileManager.
        
        Args:
            app: Reference to the NWNManagerApp instance
        """
        self.app = app
        if hasattr(self.app, 'data_manager'):
            self.service = ProfileService(self.app.data_manager)
        else:
            self.service = None  # Will be initialized after app finishes setup
        
        self.collapsed_categories = set(getattr(self.app.settings, 'collapsed_categories', [])) if hasattr(self.app, 'settings') else set()
        
        # State for inline actions
        self._hover_item_id = None
        self._inline_frame = None
        self._inline_hide_job = None
        
        self.item_map = {}  # Map item_id -> profile object
        
    def move_profile_to_group(self, profile: Profile, target_group: str):
        """Move profile to another server group and refresh list."""
        if getattr(self, 'service', None):
            self.service.move_to_group(profile, target_group)
            self.refresh_list()
        else:
            profile.server_group = target_group
            self.app.save_data()
            self.refresh_list()
        
    def refresh_list(self):
        """Refreshes the profile list (Treeview) with categories."""
        if not hasattr(self.app, 'lb'):
            return

        # Destroy stale inline action frames before rebuilding treeview
        self.hide_inline_actions()

        tree = self.app.lb
        # Clear tree
        tree.delete(*tree.get_children())
        self.item_map = {}
        
        # Determine categories and sorting (reuse logic)
        
        # Configure tags for Treeview styling
        # Categories: Bold, distinct color
        tree.tag_configure(
            "category", 
            font=("Segoe UI", 10, "bold"), 
            foreground=COLORS.get("accent", "#4cc9f0") # distinct color
        )
        # Profiles: Standard
        tree.tag_configure(
            "profile", 
            font=("Segoe UI", 10)
        )
        # Hover state: Subtle background
        tree.tag_configure(
            "hover",
            background=COLORS.get("bg_input", "#2E333D")
        )
        # Running state: Green text to indicate active game session
        tree.tag_configure(
            "running",
            foreground=COLORS.get("running_indicator", "#95D5B2"),
            background=COLORS.get("running_bg", "#233D30")
        )
        
        # Get user-defined category order or build from existing categories
        category_order = getattr(self.app, 'category_order', [])
        
        # Collect all existing categories from profiles
        existing_cats = set()
        for p in self.app.profiles:
            existing_cats.add(p.category)
        
        # Build final category list
        ordered_cats = []
        for cat in category_order:
            if cat in existing_cats:
                ordered_cats.append(cat)
                existing_cats.discard(cat)
        
        # Add remaining categories
        remaining = sorted(existing_cats)
        if "General" in remaining:
            remaining.remove("General")
            remaining.insert(0, "General")
        ordered_cats.extend(remaining)
        
        # Sort profiles by category order, then by profile's order field
        def sort_key(p):
            cat = p.category
            order = p.order
            try:
                cat_idx = ordered_cats.index(cat)
            except ValueError:
                cat_idx = len(ordered_cats)
            return (cat_idx, order)

        if self.app.profiles:
           self.app.profiles.sort(key=sort_key)
        
        # Filter profiles based on selected server group (siala/cormyr)
        current_group = getattr(self.app, 'server_group', 'siala')
        
        filtered_profiles = []
        for p in self.app.profiles:
            # Get profile's group, default to 'siala' if missing
            pg = p.server_group
            if pg == current_group:
                filtered_profiles.append(p)
        
        # Insert into Treeview
        for cat in ordered_cats:
            # Find profiles in this category AND server group
            cat_profiles = [p for p in filtered_profiles if p.category == cat]
            
            if not cat_profiles:
                continue

            # Create category node
            is_open = cat not in self.collapsed_categories
            cat_id = tree.insert("", "end", text=cat, open=is_open, tags=("category",))
            
            for i, p in enumerate(cat_profiles):
                # Prepare display text: only profile name, no login name in parentheses
                name = p.name
                if not name:
                    name = f"Profile {self.app.profiles.index(p) + 1}"
                
                # Hotkey indicator
                indicator = "⌨️ " if p.hotkey_on else ""
                display_text = f"{indicator}{name}"
                
                # Apply 'alt' tag to odd rows for striping, combined with 'profile' tag
                profile_tags = ["profile"]
                if i % 2 == 1:
                    profile_tags.append("alt")
                    
                # Check if profile is running
                if p.cdKey and p.cdKey in getattr(self.app.sessions, 'sessions', {}):
                    profile_tags.append("running")
                
                # Insert profile node
                p_id = tree.insert(cat_id, "end", text=display_text, tags=tuple(profile_tags))
                self.item_map[p_id] = p
                
                # Restore selection if it matches current profile
                if self.app.current_profile == p:
                    tree.selection_set(p_id)
                    tree.see(p_id)


            
    def get_unique_categories(self) -> List[str]:
        """Return a sorted list of unique profile categories, with 'General' first."""
        if getattr(self, 'service', None):
            return self.service.get_unique_categories()
        cats = set()
        for p in self.app.profiles:
            cats.add(p.category)
        
        res = sorted(list(cats))
        if "General" in res:
            res.remove("General")
            res.insert(0, "General")
        elif not res:
            res = ["General"]
        return res

    def add_profile(self):
        """Open the Edit dialog for a new profile and append it on save."""
        cats = self.get_unique_categories()
        
        def on_save(data: dict):
            if getattr(self, 'service', None):
                new_p = self.service.add_profile(data)
            else:
                # Create new Profile instance
                new_p = Profile(
                    name=data.get("name", "New Profile"),
                    playerName=data.get("playerName", ""),
                    cdKey=data.get("cdKey", ""),
                    server=data.get("server", ""),
                    category=data.get("category", "General") or "General",
                    launchArgs=data.get("launchArgs", ""),
                    server_group=getattr(self.app, 'server_group', "siala"),
                )
                self.app.profiles.append(new_p)
                self.app.save_data()
            
            # Select the new profile
            self.app.current_profile = new_p
            self.refresh_list()
            self.update_info_fields(new_p)
            self.app.on_select(None)

        # Get key registry for dropdown
        key_registry = []
        if hasattr(self.app, 'settings'):
            key_registry = self.app.settings.get_key_registry()

        EditDialog(
            self.app.root,
            title="Add Profile",
            categories=cats,
            on_save=on_save,
            server_list=[s.name for s in self.app.servers],
            is_new=True,
            saved_keys=key_registry
        )

    def edit_profile(self):
        """Open the Edit dialog for the currently selected profile."""
        if not self.app.current_profile:
            return

        cats = self.get_unique_categories()
        old_p = self.app.current_profile

        def on_save(data: dict):
            if getattr(self, 'service', None):
                self.service.update_profile(old_p, data)
            else:
                # Update existing profile attributes
                old_p.name = data.get("name", old_p.name)
                old_p.playerName = data.get("playerName", old_p.playerName)
                old_p.cdKey = data.get("cdKey", old_p.cdKey)
                old_p.server = data.get("server", old_p.server)
                old_p.category = data.get("category", "General") or "General"
                old_p.launchArgs = data.get("launchArgs", "")
                self.app.save_data()

            # Ensure current profile remains selected
            self.app.current_profile = old_p
            self.refresh_list()
            
            self.update_info_fields(old_p)
            self.app.on_select(None)

        # Get key registry for dropdown
        key_registry = []
        if hasattr(self.app, 'settings'):
            key_registry = self.app.settings.get_key_registry()

        EditDialog(
            self.app.root,
            title="Edit Profile",
            profile_data=old_p,
            categories=cats,
            on_save=on_save,
            server_list=[s.name for s in self.app.servers],
            saved_keys=key_registry
        )

    def delete_profile(self):
        """Delete the currently selected profile."""
        if not self.app.current_profile:
            return
        
        name = getattr(self.app.current_profile, "name", "Unknown")
        if messagebox.askyesno("Delete Profile", f"Are you sure you want to delete '{name}'?"):
            if getattr(self, 'service', None):
                 self.service.delete_profile(self.app.current_profile)
                 self.app.current_profile = None
            elif self.app.current_profile in self.app.profiles:
                self.app.profiles.remove(self.app.current_profile)
                self.app.current_profile = None
                self.app.save_data()
            self.refresh_list()
            self.app.on_select(None)

    def rename_category(self, old_name: str):
        """Renames a category and updates all profiles in it."""
        from ui.dialogs import CustomInputDialog
        
        dialog = CustomInputDialog(self.app.root, "Rename Category", f"New name for '{old_name}':", initial_value=old_name)
        self.app.root.wait_window(dialog)
        
        new_name = getattr(dialog, 'result', None)
        if new_name and new_name != old_name:
            if getattr(self, 'service', None):
                self.service.rename_category(old_name, new_name)
            else:
                changed = False
                for p in self.app.profiles:
                    if p.category == old_name:
                        p.category = new_name
                        changed = True
                if changed:
                    if hasattr(self.app, 'category_order') and old_name in self.app.category_order:
                        idx = self.app.category_order.index(old_name)
                        self.app.category_order[idx] = new_name
                    self.app.save_data()
            
            # Persist collapsed state if the renamed category was collapsed
            if old_name in self.collapsed_categories:
                self.collapsed_categories.remove(old_name)
                self.collapsed_categories.add(new_name)
                # settings.collapsed_categories is updated in save_data() via list(profile_manager.collapsed_categories)
                self.app.save_data()

            self.refresh_list()

    def toggle_category(self, category: str):
        """Toggle collapsed state of a category."""
        if category in self.collapsed_categories:
            self.collapsed_categories.remove(category)
        else:
            self.collapsed_categories.add(category)
        self.refresh_list()

    def move_category_to_group(self, category_name: str, target_group: str):
        """Move all profiles in a category to another server group."""
        current_group = getattr(self.app, 'server_group', 'siala')
        
        if getattr(self, 'service', None):
            count = self.service.move_category_to_group(category_name, current_group, target_group)
        else:
            count = 0
            for p in self.app.profiles:
                if p.category == category_name and p.server_group == current_group:
                    p.server_group = target_group
                    count += 1
            if count > 0:
                self.app.save_data()
                
        if count > 0:
            self.refresh_list()
            messagebox.showinfo("Move Category", f"Moved {count} profiles from '{category_name}' to {target_group.title()}.")
        else:
            messagebox.showinfo("Move Category", "No profiles found to move.")

    def show_profile_menu(self, event):
        """Show context menu for profiles."""
        tree = self.app.lb
        # Identify row at Y coordinate
        item_id = tree.identify_row(event.y)
        if not item_id:
            return

        # Select the item
        tree.selection_set(item_id)
        self.on_select(None)
        
        tags = tree.item(item_id, "tags")
        
        # Determine target group for moves
        current_group = getattr(self.app, 'server_group', 'siala')
        target_group = "cormyr" if current_group == "siala" else "siala"
        target_name = "Cormyr" if target_group == "cormyr" else "Siala"
        
        if "category" in tags:
            # Menu for category
            cat_name = tree.item(item_id, "text")
            menu = tk.Menu(self.app.root, tearoff=0, bg=COLORS.get("bg_menu", COLORS["bg_panel"]), fg=COLORS["fg_text"])
            
            # Smart Launch Category
            menu.add_command(
                label=f"Smart Launch All: {cat_name}",
                command=lambda: self.launch_category(cat_name)
            )
            menu.add_separator()
            
            menu.add_command(label="Rename Category", command=lambda: self.rename_category(cat_name))
            
            # Move Category Option
            menu.add_command(
                label=f"Move All to {target_name}",
                command=lambda: self.move_category_to_group(cat_name, target_group)
            )
            
            menu.post(event.x_root, event.y_root)
            
        elif "profile" in tags:
            # Menu for profile
            if item_id not in self.item_map:
                return
            prof = self.item_map[item_id]
            
            # Check if multiple profiles are selected
            selection = tree.selection()
            if len(selection) > 1:
                menu = tk.Menu(self.app.root, tearoff=0, bg=COLORS.get("bg_menu", COLORS["bg_panel"]), fg=COLORS["fg_text"])
                menu.add_command(
                    label=f"Smart Launch Selected ({len(selection)})",
                    command=self.launch_selected
                )
                menu.post(event.x_root, event.y_root)
                return

            menu = tk.Menu(self.app.root, tearoff=0, bg=COLORS.get("bg_menu", COLORS["bg_panel"]), fg=COLORS["fg_text"])
            
            menu.add_command(label="Edit", command=lambda: self.edit_profile())
            
            # Move to other group
            menu.add_command(
                label=f"Move to {target_name}", 
                command=lambda: self.move_profile_to_group(prof, target_group)
            )
            
            menu.add_separator()
            menu.add_command(label="Delete", command=lambda: self.delete_profile())
            menu.add_separator()
            
            # Hotkey ON/OFF (Exclusive)
            hk_label = "Hotkey: OFF ⌨️" if prof.hotkey_on else "Hotkey: ON ⌨️"
            menu.add_command(
                label=hk_label,
                command=lambda: self.toggle_hotkey_on(prof)
            )
            
            menu.post(event.x_root, event.y_root)

    def launch_category(self, category_name: str):
        """Launch all profiles in a category using smart launch."""
        profiles = [p for p in self.app.profiles if p.category == category_name]
        if profiles:
            self.app.smart_launch_profiles(profiles)

    def launch_selected(self):
        """Launch all selected profiles using smart launch."""
        tree = self.app.lb
        selection = tree.selection()
        profiles = []
        for item_id in selection:
            if item_id in self.item_map:
                profiles.append(self.item_map[item_id])
        
        if profiles:
            self.app.smart_launch_profiles(profiles)

    def close_selected(self):
        """Close game for all selected profiles that are currently running."""
        tree = self.app.lb
        selection = tree.selection()
        for item_id in selection:
            if item_id in self.item_map:
                profile = self.item_map[item_id]
                key = profile.cdKey
                if key and key in self.app.sessions.sessions:
                    self.app.close_game_for_profile(profile)

    def restart_selected(self):
        """Restart game for all selected profiles that are currently running."""
        tree = self.app.lb
        selection = tree.selection()
        profiles_to_restart = []
        for item_id in selection:
            if item_id in self.item_map:
                profile = self.item_map[item_id]
                key = profile.cdKey
                if key and key in self.app.sessions.sessions:
                    profiles_to_restart.append(profile)
        
        for profile in profiles_to_restart:
            self.app.restart_game_for_profile(profile)

    def toggle_hotkey_on(self, prof: Profile):
        """Toggle hotkey_on for a profile (exclusive behavior)."""
        if getattr(self, 'service', None):
            self.service.set_hotkey_exclusive(prof)
        else:
            new_val = not prof.hotkey_on
            for p in self.app.profiles:
                p.hotkey_on = False
            prof.hotkey_on = new_val
            self.app.save_data()
        self.refresh_list()

    def on_middle_click(self, event):
        """Toggle selection of the clicked item on middle click (scroll wheel)."""
        tree = self.app.lb
        item_id = tree.identify_row(event.y)
        if not item_id:
            return

        # Don't allow selecting categories via middle click
        if item_id not in self.item_map:
            return

        current_selection = list(tree.selection())
        if item_id in current_selection:
            current_selection.remove(item_id)
        else:
            current_selection.append(item_id)
            
        tree.selection_set(current_selection)
        return "break"

    def on_select(self, event):
        """Handle selection in Treeview."""
        tree = self.app.lb
        selection = tree.selection()
        if not selection:
            return
            
        item_id = selection[0]
        
        if hasattr(self, '_hover_item_id') and self._hover_item_id == item_id:
             bbox = tree.bbox(item_id)
             if bbox:
                 self._show_inline_actions(item_id, bbox)

        # Update multiselection UI
        if len(selection) > 1:
            if hasattr(self.app, 'lbl_selected_count'):
                self.app.lbl_selected_count.config(text=f"Selected: {len(selection)}")
            if hasattr(self.app, 'btn_play'):
                self.app.btn_play.config(command=self.launch_selected)
            if hasattr(self.app, 'btn_restart'):
                self.app.btn_restart.config(command=self.restart_selected)
            if hasattr(self.app, 'btn_close'):
                self.app.btn_close.config(command=self.close_selected)
        else:
            if hasattr(self.app, 'lbl_selected_count'):
                self.app.lbl_selected_count.config(text="")
            if hasattr(self.app, 'btn_play'):
                self.app.btn_play.config(command=lambda: self.app.launch_game(self.item_map.get(item_id)))
            if hasattr(self.app, 'btn_restart'):
                self.app.btn_restart.config(command=self.app.restart_game)
            if hasattr(self.app, 'btn_close'):
                self.app.btn_close.config(command=self.app.close_game)

        # Check if it's a profile
        if item_id in self.item_map:
            profile = self.item_map[item_id]
            self.app.current_profile = profile
            
            # Switch server group/server based on profile
            try:
                profile_group = profile.server_group
                current_group = getattr(self.app, 'server_group', 'siala')
                
                # Switch group if needed
                if profile_group and profile_group != current_group:
                    if hasattr(self.app, 'server_groups'):
                        self.app.server_groups[current_group] = self.app.servers
                    
                    self.app.server_group = profile_group
                    self.app.servers = self.app.server_groups.get(profile_group, [])
                    
                    if hasattr(self.app, '_create_server_buttons'):
                        self.app._create_server_buttons()
                    
                    # Update Slayer visibility
                    if hasattr(self.app, 'status_bar_comp'):
                        self.app.status_bar_comp.set_slayer_visibility(profile_group != 'siala')
                    
                    # Update sidebar highlight
                    if hasattr(self.app, '_update_group_buttons'):
                        self.app._update_group_buttons()

                # Update info fields (right panel)
                self.update_info_fields(profile)

                # Set server
                profile_server = profile.server
                if profile_server:
                     server_names = [s.name for s in self.app.servers]
                     if profile_server in server_names:
                         self.app.server_var.set(profile_server)
                elif self.app.servers:
                     self.app.server_var.set(self.app.servers[0].name)

                if hasattr(self.app, '_update_server_button_styles'):
                    self.app._update_server_button_styles()
            except Exception as e:
                self.app.log_error("on_select_server_switch", e)
            
            # Enable buttons
            if hasattr(self.app, 'btn_launch'):
                self.app.btn_launch.configure(state="normal")
            if hasattr(self.app, 'btn_connect'):
                self.app.btn_connect.configure(state="normal")
            if hasattr(self.app, 'btn_edit_profile'):
               self.app.btn_edit_profile.configure(state="normal")
            if hasattr(self.app, 'btn_delete_profile_top'):
               self.app.btn_delete_profile_top.configure(state="normal")

    def on_category_expanded(self, event):
        """Handle category expansion in treeview."""
        tree = self.app.lb
        item_id = tree.focus()
        if item_id:
            tags = tree.item(item_id, "tags")
            if "category" in tags:
                cat_name = tree.item(item_id, "text")
                if cat_name in self.collapsed_categories:
                    self.collapsed_categories.discard(cat_name)
                    self.app.save_data()

    def on_category_collapsed(self, event):
        """Handle category collapse in treeview."""
        tree = self.app.lb
        item_id = tree.focus()
        if item_id:
            tags = tree.item(item_id, "tags")
            if "category" in tags:
                cat_name = tree.item(item_id, "text")
                if cat_name not in self.collapsed_categories:
                    self.collapsed_categories.add(cat_name)
                    self.app.save_data()

    def select_initial_profile(self):
        """Select the first available profile if none selected."""
        if not self.app.profiles:
            return
            
        tree = self.app.lb
        # Find first profile item
        for cat_id in tree.get_children():
            children = tree.get_children(cat_id)
            if children:
                first_profile_id = children[0]
                tree.selection_set(first_profile_id)
                tree.see(first_profile_id)
                self.on_select(None)
                return


    def update_info_fields(self, p: Profile):
        """Update the info panel fields from profile object."""
        def set_val(entry: tk.Entry, val: str):
            if not entry:
                return
            state = entry.cget("state")
            entry.configure(state="normal")
            entry.delete(0, tk.END)
            entry.insert(0, val)
            entry.configure(state=state)
            
        try:
            # Update header with profile name
            name = p.name or p.playerName
            if hasattr(self.app, 'header_lbl') and name:
                self.app.header_lbl.config(text=name)
            
            set_val(self.app.info_login, p.playerName)
            
            # Mask cdkey
            cdkey = p.cdKey
            if not self.app.show_key and cdkey:
                masked = cdkey[:4] + "*" * (len(cdkey) - 4) if len(cdkey) > 4 else "*"*len(cdkey)
                set_val(self.app.info_cdkey, masked)
            else:
                set_val(self.app.info_cdkey, cdkey)
        except Exception:
            pass

    # --- INLINE ACTIONS (hover over list) ---

    def on_profile_list_motion(self, event):
        """Show inline edit/delete buttons when hovering over a profile row."""
        tree = self.app.lb
        item_id = tree.identify_row(event.y)
        
        if not item_id:
            self._schedule_inline_hide()
            return

        tags = tree.item(item_id, "tags")
        if "profile" not in tags and "category" not in tags:
            self._schedule_inline_hide()
            return
            
        # Add hover tag to current row, remove from others
        for item in tree.tag_has("hover"):
            if item != item_id:
                current_tags = list(tree.item(item, "tags"))
                if "hover" in current_tags:
                    current_tags.remove("hover")
                    tree.item(item, tags=current_tags)
        if "hover" not in tags:
            current_tags = list(tags)
            current_tags.append("hover")
            tree.item(item_id, tags=current_tags)
            
        bbox = tree.bbox(item_id)
        if not bbox:
            self._schedule_inline_hide()
            return
            
        self._hover_item_id = item_id # Store item_id for Treeview
        self._show_inline_actions(item_id, bbox)

    def on_profile_list_leave(self, _event):
        """Mouse left the listbox."""
        self._schedule_inline_hide()
        
    def on_profile_list_scroll(self, _event):
        """List scrolled."""
        self.hide_inline_actions()

    def _show_inline_actions(self, idx: str, bbox: tuple[int, int, int, int] | None = None):
        """Create and place the floating frame with Edit/Delete buttons over the list item."""
        self._cancel_inline_hide()
        
        is_selected = self.app.lb.selection() and idx in self.app.lb.selection()
        
        if hasattr(self, '_last_inline_id') and self._last_inline_id == idx:
            if hasattr(self, '_last_inline_selected') and self._last_inline_selected == is_selected:
                if self._inline_frame and self._inline_frame.winfo_exists():
                    return
        
        self._last_inline_id = idx
        self._last_inline_selected = is_selected

        if self._inline_frame:
            try:
                self._inline_frame.destroy()
            except Exception:
                pass
        
        if not bbox:
            bbox = self.app.lb.bbox(idx)
            if not bbox:
                return

        x, y, w, h = bbox
        
        bg_color = COLORS["bg_panel"]
        is_category = "category" in self.app.lb.item(idx, "tags")

        self._inline_frame = tk.Frame(self.app.lb, bg=bg_color, height=h, relief="flat", bd=0)
        
        inner = tk.Frame(self._inline_frame, bg=bg_color)
        inner.pack(fill="both", expand=True, padx=4, pady=2)
        
        if is_category:
            cat_name = self.app.lb.item(idx, "text")
            btn_play = tk.Label(inner, text="▶", bg=bg_color, fg=COLORS["success"], font=("Segoe UI", 11), cursor="hand2", padx=4, pady=0)
            btn_play.pack(side="left", padx=(0, 2))
            btn_play.bind("<Button-1>", lambda e: self.launch_category(cat_name))
            bind_hover_effects(btn_play, bg_color, bg_color, btn_play.cget("fg"), COLORS["success_hover"])

            btn_up = tk.Label(inner, text="\uE74A", bg=bg_color, fg=COLORS["accent"], font=("Segoe Fluent Icons", 10), cursor="hand2", padx=4, pady=0)
            btn_up.pack(side="left", padx=(0, 2))
            btn_up.bind("<Button-1>", lambda e: self._inline_move_category(idx, -1))
            bind_hover_effects(btn_up, bg_color, bg_color, btn_up.cget("fg"), COLORS["accent_hover"])

            btn_down = tk.Label(inner, text="\uE74B", bg=bg_color, fg=COLORS["accent"], font=("Segoe Fluent Icons", 10), cursor="hand2", padx=4, pady=0)
            btn_down.pack(side="left", padx=(0, 2))
            btn_down.bind("<Button-1>", lambda e: self._inline_move_category(idx, 1))
            bind_hover_effects(btn_down, bg_color, bg_color, btn_down.cget("fg"), COLORS["accent_hover"])
            
            btn_width = 85
        else:
            profile_for_launch = self.item_map.get(idx)
            btn_play = tk.Label(inner, text="▶", bg=bg_color, fg=COLORS["success"], font=("Segoe UI", 11), cursor="hand2", padx=4, pady=0)
            btn_play.pack(side="left", padx=(0, 2))
            btn_play.bind("<Button-1>", lambda e, p=profile_for_launch: self.app.launch_game(p))
            bind_hover_effects(btn_play, bg_color, bg_color, btn_play.cget("fg"), COLORS["success_hover"])

            btn_restart = tk.Label(inner, text="\uE72C", bg=bg_color, fg=COLORS["accent"], font=("Segoe Fluent Icons", 10), cursor="hand2", padx=4, pady=0)
            btn_restart.pack(side="left", padx=(0, 2))
            btn_restart.bind("<Button-1>", lambda e: self._inline_restart_profile())
            bind_hover_effects(btn_restart, bg_color, bg_color, btn_restart.cget("fg"), COLORS["accent_hover"])
            
            btn_close = tk.Label(inner, text="\uE8BB", bg=bg_color, fg=COLORS["danger"], font=("Segoe Fluent Icons", 10), cursor="hand2", padx=4, pady=0)
            btn_close.pack(side="left", padx=(0, 2))
            btn_close.bind("<Button-1>", lambda e: self._inline_close_profile())
            bind_hover_effects(btn_close, bg_color, bg_color, btn_close.cget("fg"), COLORS["danger_hover"])
            
            btn_width = 85
        
        lb_w = self.app.lb.winfo_width()
        place_x = lb_w - btn_width
        if place_x < 0: place_x = 0
        
        self._inline_frame.place(x=place_x, y=y, width=btn_width, height=h)
        
        self._inline_frame.bind("<Enter>", lambda e: self._cancel_inline_hide())
        self._inline_frame.bind("<Leave>", lambda e: self._schedule_inline_hide())
        for child in self._inline_frame.winfo_children():
            child.bind("<Enter>", lambda e: self._cancel_inline_hide())
            child.bind("<Leave>", lambda e: self._schedule_inline_hide())
            for grandchild in child.winfo_children():
                grandchild.bind("<Enter>", lambda e: self._cancel_inline_hide())
                grandchild.bind("<Leave>", lambda e: self._schedule_inline_hide())

    def _inline_move_category(self, cat_id: str, direction: int):
        """Action when Move Up (-1) or Move Down (+1) is clicked on a category."""
        try:
            tree = self.app.lb
            category_name = tree.item(cat_id, "text")
            
            if not hasattr(self.app, "category_order"):
                self.app.category_order = []
                
            if category_name not in self.app.category_order:
                current_order = []
                for cid in tree.get_children(""):
                    current_order.append(tree.item(cid, "text"))
                self.app.category_order = current_order
                
            order_list = self.app.category_order
            if category_name in order_list:
                idx = order_list.index(category_name)
                new_idx = idx + direction
                if 0 <= new_idx < len(order_list):
                    order_list[idx], order_list[new_idx] = order_list[new_idx], order_list[idx]
                    self.app.save_data()
                    self.refresh_list()
        except Exception as e:
            logging.error(f"Error moving category: {e}")

    def hide_inline_actions(self):
        """Hide the inline action buttons."""
        if self._inline_frame:
            try:
                self._inline_frame.destroy()
            except Exception:
                pass
            self._inline_frame = None
        self._hover_item_id = None
        self._last_inline_id = None
        self._last_inline_selected = None
        
        try:
            tree = self.app.lb
            for item in tree.tag_has("hover"):
                current_tags = list(tree.item(item, "tags"))
                if "hover" in current_tags:
                    current_tags.remove("hover")
                    tree.item(item, tags=current_tags)
        except Exception:
            pass

    def _schedule_inline_hide(self, delay: int = 150):
        """Schedule hiding the inline actions."""
        self._cancel_inline_hide()
        self._inline_hide_job = self.app.root.after(delay, self.hide_inline_actions)

    def _cancel_inline_hide(self):
        """Cancel scheduled hide."""
        if self._inline_hide_job:
            self.app.root.after_cancel(self._inline_hide_job)
            self._inline_hide_job = None
            
    def _select_profile_by_id(self, item_id: str):
        """Helper to safely select a profile by Treeview item ID."""
        tree = self.app.lb
        if item_id and tree.exists(item_id):
            tree.selection_set(item_id)
            tree.focus(item_id)
            tree.see(item_id)
            self.on_select(None)

    def _inline_restart_profile(self):
        """Handle click on inline restart button."""
        if self._hover_item_id:
            self._select_profile_by_id(self._hover_item_id)
            self.app.restart_game()

    def _inline_close_profile(self):
        """Handle click on inline close button."""
        if self._hover_item_id:
            self._select_profile_by_id(self._hover_item_id)
            self.app.close_game()

    def on_drag_start(self, event):
        """Handle drag start on profile list."""
        tree = self.app.lb
        item_id = tree.identify_row(event.y)
        if not item_id:
            return
            
        tags = tree.item(item_id, "tags")
        if "category" in tags:
            self.app.drag_data = {
                "type": "category",
                "item_id": item_id,
                "data": tree.item(item_id, "text"),
                "start_y": event.y,
                "active": False
            }
        else:
            if item_id in self.item_map:
                profile = self.item_map[item_id]
                self.app.drag_data = {
                    "type": "profile",
                    "item_id": item_id,
                    "data": profile,
                    "start_y": event.y,
                    "active": False
                }

    def on_drag_motion(self, event):
        """Handle drag motion to distinguish click from drag."""
        drag_data = getattr(self.app, 'drag_data', {})
        if not drag_data:
            return
        # If moved by more than 5 pixels vertically, consider it an active drag
        if abs(event.y - drag_data.get("start_y", event.y)) > 5:
            drag_data["active"] = True

    def on_drag_drop(self, event):
        """Handle drag drop to reorder profiles and categories."""
        drag_data = getattr(self.app, 'drag_data', {})
        if not drag_data or not drag_data.get("active", False):
            self.app.drag_data = {}
            return

        tree = self.app.lb
        target_id = tree.identify_row(event.y)
        if not target_id:
            self.app.drag_data = {}
            return
            
        if "type" not in drag_data:
            self.app.drag_data = {}
            return

        drag_type = drag_data["type"]
        drag_item_id = drag_data["item_id"]
        if drag_item_id == target_id:
            self.app.drag_data = {}
            return

        target_tags = tree.item(target_id, "tags")
        target_parent = tree.parent(target_id)
        
        if drag_type == "profile":
            profile = drag_data["data"]
            old_cat = profile.category
            
            target_category = None
            insert_index = 0
            
            if "category" in target_tags:
                target_category = tree.item(target_id, "text")
                insert_index = 0 
            elif "profile" in target_tags:
                if target_parent:
                    target_category = tree.item(target_parent, "text")
                    insert_index = tree.index(target_id)
            
            if target_category:
                if profile.category != target_category:
                    profile.category = target_category
                
                cat_id = None
                for child in tree.get_children():
                    if tree.item(child, "text") == target_category:
                        cat_id = child
                        break
                
                if cat_id:
                    children = list(tree.get_children(cat_id))
                    if drag_item_id in children:
                        children.remove(drag_item_id)
                    if insert_index > len(children):
                        insert_index = len(children)
                    children.insert(insert_index, drag_item_id)
                    
                    for idx, child_id in enumerate(children):
                        if child_id in self.item_map:
                            p = self.item_map[child_id]
                            p.order = idx
                            
                self.app.save_data()
                self.refresh_list()
                return

        self.app.drag_data = {}
