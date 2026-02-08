import tkinter as tk
from tkinter import ttk
import os
from ui.ui_base import COLORS, TitleBarButton

class TitleBar:
    def __init__(self, app, parent):
        self.app = app
        self.parent = parent
        self.root = app.root
        self._drag_data = {"x": 0, "y": 0}
        self._is_maximized = False
        self._normal_geometry = None
        
        self.frame = tk.Frame(
            self.parent,
            bg=COLORS["bg_panel"],
            relief="flat",
            bd=0,
            height=35,
        )
        self.frame.pack(fill="x", side="top")
        self.frame.pack_propagate(False)

        self.frame.bind("<Button-1>", self.start_move)
        self.frame.bind("<B1-Motion>", self.do_move)
        self.frame.bind("<Double-Button-1>", lambda e: self.toggle_maximize())

        self.title_lbl = tk.Label(
            self.frame,
            text="16:09 Launcher",
            bg=COLORS["bg_panel"],
            fg=COLORS["fg_text"],
            font=("Segoe UI", 10, "bold"),
        )
        self.title_lbl.pack(side="left", padx=15)
        self.title_lbl.bind("<Button-1>", self.start_move)
        self.title_lbl.bind("<B1-Motion>", self.do_move)
        self.title_lbl.bind("<Double-Button-1>", lambda e: self.toggle_maximize())

        # Buttons are packed from right to left: Close -> Maximize -> Minimize
        # Using Segoe Fluent Icons: E8BB = Close, E922/E923 = Maximize/Restore, E921 = Minimize
        self.close_btn = TitleBarButton(
            self.frame, "\uE8BB", self.app.close_app_window, hover_color=COLORS["danger"]
        )
        self.close_btn.pack(side="right", fill="y")

        self.max_btn = TitleBarButton(self.frame, "\uE922", self.toggle_maximize)
        self.max_btn.pack(side="right", fill="y")

        self.min_btn = TitleBarButton(self.frame, "\uE921", self.app.minimize_window)
        self.min_btn.pack(side="right", fill="y")

    def toggle_maximize(self):
        """Toggle between maximized and normal window state."""
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        
        if self._is_maximized:
            # Restore to normal size and center
            if self._normal_geometry:
                # Parse saved geometry "WxH+X+Y"
                try:
                    size_part = self._normal_geometry.split('+')[0]
                    w, h = map(int, size_part.split('x'))
                except:
                    w, h = 1100, 600
                
                # Center on screen
                x = (sw - w) // 2
                y = (sh - h) // 2
                self.root.geometry(f"{w}x{h}+{x}+{y}")
            self.max_btn.config(text="\uE922")  # Maximize icon
            self._is_maximized = False
        else:
            # Save current geometry and maximize
            self._normal_geometry = self.root.geometry()
            # Leave a small margin for taskbar (40px at bottom)
            self.root.geometry(f"{sw}x{sh - 40}+0+0")
            self.max_btn.config(text="\uE923")  # Restore icon
            self._is_maximized = True

    def start_move(self, event):
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y

    def do_move(self, event):
        # If maximized, exit maximize mode on drag
        if self._is_maximized:
            self.toggle_maximize()
            return
        x = self.root.winfo_x() + (event.x - self._drag_data["x"])
        y = self.root.winfo_y() + (event.y - self._drag_data["y"])
        self.root.geometry(f"+{x}+{y}")

    def apply_theme(self):
        """Update colors for theme switch."""
        try:
            self.frame.config(bg=COLORS["bg_panel"])
            self.title_lbl.config(bg=COLORS["bg_panel"], fg=COLORS["fg_text"])
            self.close_btn.update_colors()
            self.max_btn.update_colors()
            self.min_btn.update_colors()
        except Exception:
            pass


