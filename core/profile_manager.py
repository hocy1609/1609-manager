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
from typing import Dict, List, Optional, Any

from ui.ui_base import COLORS, ModernButton, bind_hover_effects
from core.models import Profile
from ui.dialogs import EditDialog


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
        self.collapsed_categories = set()
        
        # State for inline actions
        self._hover_idx = -1
        self._inline_frame = None
        self._inline_hide_job = None
        
        self.item_map = {}  # Map item_id -> profile object
        
    def move_profile_to_group(self, profile, target_group):
        """Move profile to another server group and refresh list."""
        if isinstance(profile, dict):
            profile["server_group"] = target_group
        else:
            profile.server_group = target_group
        
        self.app.save_data()
        self.refresh_list()
        
    def refresh_list(self):
        """Refreshes the profile list (Treeview) with categories."""
        if not hasattr(self.app, 'lb'):
            return

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
            font=("Segoe UI", 10),
            foreground=COLORS["fg_text"]
        )
        
        # Get user-defined category order or build from existing categories
        # Get user-defined category order or build from existing categories
        category_order = getattr(self.app, 'category_order', [])
        
        # Collect all existing categories from profiles
        existing_cats = set()
        for p in self.app.profiles:
            existing_cats.add(_get_attr(p, "category", "General"))
        
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
            cat = _get_attr(p, "category", "General")
            order = _get_attr(p, "order", 0)
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
            pg = _get_attr(p, "server_group", "siala")
            if pg == current_group:
                filtered_profiles.append(p)
        
        # Insert into Treeview
        for cat in ordered_cats:
            # Find profiles in this category AND server group
            cat_profiles = [p for p in filtered_profiles if _get_attr(p, "category", "General") == cat]
            
            if not cat_profiles:
                continue

            # Create category node
            cat_id = tree.insert("", "end", text=cat, open=True, tags=("category",))
            
            for i, p in enumerate(cat_profiles):
                # Prepare display text
                name = _get_attr(p, "name")
                if not name:
                    name = f"Profile {self.app.profiles.index(p) + 1}"
                
                char = _get_attr(p, "characterName", "")
                
                display_text = name
                if char:
                    display_text += f" ({char})"
                
                # Apply 'alt' tag to odd rows for striping, combined with 'profile' tag
                profile_tags = ["profile"]
                if i % 2 == 1:
                    profile_tags.append("alt")
                
                # Insert profile node
                p_id = tree.insert(cat_id, "end", text=display_text, tags=tuple(profile_tags))
                self.item_map[p_id] = p
                
                # Restore selection if it matches current profile
                if self.app.current_profile == p:
                    tree.selection_set(p_id)
                    tree.see(p_id)


            
    def get_unique_categories(self) -> List[str]:
        """Return a sorted list of unique profile categories, with 'General' first."""
        cats = set()
        for p in self.app.profiles:
            cats.add(_get_attr(p, "category", "General"))
        
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
            # Create new profile dict
            new_p = {
                "name": data.get("name", "New Profile"),
                "desc": data.get("desc", ""),
                "playerName": data.get("playerName", ""),
                "cdKey": data.get("cdKey", ""),
                "server": data.get("server", ""),
                "password": data.get("password", ""),
                "category": data.get("category", "General"),
                "launchArgs": data.get("launchArgs", ""),
                "is_crafter": bool(data.get("is_crafter", False)),
                "server_group": self.app.server_group if hasattr(self.app, 'server_group') else "siala",
            }
            self.app.profiles.append(new_p)
            self.app.save_data()
            
            # Select the new profile
            self.app.current_profile = new_p
            self.refresh_list()
            # on_select will be triggered by user interaction or we can force update info panel?
            # refresh_list restores selection, but doesn't trigger <<TreeviewSelect>> event automatically
            # So we manually update the info panel
            self.update_info_fields(new_p)
            self.app.on_select(None)

        EditDialog(
            self.app.root,
            title="Add Profile",
            categories=cats,
            on_save=on_save,
            server_list=[s["name"] for s in self.app.servers],
            is_new=True,
            saved_keys=getattr(self.app, 'saved_keys', [])
        )

    def edit_profile(self):
        """Open the Edit dialog for the currently selected profile."""
        if not self.app.current_profile:
            return

        cats = self.get_unique_categories()
        old_p = self.app.current_profile

        def on_save(data: dict):
            # Update existing profile
            old_p["name"] = data.get("name", old_p.get("name", ""))
            old_p["desc"] = data.get("desc", old_p.get("desc", ""))
            old_p["playerName"] = data.get("playerName", old_p.get("playerName", ""))
            old_p["cdKey"] = data.get("cdKey", old_p.get("cdKey", ""))
            old_p["server"] = data.get("server", old_p.get("server", ""))
            old_p["password"] = data.get("password", old_p.get("password", ""))
            old_p["category"] = data.get("category", "General")
            old_p["launchArgs"] = data.get("launchArgs", "")
            old_p["is_crafter"] = bool(data.get("is_crafter", False))
            
            self.app.save_data()
            # Ensure current profile remains selected
            self.app.current_profile = old_p
            self.refresh_list()
            
            self.update_info_fields(old_p)
            self.app.on_select(None)

        EditDialog(
            self.app.root,
            title="Edit Profile",
            profile_data=old_p,
            categories=cats,
            on_save=on_save,
            server_list=[s["name"] for s in self.app.servers],
            saved_keys=getattr(self.app, 'saved_keys', [])
        )

    def delete_profile(self):
        """Delete the currently selected profile."""
        if not self.app.current_profile:
            return
        
        name = self.app.current_profile.get("name", "Unknown")
        if messagebox.askyesno("Delete Profile", f"Are you sure you want to delete '{name}'?"):
            if self.app.current_profile in self.app.profiles:
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
            changed = False
            for p in self.app.profiles:
                if _get_attr(p, "category") == old_name:
                    p["category"] = new_name
                    changed = True
            
            if changed:
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
        # Find all profiles in this category AND current server group (implicit, since we only see current group)
        # Actually, if we move a category, we likely want to move ALL profiles in that category regardless of their current group?
        # OR just the ones visible? User probably expects visible ones if they are filtered.
        # But wait, if I move "General" to Cormyr, do I want profiles in "General" that are already in Cormyr to stay? Yes.
        # Do I want profiles in "General" that are in `siala` (current) to move to `cormyr`? Yes.
        
        current_group = getattr(self.app, 'server_group', 'siala')
        count = 0
        for p in self.app.profiles:
            p_cat = _get_attr(p, "category", "General")
            p_group = _get_attr(p, "server_group", "siala")
            
            if p_cat == category_name and p_group == current_group:
                _set_attr(p, "server_group", target_group)
                count += 1
        
        if count > 0:
            self.app.save_data()
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
            
            menu = tk.Menu(self.app.root, tearoff=0, bg=COLORS.get("bg_menu", COLORS["bg_panel"]), fg=COLORS["fg_text"])
            menu.add_command(label="Edit", command=lambda: self.edit_profile()) # Use edit_profile without args as it uses current_profile
            
            # Move to other group
            menu.add_command(
                label=f"Move to {target_name}", 
                command=lambda: self.move_profile_to_group(prof, target_group)
            )
            
            menu.add_separator()
            menu.add_command(label="Delete", command=lambda: self.delete_profile()) # Use delete_profile without args
            menu.add_separator()
            
            # Launch options
            menu.add_command(label="Launch", command=self.app.launch_game)
            
            # Crafter toggle
            is_crafter = bool(_get_attr(prof, "is_crafter", False))
            lbl = "Unmark as Crafter" if is_crafter else "Mark as Crafter"
            menu.add_command(label=lbl, command=self.app.toggle_crafter)
            
            menu.post(event.x_root, event.y_root)

    def on_select(self, event):
        """Handle selection in Treeview."""
        tree = self.app.lb
        selection = tree.selection()
        if not selection:
            return
            
        item_id = selection[0]
        # Check if it's a profile
        if item_id in self.item_map:
            profile = self.item_map[item_id]
            self.app.current_profile = profile
            self.app.current_profile = profile
            # self.app.update_info_panel() - REMOVED: Method does not exist, updates handled by update_info_fields
            
            # Switch server group/server based on profile
            try:
                profile_group = _get_attr(profile, "server_group", "siala")
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

                    if hasattr(self.app, 'server_manager'):
                         self.app.root.after(100, self.app.server_manager.ping_all_servers)

                # Update info fields (right panel)
                self.update_info_fields(profile)


                # Set server
                profile_server = _get_attr(profile, "server", "")
                if profile_server:
                     server_names = [s["name"] for s in self.app.servers]
                     if profile_server in server_names:
                         self.app.server_var.set(profile_server)
                elif self.app.servers:
                     self.app.server_var.set(self.app.servers[0]["name"])
                
                if hasattr(self.app, 'check_server_status'):
                    self.app.check_server_status()
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
        else:
            # Category selected - treat as deselection or just ignore?
            pass

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
                # Manually trigger on_select logic
                # We can just call on_select with None, but better to be explicit
                # But wait, we need to ensure selection is set before calling on_select if on_select reads selection
                self.on_select(None)
                return


    def update_info_fields(self, p: dict):
        """Update the info panel fields from profile dict."""
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
            name = _get_attr(p, "name", "") or _get_attr(p, "playerName", "")
            if hasattr(self.app, 'header_lbl') and name:
                self.app.header_lbl.config(text=name)
            
            set_val(self.app.info_login, _get_attr(p, "playerName", ""))
            
            # Mask cdkey
            cdkey = _get_attr(p, "cdKey", "")
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
        # Disabled for Treeview migration (requires new implementation)
        return

    def on_profile_list_leave(self, _event):
        """Mouse left the listbox."""
        self._schedule_inline_hide()
        
    def on_profile_list_scroll(self, _event):
        """List scrolled."""
        self.hide_inline_actions()

    def _show_inline_actions(self, idx: int, bbox: tuple[int, int, int, int] | None = None):
        """Create and place the floating frame with Edit/Delete buttons over the list item."""
        self._cancel_inline_hide()
        
        if self._inline_frame:
            self._inline_frame.destroy()
        
        if not bbox:
            bbox = self.app.lb.bbox(idx)
            if not bbox:
                return

        x, y, w, h = bbox
        
        # Create a frame on top of the listbox with proper background
        bg_color = COLORS["bg_input"]
        self._inline_frame = tk.Frame(self.app.lb, bg=bg_color, height=h, relief="flat", bd=0)
        
        # Inner container for proper padding
        inner = tk.Frame(self._inline_frame, bg=bg_color)
        inner.pack(fill="both", expand=True, padx=4, pady=2)
        
        # Edit btn
        btn_edit = tk.Label(
            inner, text="✎", bg=bg_color, 
            fg=COLORS["accent"], font=("Segoe UI", 11), cursor="hand2",
            padx=4, pady=0
        )
        btn_edit.pack(side="left", padx=(0, 2))
        btn_edit.bind("<Button-1>", lambda e: self._inline_edit_profile())
        bind_hover_effects(btn_edit, bg_color, COLORS["bg_panel"], COLORS["accent"], COLORS["success"])
        
        # Delete btn
        btn_del = tk.Label(
            inner, text="✖", bg=bg_color, 
            fg=COLORS["danger"], font=("Segoe UI", 11), cursor="hand2",
            padx=4, pady=0
        )
        btn_del.pack(side="left", padx=(0, 2))
        btn_del.bind("<Button-1>", lambda e: self._inline_delete_profile())
        bind_hover_effects(btn_del, bg_color, COLORS["bg_panel"], COLORS["danger"], COLORS["danger_hover"])
        
        # Calculate position - place at right edge
        btn_width = 60
        lb_w = self.app.lb.winfo_width()
        place_x = lb_w - btn_width - 4
        
        if place_x < 0: 
            place_x = 0
        
        self._inline_frame.place(x=place_x, y=y, width=btn_width, height=h)
        
        # Bind enter/leave for the frame too, so it doesn't disappear when we move mouse over it
        self._inline_frame.bind("<Enter>", lambda e: self._cancel_inline_hide())
        self._inline_frame.bind("<Leave>", lambda e: self._schedule_inline_hide())

    def hide_inline_actions(self):
        """Hide the inline action buttons."""
        if self._inline_frame:
            self._inline_frame.destroy()
            self._inline_frame = None
        self._hover_idx = -1

    def _schedule_inline_hide(self, delay: int = 150):
        """Schedule hiding the inline actions."""
        self._cancel_inline_hide()
        self._inline_hide_job = self.app.root.after(delay, self.hide_inline_actions)

    def _cancel_inline_hide(self):
        """Cancel scheduled hide."""
        if self._inline_hide_job:
            self.app.root.after_cancel(self._inline_hide_job)
            self._inline_hide_job = None
            
    def _select_profile_by_index(self, idx: int):
        """Helper to safely select a profile by index."""
        if 0 <= idx < self.app.lb.size():
            self.app.lb.selection_clear(0, tk.END)
            self.app.lb.selection_set(idx)
            self.app.lb.activate(idx)
            self.app.on_select(None)

    def _inline_edit_profile(self):
        """Handle click on inline edit button."""
        if self._hover_idx != -1:
            self._select_profile_by_index(self._hover_idx)
            self.edit_profile()

    def _inline_delete_profile(self):
        """Handle click on inline delete button."""
        if self._hover_idx != -1:
            self._select_profile_by_index(self._hover_idx)
            self.delete_profile()

    def on_drag_start(self, event):
        """Handle drag start on profile list."""
        tree = self.app.lb
        item_id = tree.identify_row(event.y)
        if not item_id:
            return
            
        # Determine what we are dragging
        tags = tree.item(item_id, "tags")
        if "category" in tags:
            self.app.drag_data = {
                "type": "category",
                "item_id": item_id,
                "data": tree.item(item_id, "text")
            }
        else:
            if item_id in self.item_map:
                profile = self.item_map[item_id]
                self.app.drag_data = {
                    "type": "profile",
                    "item_id": item_id,
                    "data": profile
                }
            else:
                 return

    def on_drag_drop(self, event):
        """Handle drag drop to reorder profiles and categories."""
        tree = self.app.lb
        target_id = tree.identify_row(event.y)
        if not target_id:
            return
            
        drag_data = self.app.drag_data
        if not drag_data or "type" not in drag_data:
            return

        drag_type = drag_data["type"]
        drag_item_id = drag_data["item_id"]
        
        if drag_item_id == target_id:
             return

        # Handle moving logic
        
        # Determine target region
        target_tags = tree.item(target_id, "tags")
        target_parent = tree.parent(target_id)
        
        # Profile Drop Logic
        if drag_type == "profile":
            # Profile being dragged
            profile = drag_data["data"]
            old_cat = _get_attr(profile, "category", "General")
            
            # Identify target category and index
            target_category = None
            insert_index = 0
            
            if "category" in target_tags:
                # Dropped ON a category header -> Append to end of this category or start?
                # Let's append to end for simplicity, or insert at top (index 0)
                target_category = tree.item(target_id, "text")
                insert_index = 0 # Insert at top
            elif "profile" in target_tags:
                # Dropped ON another profile -> Insert before or after?
                # Usually drop "on" means insert before or swap. Let's say insert before.
                if target_parent:
                    target_category = tree.item(target_parent, "text")
                    target_index = tree.index(target_id)
                    insert_index = target_index
            
            if target_category:
                # 1. Update Category if changed
                current_cat = _get_attr(profile, "category", "General")
                if current_cat != target_category:
                    _set_attr(profile, "category", target_category)
                
                # 2. Reorder within the target category
                # Get all profiles in target category from the app.profiles list
                # We need to respect the server filter? No, reordering should affect global state if possible,
                # but we are only viewing filtered list.
                # Actually, `tree.get_children(cat_id)` gives us the visual order.
                # We should construct the new order based on visual state.
                
                # Find the category ID in tree
                cat_id = None
                for child in tree.get_children():
                    if tree.item(child, "text") == target_category:
                        cat_id = child
                        break
                
                if cat_id:
                    # Get current visual children (items)
                    children = list(tree.get_children(cat_id))
                    
                    # Remove dragged item from its old position in visual list if it was there
                    if drag_item_id in children:
                        children.remove(drag_item_id)
                    
                    # Insert at new index
                    # Safe guard index
                    if insert_index > len(children):
                        insert_index = len(children)
                    
                    children.insert(insert_index, drag_item_id)
                    
                    # Now update the 'order' attribute of profiles based on this new visual order
                    for idx, child_id in enumerate(children):
                        if child_id in self.item_map:
                            p = self.item_map[child_id]
                            _set_attr(p, "order", idx)
                            
                self.app.save_data()
                self.refresh_list()
                
                # Restore selection
                # We need to find the new ID for this profile since refresh_list recreates items
                # But we can rely on on_select logic to handle current_profile if it matches
                return

        # Category Reordering Logic (omitted for now as requested focus is on profile reordering)

        # Clear drag data
        self.app.drag_data = {}
        
    def _handle_category_drop(self, old_idx, new_idx, dragged_cat):
        """Handle dropping a category header to reorder categories."""
        if not dragged_cat:
            return
        
        # Find target category (scan upward from new_idx)
        target_cat = None
        for i in range(min(new_idx, len(self.app.view_map) - 1), -1, -1):
            if self.app.view_map[i]["type"] == "header":
                target_cat = self.app.view_map[i]["data"]
                break
        
        if not target_cat or target_cat == dragged_cat:
            return
        
        # Get current category order
        category_order = getattr(self.app, 'category_order', [])
        if dragged_cat not in category_order or target_cat not in category_order:
            return
        
        # Remove dragged category from list
        category_order = [c for c in category_order if c != dragged_cat]
        
        # Insert at new position (before or after target based on direction)
        target_idx = category_order.index(target_cat)
        if new_idx > old_idx:
            # Moving down - insert after target
            category_order.insert(target_idx + 1, dragged_cat)
        else:
            # Moving up - insert before target
            category_order.insert(target_idx, dragged_cat)
        
        self.app.category_order = category_order
        self.app.save_data()
        self.refresh_list()
    
    def _handle_profile_drop(self, old_idx, new_idx, profile_data):
        """Handle dropping a profile to reorder or change category."""
        if not profile_data:
            return
        
        # Find target category by scanning upward from new_idx
        target_cat = "General"
        for i in range(min(new_idx, len(self.app.view_map) - 1), -1, -1):
            if self.app.view_map[i]["type"] == "header":
                target_cat = self.app.view_map[i]["data"]
                break
        
        old_cat = _get_attr(profile_data, "category", "General")
        
        # Get all profiles in target category and their current order
        target_profiles = [
            p for p in self.app.profiles 
            if _get_attr(p, "category", "General") == target_cat and p is not profile_data
        ]
        target_profiles.sort(key=lambda p: _get_attr(p, "order", 0))
        
        # Calculate new order value based on drop position
        # Find position within category
        profiles_before = 0
        for i in range(new_idx - 1, -1, -1):
            item = self.app.view_map[i]
            if item["type"] == "header":
                break
            if item["type"] == "profile" and item["data"] is not profile_data:
                if _get_attr(item["data"], "category", "General") == target_cat:
                    profiles_before += 1
        
        # Update category if changed
        _set_attr(profile_data, "category", target_cat)
        
        # Insert at the right position and recalculate order for all profiles in category
        target_profiles.insert(profiles_before, profile_data)
        
        # Reassign order values
        for i, p in enumerate(target_profiles):
            _set_attr(p, "order", i)
        
        # If category changed, recalculate order in old category too
        if old_cat != target_cat:
            old_cat_profiles = [
                p for p in self.app.profiles 
                if _get_attr(p, "category", "General") == old_cat
            ]
            old_cat_profiles.sort(key=lambda p: _get_attr(p, "order", 0))
            for i, p in enumerate(old_cat_profiles):
                _set_attr(p, "order", i)
        
        self.app.save_data()
        self.refresh_list()

