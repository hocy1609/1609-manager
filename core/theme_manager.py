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
        """Reapply current theme by rebuilding the entire UI."""
        # 1. Update globals in ui_base
        import ui.ui_base as _uib
        _uib.set_theme(self.app.theme, root=self.app.root)
        
        # 2. Trigger Nuclear Rebuild
        # This destroys and recreates all widgets with the new theme colors
        try:
            if hasattr(self.app, 'ui_state_manager'):
                self.app.ui_state_manager.rebuild_ui()
            else:
                # Fallback if no manager (should not happen in prod)
                pass
        except Exception as e:
            self.app.log_error("ThemeManager.apply_theme", e)

    # Legacy update methods removed - we now rebuild the world


    # Legacy/helper methods removed or folded into _update_tree
    # Keeping empty stubs if called from outside, or rely on them being internal

