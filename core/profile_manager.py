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
        
    def refresh_list(self):
        """Refreshes the profile listbox with categories."""
        if not hasattr(self.app, 'lb'):
            return

        self.app.lb.delete(0, tk.END)
        self.app.view_map = []
        
        # Determine categories
        if not self.app.profiles:
            pass

        # Sort profiles by category then name
        def sort_key(p):
            cat = p.get("category", "General")
            name = p.get("name", "")
            is_general = (cat == "General")
            return (not is_general, cat, name)

        sorted_profiles = sorted(self.app.profiles, key=sort_key)
        
        # Pre-calculate active cdkeys for O(1) lookup
        active_cdkeys = set()
        if hasattr(self.app, 'sessions') and self.app.sessions:
            for key in self.app.sessions.sessions.keys():
                # key format: "player_name::cdkey"
                parts = key.split("::")
                if len(parts) > 1:
                    active_cdkeys.add(parts[-1])

        current_cat = None
        
        for p in sorted_profiles:
            cat = p.get("category", "General")
            if cat != current_cat:
                # Add separator before category (except first)
                if current_cat is not None:
                    self.app.lb.insert(tk.END, "─" * 30)
                    self.app.lb.itemconfig(tk.END, {
                        'bg': COLORS["bg_sidebar"], 
                        'fg': COLORS["border"], 
                        'selectbackground': COLORS["bg_sidebar"], 
                        'selectforeground': COLORS["border"]
                    })
                    self.app.view_map.append({"type": "separator", "data": None})
                
                # Add category header with bold appearance
                is_collapsed = cat in self.collapsed_categories
                prefix = "▸" if is_collapsed else "▾"
                self.app.lb.insert(tk.END, f"{prefix} {cat.upper()}")
                self.app.lb.itemconfig(tk.END, {
                    'bg': COLORS["bg_input"], 
                    'fg': COLORS["accent"], 
                    'selectbackground': COLORS["bg_input"], 
                    'selectforeground': COLORS["accent"]
                })
                self.app.view_map.append({"type": "header", "data": cat})
                current_cat = cat
            
            # Skip if category is collapsed
            if current_cat in self.collapsed_categories:
                continue
            
            # Add profile item
            name = p.get('name', '???')
            
            # Check if running using pre-calculated set
            cdkey = p.get('cdKey')
            is_running = bool(cdkey and cdkey in active_cdkeys)
            
            display_text = f"  {name}" 
            if is_running:
                display_text += "  (Running)"
            
            # Check crafter
            if p.get("is_crafter", False):
                display_text += "  🔨"

            self.app.lb.insert(tk.END, display_text)
            
            # Highlight running
            if is_running:
                 self.app.lb.itemconfig(tk.END, {'fg': COLORS["success"]})
            elif p.get("is_crafter", False):
                 self.app.lb.itemconfig(tk.END, {'fg': COLORS["accent"]})
            else:
                 self.app.lb.itemconfig(tk.END, {'fg': COLORS["fg_text"]})

            self.app.view_map.append({"type": "profile", "data": p})
            
    def get_unique_categories(self) -> List[str]:
        """Return a sorted list of unique profile categories, with 'General' first."""
        cats = set()
        for p in self.app.profiles:
            cats.add(p.get("category", "General"))
        
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
            }
            self.app.profiles.append(new_p)
            self.app.save_data()
            self.refresh_list()
            # Select the new profile
            # We need to find its index in view_map
            for idx, item in enumerate(self.app.view_map):
                if item.get("data") == new_p:
                    self.app.lb.selection_clear(0, tk.END)
                    self.app.lb.selection_set(idx)
                    self.app.lb.activate(idx)
                    self.app.on_select(None)
                    self.app.lb.see(idx)
                    break

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
            self.refresh_list()
            
            # Re-select
            for idx, item in enumerate(self.app.view_map):
                if item.get("data") == old_p:
                    self.app.lb.selection_clear(0, tk.END)
                    self.app.lb.selection_set(idx)
                    self.app.lb.activate(idx)
                    self.app.on_select(None)
                    break

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
                if p.get("category") == old_name:
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

    def show_profile_menu(self, event):
        """Show context menu for profiles."""
        idx = self.app.lb.nearest(event.y)
        if idx < 0 or idx >= len(self.app.view_map):
            return

        # Select the item under cursor
        self.app.lb.selection_clear(0, tk.END)
        self.app.lb.selection_set(idx)
        self.app.lb.activate(idx)
        self.app.on_select(None)
        
        item = self.app.view_map[idx]
        if item["type"] == "header":
            # Menu for category
            cat_name = item["data"]
            menu = tk.Menu(self.app.root, tearoff=0, bg=COLORS["bg_menu"], fg=COLORS["fg_text"])
            menu.add_command(label="Rename Category", command=lambda: self.rename_category(cat_name))
            menu.post(event.x_root, event.y_root)
        else:
            # Menu for profile
            menu = tk.Menu(self.app.root, tearoff=0, bg=COLORS["bg_menu"], fg=COLORS["fg_text"])
            menu.add_command(label="Edit", command=self.edit_profile)
            menu.add_command(label="Delete", command=self.delete_profile)
            menu.add_separator()
            
            # Launch options
            menu.add_command(label="Launch", command=self.app.launch_game)
            
            # Crafter toggle
            prof = item["data"]
            is_crafter = bool(prof.get("is_crafter", False))
            lbl = "Unmark as Crafter" if is_crafter else "Mark as Crafter"
            menu.add_command(label=lbl, command=self.app.toggle_crafter)
            
            menu.post(event.x_root, event.y_root)

    def on_select(self, _):
        """Handle profile selection."""
        try:
            sel = self.app.lb.curselection()
            if not sel:
                # Nothing selected
                self.app.current_profile = None
                try:
                    self.app.header_lbl.config(text="Select Profile")
                    self.app.cat_lbl.config(text="")
                    self.update_info_fields({})
                except Exception:
                    pass
                try:
                    self.app.update_launch_buttons()
                except Exception:
                    pass
                # Disable edit/delete when no selection
                try:
                    self.app.btn_edit_profile.configure(state="disabled")
                    self.app.btn_delete_profile_top.configure(state="disabled")
                except Exception:
                    pass
                return

            idx = int(sel[0])
            if idx < 0 or idx >= len(self.app.view_map):
                return

            item = self.app.view_map[idx]
            if item.get("type") == "header":
                # Clear selection as headers aren't selectable profiles
                self.app.lb.selection_clear(0, tk.END)
                
                # Show category but no profile selected
                self.app.current_profile = None
                try:
                    self.app.header_lbl.config(text="Select Profile")
                    self.app.cat_lbl.config(text=item.get("data", ""))
                    self.update_info_fields({})
                except Exception:
                    pass
                try:
                    self.app.update_launch_buttons()
                except Exception:
                    pass
                try:
                    self.app.btn_edit_profile.configure(state="disabled")
                    self.app.btn_delete_profile_top.configure(state="disabled")
                except Exception:
                    pass
                return

            # Profile selected
            prof = item.get("data")
            self.app.current_profile = prof
            try:
                self.app.header_lbl.config(text=prof.get("name", ""))
                self.app.cat_lbl.config(text=prof.get("category", ""))
                self.update_info_fields(prof)
            except Exception:
                pass
            # Load server binding from profile
            try:
                # Switch server group if profile has a different group
                profile_group = prof.get("server_group", "siala")
                if profile_group and profile_group != getattr(self.app, 'server_group', 'siala'):
                    # Save current group's servers
                    if hasattr(self.app, 'server_groups') and hasattr(self.app, 'server_group'):
                        self.app.server_groups[self.app.server_group] = self.app.servers
                    # Switch to profile's group
                    self.app.server_group = profile_group
                    self.app.servers = self.app.server_groups.get(profile_group, [])
                    # Update group button highlighting
                    if hasattr(self.app, '_update_group_buttons'):
                        self.app._update_group_buttons()
                    # Recreate server buttons
                    if hasattr(self.app, '_create_server_buttons'):
                        self.app._create_server_buttons()
                    # Trigger ping for new servers
                    self.app.root.after(100, self.app.server_manager.ping_all_servers)
                
                # Set server from profile
                profile_server = prof.get("server", "")
                if profile_server and profile_server in [s["name"] for s in self.app.servers]:
                    self.app.server_var.set(profile_server)
                elif self.app.servers:
                    self.app.server_var.set(self.app.servers[0]["name"])
                    
                self.app.check_server_status()
                # Update server button highlighting
                if hasattr(self.app, '_update_server_button_styles'):
                    self.app._update_server_button_styles()
            except Exception:
                pass
            try:
                self.app.update_launch_buttons()
            except Exception:
                pass
            # Enable edit/delete for selected profile
            try:
                self.app.btn_edit_profile.configure(state="normal")
                self.app.btn_delete_profile_top.configure(state="normal")
            except Exception:
                pass
        except Exception as e:
            self.app.log_error("on_select", e)

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
            set_val(self.app.info_login, p.get("playerName", ""))
            
            # Mask cdkey
            cdkey = p.get("cdKey", "")
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
        try:
            idx = self.app.lb.nearest(event.y)
            # If mouse is outside the items (e.g. empty space at bottom), nearest returns last item
            # Check bounding box
            bbox = self.app.lb.bbox(idx)
            if not bbox:
                self.hide_inline_actions()
                return
            
            y_offset = event.y - bbox[1]
            if y_offset < 0 or y_offset > bbox[3]:
                self.hide_inline_actions()
                return

            if idx == self._hover_idx:
                return  # already showing for this item

            # Check if it's a profile (not header)
            if idx < 0 or idx >= len(self.app.view_map):
                self.hide_inline_actions()
                return

            item = self.app.view_map[idx]
            if item.get("type") != "profile":
                self.hide_inline_actions()
                return

            # It's a profile, show buttons
            self._hover_idx = idx
            self._show_inline_actions(idx, bbox)
            
        except Exception:
            pass

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
        
        # Create a frame on top of the listbox
        # We put it inside listbox? No, place it relative to listbox
        self._inline_frame = tk.Frame(self.app.lb, bg=COLORS["bg_sidebar"], height=h)
        
        # Edit btn
        btn_edit = tk.Label(
            self._inline_frame, text="✎", bg=COLORS["bg_sidebar"], 
            fg=COLORS["fg_dim"], font=("Segoe UI", 10), cursor="hand2"
        )
        btn_edit.pack(side="right", padx=2)
        btn_edit.bind("<Button-1>", lambda e: self._inline_edit_profile())
        bind_hover_effects(btn_edit, COLORS["bg_sidebar"], COLORS["accent"], COLORS["fg_dim"])
        
        # Delete btn
        btn_del = tk.Label(
            self._inline_frame, text="✖", bg=COLORS["bg_sidebar"], 
            fg=COLORS["fg_dim"], font=("Segoe UI", 10), cursor="hand2"
        )
        btn_del.pack(side="right", padx=2)
        btn_del.bind("<Button-1>", lambda e: self._inline_delete_profile())
        bind_hover_effects(btn_del, COLORS["bg_sidebar"], COLORS["danger"], COLORS["fg_dim"])
        
        # Place it at the right edge of the listbox
        req_w = 54 
        lb_w = self.app.lb.winfo_width()
        place_x = lb_w - req_w - 6 # Leave room for visual scrollbar / padding
        
        if place_x < 0: place_x = 0
        
        self._inline_frame.place(x=place_x, y=y, width=req_w, height=h)
        
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
        idx = self.app.lb.nearest(event.y)
        if idx < 0 or idx >= len(self.app.view_map):
            return
        if self.app.view_map[idx]["type"] == "header":
            # Toggle category on click (since drag is disabled for headers)
            self.toggle_category(self.app.view_map[idx]["data"])
            self.app.lb.selection_clear(0, tk.END)
            return "break"
        self.app.drag_data["index"] = idx
        self.app.on_select(None)
    
    def on_drag_drop(self, event):
        """Handle drag drop to reorder profile categories."""
        old_idx = self.app.drag_data.get("index")
        if old_idx is None:
            return

        new_idx = self.app.lb.nearest(event.y)
        if new_idx == old_idx:
            return

        target_cat = "General"
        # Find category of target index
        # Scan upwards from new_idx
        start_scan = new_idx
        if start_scan >= len(self.app.view_map):
            start_scan = len(self.app.view_map) - 1
            
        for i in range(start_scan, -1, -1):
            if i < len(self.app.view_map) and self.app.view_map[i]["type"] == "header":
                target_cat = self.app.view_map[i]["data"]
                break
        
        if old_idx < len(self.app.view_map):
            profile_data = self.app.view_map[old_idx]["data"]
            if profile_data:
                profile_data["category"] = target_cat
                self.app.save_data()
                self.refresh_list()
        
        self.app.drag_data["index"] = None