class StatusBar:
    def __init__(self, app, parent):
        self.app = app
        self.parent = parent
        self.labels = {}
        self._resize_data = {"x": 0, "y": 0, "width": 0, "height": 0}
        
        self.frame = tk.Frame(self.parent, bg=COLORS["bg_panel"], height=28)
        self.frame.pack(fill="x", side="bottom")
        self.frame.pack_propagate(False)
        
        # Resize grip on the right corner
        self.resize_grip = tk.Label(
            self.frame,
            text="⋮⋮",  # Unicode grip icon
            bg=COLORS["bg_panel"],
            fg=COLORS["fg_dim"],
            font=("Segoe UI", 10),
            cursor="size_nw_se"
        )
        self.resize_grip.pack(side="right", padx=5)
        self.resize_grip.bind("<Button-1>", self._start_resize)
        self.resize_grip.bind("<B1-Motion>", self._do_resize)
        
        # Left side: Sessions count - split into icon + text for proper font rendering
        left_frame = tk.Frame(self.frame, bg=COLORS["bg_panel"])
        left_frame.pack(side="left", padx=15, pady=4)
        
        # Icon label with Segoe Fluent Icons
        self._sessions_icon = tk.Label(
            left_frame,
            text="\uE7FC",
            bg=COLORS["bg_panel"],
            fg=COLORS["fg_dim"],
            font=("Segoe Fluent Icons", 10)
        )
        self._sessions_icon.pack(side="left")
        
        # Text label with normal font
        self.labels["sessions"] = tk.Label(
            left_frame,
            text="Sessions: 0",
            bg=COLORS["bg_panel"],
            fg=COLORS["fg_dim"],
            font=("Segoe UI", 9)
        )
        self.labels["sessions"].pack(side="left", padx=(3, 0))

        
        # Separator
        tk.Frame(self.frame, bg=COLORS["border"], width=1).pack(side="left", fill="y", padx=10, pady=4)
        
        # Log Monitor status (clickable toggle) - split into icon + text
        log_frame = tk.Frame(self.frame, bg=COLORS["bg_panel"], cursor="hand2")
        log_frame.pack(side="left", padx=5)
        
        self._log_icon = tk.Label(
            log_frame,
            text="\uE9D2",
            bg=COLORS["bg_panel"],
            fg=COLORS["fg_dim"],
            font=("Segoe Fluent Icons", 10),
            cursor="hand2"
        )
        self._log_icon.pack(side="left")
        
        self.labels["log_monitor"] = tk.Label(
            log_frame,
            text="Log: Off",
            bg=COLORS["bg_panel"],
            fg=COLORS["fg_dim"],
            font=("Segoe UI", 9),
            cursor="hand2"
        )
        self.labels["log_monitor"].pack(side="left", padx=(3, 0))
        
        # Bind click to both icon and text
        log_frame.bind("<Button-1>", lambda e: self._toggle_log_monitor())
        self._log_icon.bind("<Button-1>", lambda e: self._toggle_log_monitor())
        self.labels["log_monitor"].bind("<Button-1>", lambda e: self._toggle_log_monitor())

        
        # Separator
        tk.Frame(self.frame, bg=COLORS["border"], width=1).pack(side="left", fill="y", padx=10, pady=4)
        
        self._create_slayer_labels()
    
    def _start_resize(self, event):
        """Start window resize from bottom-right corner."""
        root = self.app.root
        self._resize_data["x"] = event.x_root
        self._resize_data["y"] = event.y_root
        self._resize_data["width"] = root.winfo_width()
        self._resize_data["height"] = root.winfo_height()
    
    def _do_resize(self, event):
        """Handle window resize drag."""
        root = self.app.root
        dx = event.x_root - self._resize_data["x"]
        dy = event.y_root - self._resize_data["y"]
        
        new_width = max(900, self._resize_data["width"] + dx)
        new_height = max(500, self._resize_data["height"] + dy)
        
        x = root.winfo_x()
        y = root.winfo_y()
        root.geometry(f"{new_width}x{new_height}+{x}+{y}")
        
    def _create_slayer_labels(self):
        # Hotkeys status (clickable toggle) - E765 = Keyboard icon
        hotkeys_frame = tk.Frame(self.frame, bg=COLORS["bg_panel"], cursor="hand2")
        hotkeys_frame.pack(side="left", padx=5)
        
        self._hotkeys_icon = tk.Label(
            hotkeys_frame,
            text="\uE765",
            bg=COLORS["bg_panel"],
            fg=COLORS["fg_dim"],
            font=("Segoe Fluent Icons", 10),
            cursor="hand2"
        )
        self._hotkeys_icon.pack(side="left")
        
        self.labels["hotkeys"] = tk.Label(
            hotkeys_frame,
            text="Hotkeys: Off",
            bg=COLORS["bg_panel"],
            fg=COLORS["fg_dim"],
            font=("Segoe UI", 9),
            cursor="hand2"
        )
        self.labels["hotkeys"].pack(side="left", padx=(3, 0))
        
        # Bind click to all parts
        hotkeys_frame.bind("<Button-1>", lambda e: self._toggle_hotkeys())
        self._hotkeys_icon.bind("<Button-1>", lambda e: self._toggle_hotkeys())
        self.labels["hotkeys"].bind("<Button-1>", lambda e: self._toggle_hotkeys())

        # Separator before Auto-Fog
        tk.Frame(self.frame, bg=COLORS["border"], width=1).pack(side="left", fill="y", padx=10, pady=4)
        
        # Auto-Fog status (clickable toggle) - E753 = Cloud/Weather icon
        fog_frame = tk.Frame(self.frame, bg=COLORS["bg_panel"], cursor="hand2")
        fog_frame.pack(side="left", padx=5)
        
        self._fog_icon = tk.Label(
            fog_frame,
            text="\uE753",
            bg=COLORS["bg_panel"],
            fg=COLORS["fg_dim"],
            font=("Segoe Fluent Icons", 10),
            cursor="hand2"
        )
        self._fog_icon.pack(side="left")
        
        self.labels["auto_fog"] = tk.Label(
            fog_frame,
            text="Fog: Off",
            bg=COLORS["bg_panel"],
            fg=COLORS["fg_dim"],
            font=("Segoe UI", 9),
            cursor="hand2"
        )
        self.labels["auto_fog"].pack(side="left", padx=(3, 0))
        
        # Bind click to all parts
        fog_frame.bind("<Button-1>", lambda e: self._toggle_auto_fog())
        self._fog_icon.bind("<Button-1>", lambda e: self._toggle_auto_fog())
        self.labels["auto_fog"].bind("<Button-1>", lambda e: self._toggle_auto_fog())

        # Separator before Slayer (now at end)
        tk.Frame(self.frame, bg=COLORS["border"], width=1).pack(side="left", fill="y", padx=10, pady=4)
        
        # Slayer status (clickable toggle) - E81D = Cut/blade icon - NOW AT END
        slayer_frame = tk.Frame(self.frame, bg=COLORS["bg_panel"], cursor="hand2")
        slayer_frame.pack(side="left", padx=5)
        
        self._slayer_icon = tk.Label(
            slayer_frame,
            text="\uE81D",
            bg=COLORS["bg_panel"],
            fg=COLORS["fg_dim"],
            font=("Segoe Fluent Icons", 10),
            cursor="hand2"
        )
        self._slayer_icon.pack(side="left")
        
        self.labels["slayer"] = tk.Label(
            slayer_frame,
            text="Slayer: Off",
            bg=COLORS["bg_panel"],
            fg=COLORS["fg_dim"],
            font=("Segoe UI", 9),
            cursor="hand2"
        )
        self.labels["slayer"].pack(side="left", padx=(3, 0))
        
        # Slayer hit counter (separate, normal font)
        self.labels["slayer_hits"] = tk.Label(
            slayer_frame,
            text="(0 hits)",
            bg=COLORS["bg_panel"],
            fg=COLORS["fg_dim"],
            font=("Segoe UI", 9)
        )
        self.labels["slayer_hits"].pack(side="left", padx=(3, 0))
        
        # Bind click to all parts
        slayer_frame.bind("<Button-1>", lambda e: self._toggle_slayer())
        self._slayer_icon.bind("<Button-1>", lambda e: self._toggle_slayer())
        self.labels["slayer"].bind("<Button-1>", lambda e: self._toggle_slayer())

    
    def _toggle_hotkeys(self):
        """Toggle hotkeys enabled state on click."""
        try:
            print("[StatusBar] _toggle_hotkeys clicked")
            # Try to toggle variable first
            var = getattr(self.app, 'hotkeys_enabled_var', None)
            
            if var:
                new_enabled = not var.get()
                var.set(new_enabled)
                print(f"[StatusBar] Hotkeys var set to {new_enabled}")
                # Manual trigger logic since this var might not have a trace in all versions
                self.app.hotkeys_config['enabled'] = new_enabled
                if new_enabled:
                    if hasattr(self.app, '_apply_saved_hotkeys'):
                        self.app._apply_saved_hotkeys()
                else:
                    if hasattr(self.app, 'multi_hotkey_manager'):
                        self.app.multi_hotkey_manager.unregister_all()
                if hasattr(self.app, 'save_data'):
                    self.app.save_data()
            else:
                # Fallback logic
                hotkeys_cfg = getattr(self.app, 'hotkeys_config', {})
                new_enabled = not hotkeys_cfg.get('enabled', False)
                self.app.hotkeys_config['enabled'] = new_enabled
                
                if new_enabled:
                    if hasattr(self.app, '_apply_saved_hotkeys'):
                        self.app._apply_saved_hotkeys()
                else:
                    if hasattr(self.app, 'multi_hotkey_manager'):
                        self.app.multi_hotkey_manager.unregister_all()
                
                if hasattr(self.app, 'save_data'):
                    self.app.save_data()
        except Exception as e:
            print(f"[StatusBar] Error in _toggle_hotkeys: {e}")
    
    def _toggle_log_monitor(self):
        """Toggle log monitor on click."""
        try:
            if hasattr(self.app, 'log_monitor_manager'):
                self.app.log_monitor_manager.toggle_log_monitor_enabled()
        except Exception as e:
            print(f"[StatusBar] Error in _toggle_log_monitor: {e}")
    
    def _toggle_slayer(self):
        """Toggle Slayer (Open Wounds) on click."""
        try:
            # Retrieve variable
            var = getattr(self.app.log_monitor_state, 'open_wounds_enabled_var', None)
            if var:
                # Toggle variable - trace will handle config save and UI updates
                new_val = not var.get()
                var.set(new_val)
                print(f"[StatusBar] Toggling Slayer var to {new_val}")
            else:
                # Fallback if var not ready
                ow_cfg = self.app.log_monitor_state.config.get("open_wounds", {})
                new_enabled = not ow_cfg.get("enabled", False)
                self.app.log_monitor_state.config["open_wounds"]["enabled"] = new_enabled
                if hasattr(self.app, 'log_monitor_manager'):
                    self.app.log_monitor_manager.update_slayer_ui_state()
                    self.app.log_monitor_manager._ensure_slayer_if_enabled()
                if hasattr(self.app, 'save_data'):
                    self.app.save_data()
        except Exception as e:
            print(f"[StatusBar] Error in _toggle_slayer: {e}")
    
    def _toggle_auto_fog(self):
        """Toggle Auto-Fog on click."""
        try:
            # Retrieve variable
            var = getattr(self.app.log_monitor_state, 'auto_fog_enabled_var', None)
            if var:
                # Toggle variable - trace will handle config save and UI updates
                new_val = not var.get()
                var.set(new_val)
                print(f"[StatusBar] Toggling Auto-Fog var to {new_val}")
            else:
                # Fallback
                af_cfg = self.app.log_monitor_state.config.get("auto_fog", {})
                new_enabled = not af_cfg.get("enabled", False)
                self.app.log_monitor_state.config["auto_fog"]["enabled"] = new_enabled
                if hasattr(self.app, 'save_data'):
                    self.app.save_data()
        except Exception as e:
            print(f"[StatusBar] Error in _toggle_auto_fog: {e}")

    def update(self):
        """Update all status bar labels"""
        try:
            # Sessions count (text only, icon is separate)
            session_count = len(getattr(self.app.sessions, "sessions", {}) or {})
            sessions_text = f"Sessions: {session_count}"
            sessions_fg = COLORS["success"] if session_count > 0 else COLORS["fg_dim"]
            self.labels["sessions"].config(text=sessions_text, fg=sessions_fg)
            if hasattr(self, '_sessions_icon'):
                self._sessions_icon.config(fg=sessions_fg)
            
            # Log Monitor status (text only, icon is separate)
            log_on = self.app.log_monitor_state.monitor and self.app.log_monitor_state.monitor.is_running()
            log_enabled = self.app.log_monitor_state.config.get("enabled", False)
            
            if log_on:
                log_text = "Log: On"
                log_fg = COLORS["success"]
            elif log_enabled:
                log_text = "Log: Waiting"
                log_fg = COLORS["accent"]
            else:
                log_text = "Log: Off"
                log_fg = COLORS["fg_dim"]
            self.labels["log_monitor"].config(text=log_text, fg=log_fg)
            if hasattr(self, '_log_icon'):
                self._log_icon.config(fg=log_fg)
            
            # Hotkeys status (text only, icon is separate)
            hotkeys_cfg = getattr(self.app, 'hotkeys_config', {})
            hotkeys_enabled = hotkeys_cfg.get('enabled', False)
            hotkeys_active = hasattr(self.app, 'multi_hotkey_manager') and self.app.multi_hotkey_manager._running
            
            if hotkeys_active:
                binds_count = len([b for b in hotkeys_cfg.get('binds', []) if b.get('enabled', True)])
                hotkeys_text = f"Hotkeys: On ({binds_count})"
                hotkeys_fg = COLORS["success"]
            elif hotkeys_enabled:
                hotkeys_text = "Hotkeys: Waiting"
                hotkeys_fg = COLORS["accent"]
            else:
                hotkeys_text = "Hotkeys: Off"
                hotkeys_fg = COLORS["fg_dim"]
            self.labels["hotkeys"].config(text=hotkeys_text, fg=hotkeys_fg)
            if hasattr(self, '_hotkeys_icon'):
                self._hotkeys_icon.config(fg=hotkeys_fg)
            
            # Auto-Fog status (text only, icon is separate)
            auto_fog_cfg = self.app.log_monitor_state.config.get("auto_fog", {})
            fog_enabled = auto_fog_cfg.get("enabled", False)
            fog_active = fog_enabled and log_on
            
            if fog_active:
                fog_text = "Fog: On"
                fog_fg = COLORS["success"]
            elif fog_enabled:
                fog_text = "Fog: Waiting"
                fog_fg = COLORS["accent"]
            else:
                fog_text = "Fog: Off"
                fog_fg = COLORS["fg_dim"]
            self.labels["auto_fog"].config(text=fog_text, fg=fog_fg)
            if hasattr(self, '_fog_icon'):
                self._fog_icon.config(fg=fog_fg)
            
            # Slayer status - NOW REQUIRES LOG MONITOR TO BE ON (no independent monitor)
            # Slayer status
            slayer_cfg = self.app.log_monitor_state.config.get("open_wounds", {})
            slayer_enabled = slayer_cfg.get("enabled", False)
            
            # Check both main monitor and standalone slayer monitor
            slayer_monitor_running = self.app.log_monitor_state.slayer_monitor and self.app.log_monitor_state.slayer_monitor.is_running()
            slayer_active = slayer_enabled and (log_on or slayer_monitor_running)
            
            if slayer_active:
                slayer_text = f"Slayer: On ({slayer_cfg.get('key', 'F1')})"
                slayer_fg = COLORS["warning"]
            elif slayer_enabled:
                slayer_text = "Slayer: Waiting"
                slayer_fg = COLORS["accent"]
            else:
                slayer_text = "Slayer: Off"
                slayer_fg = COLORS["fg_dim"]
            self.labels["slayer"].config(text=slayer_text, fg=slayer_fg)
            if hasattr(self, '_slayer_icon'):
                self._slayer_icon.config(fg=slayer_fg)
            
            # Slayer hits
            hits_text = f"({self.app.log_monitor_state.slayer_hit_count} hits)"
            hits_fg = COLORS["warning"] if self.app.log_monitor_state.slayer_hit_count > 0 else COLORS["fg_dim"]
            self.labels["slayer_hits"].config(text=hits_text, fg=hits_fg)
        except Exception:
            pass

    def apply_theme(self):
        """Update colors for theme switch"""
        self.frame.config(bg=COLORS["bg_panel"])
        if hasattr(self, 'resize_grip'):
            self.resize_grip.config(bg=COLORS["bg_panel"], fg=COLORS["fg_dim"])
        
        # Update labels background
        for label in self.labels.values():
            label.config(bg=COLORS["bg_panel"])
        
        # Update separate icon labels
        for attr in ['_sessions_icon', '_log_icon', '_hotkeys_icon', '_fog_icon', '_slayer_icon']:
            if hasattr(self, attr):
                getattr(self, attr).config(bg=COLORS["bg_panel"])
        
        # Force immediate update of foregrounds
        self.update()


