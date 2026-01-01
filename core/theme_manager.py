"""
Theme Management for NWN Manager.

This module handles all theme-related operations including:
- Applying themes across the application
- Updating widget colors recursively
- Rebuilding screens on theme change
"""

import tkinter as tk
from ui.ui_base import COLORS


class ThemeManager:
    """
    Manages theme application and updates across the NWN Manager application.
    
    Takes a reference to the main app to access its widgets and state.
    """
    
    def __init__(self, app):
        """
        Initialize the ThemeManager.
        
        Args:
            app: Reference to the NWNManagerApp instance
        """
        self.app = app
    
    def apply_theme(self):
        """Reapply current theme across all widgets for smoother live switching."""
        try:
            import ui.ui_base as _uib
            _uib.set_theme(self.app.theme, root=self.app.root)
        except Exception:
            pass
        
        # Update all Canvas widgets (ToggleSwitches, etc.)
        self._update_canvas_widgets(self.app.root)
        
        # Update root background
        try:
            self.app.root.configure(bg=COLORS.get('bg_root'))
        except Exception:
            pass
        
        # Update main content frame
        try:
            if hasattr(self.app, 'content_frame') and self.app.content_frame:
                self.app.content_frame.configure(bg=COLORS.get('bg_root'))
        except Exception:
            pass
        
        # Update sidebar
        try:
            if hasattr(self.app, 'sidebar') and self.app.sidebar:
                self.app.sidebar.configure(bg=COLORS.get('bg_root'))
        except Exception:
            pass
        
        # Update listbox
        try:
            if hasattr(self.app, 'lb') and self.app.lb:
                self.app.lb.configure(
                    bg=COLORS.get('bg_input'),
                    fg=COLORS.get('fg_text'),
                    selectbackground=COLORS.get('accent'),
                    selectforeground=COLORS.get('text_dark')
                )
        except Exception:
            pass
        
        # Update server status label
        try:
            if hasattr(self.app, 'status_lbl') and self.app.status_lbl:
                txt = self.app.status_lbl.cget('text')
                if 'Online' in txt:
                    fg = COLORS.get('success')
                elif 'Offline' in txt or 'Error' in txt:
                    fg = COLORS.get('offline')
                else:
                    fg = COLORS.get('fg_dim')
                self.app.status_lbl.configure(fg=fg, bg=COLORS.get('bg_root'))
        except Exception:
            pass
        
        # Update profile details area
        try:
            if hasattr(self.app, 'detail_frame') and self.app.detail_frame:
                self._update_widget_colors_recursive(self.app.detail_frame)
        except Exception:
            pass
        
        # Update craft screen elements
        try:
            if hasattr(self.app, 'craft_status_lbl') and self.app.craft_status_lbl:
                self.app.craft_status_lbl.configure(bg=COLORS.get('bg_root'), fg=COLORS.get('fg_text'))
        except Exception:
            pass
        
        # Update nav bar
        try:
            if hasattr(self.app, 'nav_bar_comp') and self.app.nav_bar_comp:
                self.app.nav_bar_comp.apply_theme()
        except Exception:
            pass
        
        # Update status bar colors
        try:
            if hasattr(self.app, 'status_bar_comp') and self.app.status_bar_comp:
                self.app.status_bar_comp.apply_theme()
        except Exception:
            pass
        
        # Update slayer UI state (colors)
        try:
            if hasattr(self.app, '_update_slayer_ui_state'):
                self.app._update_slayer_ui_state()
        except Exception:
            pass
        
        # Schedule screen rebuild after a short delay (to not interfere with dialog)
        try:
            self.app.root.after(50, self._rebuild_current_screen)
        except Exception:
            pass
        
        # Force refresh
        try:
            self.app.root.update_idletasks()
        except Exception:
            pass
    
    def _rebuild_current_screen(self):
        """Rebuild the current screen with new theme colors."""
        try:
            # Update navigation bar colors
            self._update_all_nav_buttons()
            
            # Update status bar
            self._update_status_bar_theme()
            
            # Destroy and recreate the current screen
            current = self.app.current_screen
            
            # Destroy the old screen frame
            if current in self.app.screens:
                self.app.screens[current].destroy()
                del self.app.screens[current]
            
            # Recreate the screen
            if current == "home":
                self.app.create_home_screen()
                self.app.screens["home"].pack(fill="both", expand=True)
                # Restore listbox state
                self.app.refresh_list()
            elif current == "craft":
                self.app.create_craft_screen()
                self.app.screens["craft"].pack(fill="both", expand=True)
            elif current == "log_monitor":
                self.app.create_log_monitor_screen()
                self.app.screens["log_monitor"].pack(fill="both", expand=True)
            elif current == "help":
                self.app.create_help_screen()
                self.app.screens["help"].pack(fill="both", expand=True)
            
            # Update nav button visual state
            if hasattr(self.app, 'nav_bar_comp') and self.app.nav_bar_comp:
                self.app.nav_bar_comp.apply_theme()
                    
        except Exception as e:
            self.app.log_error("_rebuild_current_screen", e)
    
    def _update_all_nav_buttons(self):
        """Update all navigation buttons with current theme colors."""
        try:
            # Update nav_frame background
            if hasattr(self.app, 'nav_frame') and self.app.nav_frame:
                self.app.nav_frame.configure(bg=COLORS["bg_panel"])
                for child in self.app.nav_frame.winfo_children():
                    try:
                        child.configure(bg=COLORS["bg_panel"])
                    except:
                        pass
                    for subchild in child.winfo_children():
                        try:
                            if subchild.winfo_class() == "Button":
                                # Check if it's the active screen
                                for screen, btn in self.app.nav_buttons.items():
                                    if btn == subchild:
                                        if screen == self.app.current_screen:
                                            subchild.configure(
                                                bg=COLORS["accent"],
                                                fg=COLORS["text_dark"],
                                                activebackground=COLORS["accent_hover"]
                                            )
                                        else:
                                            subchild.configure(
                                                bg=COLORS["bg_panel"],
                                                fg=COLORS["fg_text"],
                                                activebackground=COLORS["bg_input"]
                                            )
                                        break
                            else:
                                subchild.configure(bg=COLORS["bg_panel"])
                        except:
                            pass
        except Exception:
            pass
    
    def _update_nav_bar_theme(self):
        """Update navigation bar colors."""
        try:
            if hasattr(self.app, 'nav_bar_comp') and self.app.nav_bar_comp:
                self.app.nav_bar_comp.apply_theme()
        except Exception:
            pass
    
    def _update_sidebar_theme(self):
        """Update sidebar colors."""
        try:
            if hasattr(self.app, 'sidebar') and self.app.sidebar:
                self.app.sidebar.configure(bg=COLORS.get('bg_root'))
                # Update all children recursively
                self._update_widget_tree_bg(self.app.sidebar, COLORS.get('bg_root'))
            
            # Update listbox
            if hasattr(self.app, 'lb') and self.app.lb:
                self.app.lb.configure(
                    bg=COLORS.get('bg_input'),
                    fg=COLORS.get('fg_text'),
                    selectbackground=COLORS.get('accent'),
                    selectforeground=COLORS.get('text_dark')
                )
        except Exception:
            pass
    
    def _update_widget_tree_bg(self, widget, bg_color):
        """Recursively update background color of widget tree."""
        try:
            widget.configure(bg=bg_color)
        except Exception:
            pass
        try:
            for child in widget.winfo_children():
                cls = child.winfo_class().lower()
                if cls in ('frame', 'label'):
                    self._update_widget_tree_bg(child, bg_color)
                elif cls == 'listbox':
                    child.configure(bg=COLORS.get('bg_input'), fg=COLORS.get('fg_text'))
        except Exception:
            pass
    
    def _update_widget_colors_recursive(self, widget):
        """Recursively update widget colors based on current theme."""
        try:
            cls = widget.winfo_class().lower()
            
            if cls in ("frame", "labelframe"):
                try:
                    widget.configure(bg=COLORS.get('bg_root'))
                except Exception:
                    pass
                if cls == "labelframe":
                    try:
                        widget.configure(fg=COLORS.get('fg_dim'))
                    except Exception:
                        pass
            elif cls == "label":
                try:
                    widget.configure(bg=COLORS.get('bg_root'))
                except Exception:
                    pass
            elif cls == "entry":
                try:
                    widget.configure(bg=COLORS.get('bg_input'), fg=COLORS.get('fg_text'))
                except Exception:
                    pass
            elif cls == "button":
                # Skip ModernButtons as they handle themselves
                pass
            
            for child in widget.winfo_children():
                self._update_widget_colors_recursive(child)
        except Exception:
            pass
    
    def _update_status_bar_theme(self):
        """Update status bar colors when theme changes."""
        try:
            if hasattr(self.app, 'status_bar_comp') and self.app.status_bar_comp:
                self.app.status_bar_comp.apply_theme()
            # Trigger a status bar update to reapply semantic colors
            self.app._update_status_bar()
        except Exception:
            pass
    
    def _update_canvas_widgets(self, widget):
        """Recursively update Canvas widgets (for ToggleSwitches)."""
        try:
            if isinstance(widget, tk.Canvas):
                widget.configure(bg=COLORS.get('bg_root', widget.cget('bg')))
            # Check if it's a ToggleSwitch and redraw
            if hasattr(widget, '_draw') and hasattr(widget, 'on_color'):
                widget.on_color = COLORS.get('accent')
                widget.off_color = COLORS.get('border')
                widget._draw()
            for child in widget.winfo_children():
                self._update_canvas_widgets(child)
        except Exception:
            pass
