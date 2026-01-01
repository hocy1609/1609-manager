"""
Settings Manager for 16:09 Launcher.

Handles the settings dialog logic, including:
- Preparing current settings for display
- Handling save operations
- Handling live setting changes (callbacks)
- Invoking related dialogs (Backup, Import/Export, Log Monitor)
"""

from ui.dialogs import SettingsDialog
import tkinter as tk

class SettingsManager:
    """
    Manages the Settings Dialog and interactions.
    """
    def __init__(self, app):
        self.app = app

    def open_settings(self):
        """Open the main settings dialog."""
        current_sets = {
            "doc_path": self.app.doc_path_var.get(),
            "exe_path": self.app.exe_path_var.get(),
            "exit_coords_x": self.app.exit_x,
            "exit_coords_y": self.app.exit_y,
            "confirm_coords_x": self.app.confirm_x,
            "confirm_coords_y": self.app.confirm_y,
            "exit_speed": getattr(self.app, "exit_speed", 0.1),
            "esc_count": getattr(self.app, "esc_count", 1),
            "clip_margin": getattr(self.app, "clip_margin", 48),
            "show_tooltips": getattr(self.app, "show_tooltips", True),
            "theme": getattr(self.app, "theme", "dark"),
        }

        def on_save_settings(new_sets: dict):
            # Accept both legacy keys (`exit_x`) from dialog and canonical keys
            # used in saved settings (`exit_coords_x`). Use sensible defaults
            # if a key is missing to avoid KeyError from dialogs that send a
            # reduced subset.
            try:
                self.app.doc_path_var.set(new_sets.get("doc_path", self.app.doc_path_var.get()))
            except Exception:
                pass
            try:
                self.app.exe_path_var.set(new_sets.get("exe_path", self.app.exe_path_var.get()))
            except Exception:
                pass

            def _int_from_keys(d, primary, alt, default):
                v = d.get(primary, d.get(alt, None))
                try:
                    return int(v)
                except Exception:
                    return default

            self.app.exit_x = _int_from_keys(new_sets, "exit_coords_x", "exit_x", getattr(self.app, "exit_x", 950))
            self.app.exit_y = _int_from_keys(new_sets, "exit_coords_y", "exit_y", getattr(self.app, "exit_y", 640))
            self.app.confirm_x = _int_from_keys(new_sets, "confirm_coords_x", "confirm_x", getattr(self.app, "confirm_x", 802))
            self.app.confirm_y = _int_from_keys(new_sets, "confirm_coords_y", "confirm_y", getattr(self.app, "confirm_y", 613))
            # automation/UI
            try:
                self.app.exit_speed = float(new_sets.get("exit_speed", 0.1))
            except Exception:
                self.app.exit_speed = 0.1
            try:
                self.app.esc_count = int(new_sets.get("esc_count", 1))
            except Exception:
                self.app.esc_count = 1
            try:
                self.app.clip_margin = int(new_sets.get("clip_margin", 48))
            except Exception:
                self.app.clip_margin = 48
            self.app.show_tooltips = bool(new_sets.get("show_tooltips", True))
            
            # Apply theme
            new_theme = new_sets.get("theme", self.app.theme)
            theme_changed = (new_theme != self.app.theme)
            self.app.theme = new_theme
            
            try:
                import ui.ui_base as _uib
                _uib.TOOLTIPS_ENABLED = self.app.show_tooltips
                if theme_changed:
                    _uib.set_theme(self.app.theme, root=self.app.root)
            except Exception:
                pass
            
            self.app.save_data()
            
            # Rebuild UI after save if theme changed
            if theme_changed:
                self.app._rebuild_current_screen()

        def on_change_settings(delta: dict):
            """Apply individual setting changes immediately without requiring Save."""
            try:
                # Tooltips toggle: update UI module and all buttons live
                if "show_tooltips" in delta:
                    try:
                        self.app.show_tooltips = bool(delta.get("show_tooltips", self.app.show_tooltips))
                        import ui.ui_base as _uib
                        _uib.set_tooltips_enabled(self.app.show_tooltips)
                    except Exception:
                        pass

                # Numeric/automation fields
                if "exit_speed" in delta:
                    try:
                        self.app.exit_speed = float(delta.get("exit_speed", self.app.exit_speed))
                    except Exception:
                        pass
                if "esc_count" in delta:
                    try:
                        self.app.esc_count = int(delta.get("esc_count", self.app.esc_count))
                    except Exception:
                        pass
                if "clip_margin" in delta:
                    try:
                        self.app.clip_margin = int(delta.get("clip_margin", self.app.clip_margin))
                    except Exception:
                        pass

                # Theme change is applied on Save, not live
                # (live repaint is unreliable in Tkinter)

                # Persist the change with debounce so frequent edits don't spam disk
                try:
                    # Use default debounce for stable autosave (now 3000 ms)
                    if hasattr(self.app, 'schedule_save'):
                         self.app.schedule_save()
                    else:
                         self.app.save_data() # Fallback if schedule_save is missing
                except Exception:
                    pass
            except Exception as e:
                self.app.log_error("on_change_settings", e)

        SettingsDialog(
            self.app.root,
            current_sets,
            on_save_settings,
            self.app.export_data,
            self.app.import_data,
            on_open_backup=self.app.open_restore_dialog,
            on_change=on_change_settings,
            on_import_xnwn=self.app.import_xnwn_ini,
            on_log_monitor=self.app.open_log_monitor_dialog,
        )
