"""
UI state and layout management for NWN Manager.

This module centralizes UI initialization, layout helpers, and window controls
to keep NWNManagerApp focused on wiring and delegating.
"""

import tkinter as tk
from tkinter import ttk

from ui.ui_base import COLORS
from ui.components import TitleBar, StatusBar, NavigationBar
from ui.screens import (
    build_home_screen,
    build_settings_screen,
    build_log_monitor_screen,
    build_hotkeys_screen,
)


class UIStateManager:
    """Manages UI initialization, layout, and window helpers."""

    def __init__(self, app):
        self.app = app

    def configure_root_window(self):
        root = self.app.root
        root.title("16:09 Launcher")

        # Get DPI scale factor for HiDPI displays (4K, etc.)
        try:
            from utils.win_automation import get_dpi_scale
            dpi_scale = get_dpi_scale()
        except Exception:
            dpi_scale = 1.0
        
        # Clamp scale to reasonable range (1.0 - 3.0)
        dpi_scale = max(1.0, min(3.0, dpi_scale))
        
        # Store for later use
        self.app.dpi_scale = dpi_scale
        
        # Get screen dimensions
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        
        # Percentage-based sizing relative to screen resolution
        width = int(sw * 0.66)
        height = int(sh * 0.65)
        
        # Clamp to reasonable bounds
        width = max(1000, min(width, 1900))
        height = max(500, min(height, 1000))
        
        # Center window on screen
        x = (sw - width) // 2
        y = (sh - height) // 2
        root.geometry(f"{width}x{height}+{x}+{y}")
        
        # Allow resizing with minimum constraints
        root.resizable(True, True)
        root.minsize(1000, 500)
        
        root.configure(bg=COLORS["bg_root"])
        root.overrideredirect(True)
        
        print(f"[Window] Screen: {sw}x{sh}, DPI: {dpi_scale}, Window: {width}x{height}")

    def initialize_state(self):
        """Initialize UI-related state and Tk variables."""
        self.app.doc_path_var = tk.StringVar()
        self.app.exe_path_var = tk.StringVar()
        self.app.server_var = tk.StringVar()
        self.app.use_server_var = tk.BooleanVar(value=True)

        self.app.exit_x, self.app.exit_y = 950, 640
        self.app.confirm_x, self.app.confirm_y = 802, 613
        self.app.exit_speed = 0.1
        self.app.esc_count = 1
        self.app.clip_margin = 48
        self.app.show_tooltips = True

        self.app.profiles = []
        self.app.servers = []
        self.app.server_group = "siala"
        self.app.server_groups = {}
        self.app.theme = "dark"

        self.app.current_profile = None

        # Info panel entries
        self.app.info_name = None
        self.app.info_login = None
        self.app.info_cdkey = None
        self.app.show_key = False

        self.app.view_map = []
        self.app.drag_data = {"index": None}
        self.app._drag_data = {"x": 0, "y": 0}

        # UI components
        self.app.title_bar_comp = None
        self.app.status_bar_comp = None
        self.app.nav_bar_comp = None

        # UI helpers
        self.app._last_session_count = -1
        self.app._last_running_state = None

        # Controller profile per active cdKey
        self.app.controller_profile_by_cdkey = {}

        self.app.current_screen = "home"
        self.app.nav_frame = None
        self.app.content_frame = None
        self.app.screens = {}

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")

        style.configure(
            "TCheckbutton",
            background=COLORS["bg_root"],
            foreground=COLORS["fg_text"],
            font=("Segoe UI", 10),
            focuscolor=COLORS["bg_root"],
        )

        style.map(
            "TCombobox",
            fieldbackground=[("readonly", COLORS["bg_input"])],
            selectbackground=[("readonly", COLORS["bg_input"])],
            selectforeground=[("readonly", COLORS["fg_text"])],
            background=[("readonly", COLORS["bg_panel"])],
        )

        style.configure(
            "TCombobox",
            background=COLORS["bg_panel"],
            foreground=COLORS["fg_text"],
            fieldbackground=COLORS["bg_input"],
            arrowcolor=COLORS["fg_text"],
            bordercolor=COLORS["border"],
        )
        
        # Style the dropdown list (Listbox) for Combobox - ttk.Style doesn't affect it
        self.app.root.option_add("*TCombobox*Listbox.background", COLORS["bg_input"])
        self.app.root.option_add("*TCombobox*Listbox.foreground", COLORS["fg_text"])
        self.app.root.option_add("*TCombobox*Listbox.selectBackground", COLORS["accent"])
        self.app.root.option_add("*TCombobox*Listbox.selectForeground", COLORS["text_dark"])

        # Treeview Styles
        style.configure(
            "ProfileList.Treeview",
            background=COLORS["bg_panel"],
            foreground=COLORS["fg_text"],
            fieldbackground=COLORS["bg_panel"],
            borderwidth=0,
            font=("Segoe UI", 11),
            rowheight=28
        )
        style.map(
            "ProfileList.Treeview",
            background=[
                ("selected", "focus", COLORS["accent"]),
                ("selected", "!focus", COLORS["accent"]),
                ("!selected", COLORS["bg_panel"])
            ],
            foreground=[
                ("selected", "focus", COLORS["text_dark"]),
                ("selected", "!focus", COLORS["text_dark"]),
                ("!selected", COLORS["fg_text"])
            ]
        )
        style.configure(
            "ProfileList.Treeview.Heading",
            background=COLORS["bg_panel"],
            foreground=COLORS["fg_dim"],
            font=("Segoe UI", 9, "bold"),
            relief="flat"
        )
        style.map("ProfileList.Treeview.Heading",
            background=[("active", COLORS["bg_panel"])],
            foreground=[("active", COLORS["accent"])]
        )
        
        
        # Remove default border from Treeview layout
        style.layout("ProfileList.Treeview", [('ProfileList.Treeview.treearea', {'sticky': 'nswe'})])

        # Add visual separation between items (borders)
        style.configure(
            "ProfileList.Treeview.Item",
            borderwidth=1,
            bordercolor=COLORS["border"], # Use distinct border color as separator
            relief="solid"
        )
        style.map(
            "ProfileList.Treeview.Item",
            bordercolor=[("selected", COLORS["accent"])]
        )

    def set_appwindow(self):
        from utils.win_automation import user32, GWL_EXSTYLE, WS_EX_APPWINDOW, WS_EX_TOOLWINDOW

        try:
            hwnd = user32.GetParent(self.app.root.winfo_id())
            style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            style = style & ~WS_EX_TOOLWINDOW
            style = style | WS_EX_APPWINDOW
            user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
            self.app.root.wm_withdraw()
            self.app.root.after(10, self.app.root.wm_deiconify)
        except Exception as e:
            self.app.log_error("set_appwindow", e)

    def start_move(self, event):
        self.app._drag_data["x"] = event.x
        self.app._drag_data["y"] = event.y

    def do_move(self, event):
        x = self.app.root.winfo_x() + (event.x - self.app._drag_data["x"])
        y = self.app.root.winfo_y() + (event.y - self.app._drag_data["y"])
        self.app.root.geometry(f"+{x}+{y}")

    def minimize_window(self):
        from utils.win_automation import user32, SW_MINIMIZE

        try:
            hwnd = user32.GetParent(self.app.root.winfo_id())
            user32.ShowWindow(hwnd, SW_MINIMIZE)
        except Exception:
            self.app.root.iconify()

    def close_app_window(self):
        self.app.root.destroy()

    _SCREEN_BUILDERS = {
        "home": "create_home_screen",
        "hotkeys": "create_hotkeys_screen",
        "settings": "create_settings_screen",
        "log_monitor": "create_log_monitor_screen",
    }

    def create_ui(self):
        """Build main UI layout."""
        app = self.app
        # Title bar
        app.title_bar_comp = TitleBar(app, app.root)

        # Status bar at bottom (attach to root to avoid being obscured by content)
        # Pack before main container so it reserves space at bottom
        app.status_bar_comp = StatusBar(app, app.root)

        # Main container (kept between title bar and status bar)
        main_container = tk.Frame(app.root, bg=COLORS["bg_root"])
        main_container.pack(side="top", fill="both", expand=True)

        # Navigation bar at top
        app.nav_frame = tk.Frame(main_container, bg=COLORS["bg_panel"], height=60)
        app.nav_frame.pack(fill="x", side="top")
        app.nav_frame.pack_propagate(False)

        app.nav_bar_comp = NavigationBar(app, app.nav_frame)

        # Content area
        app.content_frame = tk.Frame(main_container, bg=COLORS["bg_root"])
        app.content_frame.pack(fill="both", expand=True)

        # Create home screen immediately (most used), others loaded lazily
        self.create_home_screen()

        # Show home by default
        self.show_screen("home")

        # Start status bar update loop
        self._update_status_bar_loop()

    def rebuild_ui(self):
        """Destroy all window content and rebuild from scratch.
        
        This is the nuclear option for theme application. Instead of trying to patch
        colors on existing widgets (which is error-prone), we wipe the slate clean
        and build everything fresh with the new theme globals.
        """
        try:
            # 1. Save state
            current_screen = self.app.current_screen
            
            # 2. Destroy all widgets in root
            for widget in self.app.root.winfo_children():
                widget.destroy()
                
            # 3. Reset component references
            self.app.title_bar_comp = None
            self.app.status_bar_comp = None
            self.app.nav_bar_comp = None
            self.app.nav_frame = None
            self.app.content_frame = None
            self.app.screens = {}
            
            # 4. Re-apply ttk styles with new COLORS
            self.setup_styles()
            self.app.root.configure(bg=COLORS["bg_root"])
            
            # 5. Re-create UI
            # This uses the CURRENT global COLORS (which should have been updated by set_theme)
            self.create_ui()
            
            # 6. Restore screen
            self.show_screen(current_screen)
            
            # 7. Repopulate data-driven widgets
            if hasattr(self.app, 'profile_manager'):
                self.app.profile_manager.refresh_list()
            if hasattr(self.app, '_create_server_buttons'):
                self.app._create_server_buttons()
            
            # 8. Force immediate update
            self.app.root.update_idletasks()
            
        except Exception as e:
            self.app.log_error("rebuild_ui", e)
    
    def _update_status_bar_loop(self):
        """Periodically update status bar information."""
        try:
            self._update_status_bar()
        except Exception:
            pass
        self.app.root.after(1000, self._update_status_bar_loop)

    def _update_status_bar(self):
        """Update all status bar labels."""
        if self.app.status_bar_comp:
            self.app.status_bar_comp.update()

        # Update navigation indicators
        self._update_nav_indicators()

        # Update slayer UI state periodically
        try:
            self.app._update_slayer_ui_state()
        except Exception:
            pass

    def _update_nav_indicators(self):
        """Update navigation button indicators."""
        if self.app.nav_bar_comp:
            self.app.nav_bar_comp.update_indicators()

    def _update_nav_btn_style(self, btn, screen_name):
        """Update button style based on whether it's the active screen."""
        if screen_name == self.app.current_screen:
            btn.configure(bg=COLORS["accent"], fg=COLORS["text_dark"])
        else:
            btn.configure(bg=COLORS["bg_panel"], fg=COLORS["fg_text"])

    def show_screen(self, screen_name):
        """Switch to specified screen instantly. Lazily creates screen if needed."""
        # Lazy-load screen if not yet created
        if screen_name not in self.app.screens:
            builder_name = self._SCREEN_BUILDERS.get(screen_name)
            if builder_name:
                builder_method = getattr(self, builder_name, None)
                if builder_method:
                    builder_method()
            # If still not created, bail
            if screen_name not in self.app.screens:
                return
        
        new_screen = self.app.screens.get(screen_name)
        
        # Hide all other screens
        for name, screen in self.app.screens.items():
            if name != screen_name:
                try:
                    screen.pack_forget()
                except Exception:
                    pass
        
        # Skip if same screen and already visible
        try:
            if screen_name == self.app.current_screen and new_screen.winfo_ismapped():
                return
        except Exception:
            pass
        
        # Update state
        self.app.current_screen = screen_name
        
        # Update navigation bar button styles
        if self.app.nav_bar_comp:
            for name in self.app.nav_bar_comp.buttons:
                self.app.nav_bar_comp._update_style(name)
        
        # Show new screen
        new_screen.pack(fill="both", expand=True)

    def create_home_screen(self):
        """Original main UI as home screen (delegated)."""
        return build_home_screen(self.app)

    def on_root_resize(self, event):
        """Listen to root size changes and switch layout mode when crossing threshold."""
        try:
            width = self.app.root.winfo_width()
        except Exception:
            return
        threshold = 900
        mode = "wide" if width >= threshold else "compact"
        if mode == getattr(self.app, "_layout_mode", None):
            return
        self.apply_layout_mode(mode)
        self.app._layout_mode = mode

    def apply_layout_mode(self, mode: str):
        """Adaptive outer spacing only (simplified)."""
        try:
            self.update_spacing(mode)
        except Exception as e:
            self.app.log_error("apply_layout_mode", e)

    def update_spacing(self, mode: str):
        """Scale paddings smoothly based on window width and mode."""
        try:
            w = self.app.root.winfo_width()
            scale = max(0.0, min(1.0, (w - 700) / 600))
            base = 18 if mode == "compact" else 32
            pad = int(base + 24 * scale)
            if hasattr(self.app, "home_content"):
                try:
                    self.app.home_content.pack_configure(padx=pad, pady=pad)
                except Exception:
                    pass
        except Exception as e:
            self.app.log_error("update_spacing", e)


    def create_settings_screen(self):
        """Settings screen - delegated."""
        return build_settings_screen(self.app)

    def create_log_monitor_screen(self):
        """Log monitor screen - delegated."""
        return build_log_monitor_screen(self.app)

    def create_hotkeys_screen(self):
        """Hotkeys screen - delegated."""
        return build_hotkeys_screen(self.app)