class NavigationBar:
    """Navigation bar with large accent-colored icons and text labels."""
    
    def __init__(self, app, parent):
        self.app = app
        self.parent = parent
        self.buttons = {}  # screen -> frame widget
        self._icons = {}   # screen -> icon label
        self._labels = {}  # screen -> text label
        self._hovered = set()
        
        self.frame = tk.Frame(self.parent, bg=COLORS["bg_panel"])
        self.frame.pack(side="left", padx=20, pady=10)
        
        # Segoe Fluent Icons Unicode characters (Windows 11 icon font)
        # Use "Segoe Fluent Icons" font or fallback to "Segoe MDL2 Assets"
        # (icon, text, screen, tooltip)
        btn_defs = [
            ("\uE80F", "Home", "home", "Главный экран - управление аккаунтами и запуск игры"),
            ("\uE9D2", "Log Monitor", "log_monitor", "Мониторинг лога игры"),
            ("\uE765", "Hotkeys", "hotkeys", "Настройка горячих клавиш"),
            ("\uE90F", "Craft", "craft", "Автокрафт и управление макросами"),
            ("\uE713", "Settings", "settings", "Настройки приложения"),
        ]
        
        for icon, text, screen, tooltip_text in btn_defs:
            # Container frame
            btn_frame = tk.Frame(
                self.frame,
                bg=COLORS["bg_panel"],
                cursor="hand2",
                padx=12,
                pady=8,
            )
            btn_frame.pack(side="left", padx=2)
            
            # Icon label - accent color, same baseline
            # Use Segoe Fluent Icons (Win11) with fallback to Segoe MDL2 Assets (Win10)
            icon_lbl = tk.Label(
                btn_frame,
                text=icon,
                bg=COLORS["bg_panel"],
                fg=COLORS["accent"],
                font=("Segoe Fluent Icons", 14),
                cursor="hand2",
            )
            icon_lbl.pack(side="left", padx=(0, 4), anchor="center")
            
            # Text label - normal color
            text_lbl = tk.Label(
                btn_frame,
                text=text,
                bg=COLORS["bg_panel"],
                fg=COLORS["fg_text"],
                font=("Segoe UI", 10),
                cursor="hand2",
            )
            text_lbl.pack(side="left", anchor="center")
            
            # Store references
            self.buttons[screen] = btn_frame
            self._icons[screen] = icon_lbl
            self._labels[screen] = text_lbl
            
            # Bind click to frame and both labels
            for widget in [btn_frame, icon_lbl, text_lbl]:
                widget.bind("<Button-1>", lambda e, s=screen: self._on_click(s))
            
            # Hover
            btn_frame.bind("<Enter>", lambda e, s=screen: self._on_hover(s, True), add="+")
            btn_frame.bind("<Leave>", lambda e, s=screen: self._on_hover(s, False), add="+")
            

    
    def _on_click(self, screen):
        """Handle button click."""
        self.app.show_screen(screen)
    
    def _on_hover(self, screen, entering):
        """Handle hover with simple state tracking."""
        if entering:
            if screen in self._hovered:
                return
            self._hovered.add(screen)
            if screen != self.app.current_screen:
                self._set_colors(screen, COLORS["bg_input"], COLORS["fg_text"])
        else:
            if screen not in self._hovered:
                return
            self._hovered.discard(screen)
            self._update_style(screen)
    
    def _set_colors(self, screen, bg, fg, icon_fg=None):
        """Set colors for a button. Icon keeps accent color unless specified."""
        try:
            self.buttons[screen].configure(bg=bg)
            self._icons[screen].configure(bg=bg, fg=icon_fg or COLORS["accent"])
            self._labels[screen].configure(bg=bg, fg=fg)
        except Exception:
            pass
    
    def _update_style(self, screen):
        """Update button style based on active screen."""
        if screen == self.app.current_screen:
            # Active: accent bg, dark text, white icon
            self._set_colors(screen, COLORS["accent"], COLORS["text_dark"], COLORS["text_dark"])
        else:
            # Inactive: panel bg, normal text, accent icon
            self._set_colors(screen, COLORS["bg_panel"], COLORS["fg_text"], COLORS["accent"])

    def update_btn_style(self, btn, screen_name):
        """Legacy method for compatibility."""
        self._update_style(screen_name)

    def update_indicators(self):
        """Update indicators on navigation buttons."""
        try:
            # Home sessions indicator
            session_count = len(getattr(self.app.sessions, "sessions", {}) or {})
            home_text = f"Home ({session_count})" if session_count > 0 else "Home"
            if "home" in self._labels:
                current = self._labels["home"].cget("text")
                if current != home_text:
                    self._labels["home"].config(text=home_text)
            
            # Log monitor active indicator
            log_on = self.app.log_monitor_state.monitor and self.app.log_monitor_state.monitor.is_running()
            log_text = "Log Monitor 🟢" if log_on else "Log Monitor"
            if "log_monitor" in self._labels:
                current = self._labels["log_monitor"].cget("text")
                if current != log_text:
                    self._labels["log_monitor"].config(text=log_text)
        except Exception:
            pass

    def apply_theme(self):
        """Update all buttons for theme switch."""
        try:
            self.frame.config(bg=COLORS["bg_panel"])
            for screen in self.buttons:
                self._update_style(screen)
        except Exception:
            pass
