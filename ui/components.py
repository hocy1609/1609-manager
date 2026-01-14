import tkinter as tk
from tkinter import ttk
import os
from ui.ui_base import COLORS, TitleBarButton, ToolTip

class TitleBar:
    def __init__(self, app, parent):
        self.app = app
        self.parent = parent
        self.root = app.root
        self._drag_data = {"x": 0, "y": 0}
        
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

        # Buttons are packed from right to left: Close -> Minimize -> Settings
        self.close_btn = TitleBarButton(
            self.frame, "✕", self.app.close_app_window, hover_color=COLORS["danger"]
        )
        self.close_btn.pack(side="right", fill="y")

        self.min_btn = TitleBarButton(self.frame, "_", self.app.minimize_window)
        self.min_btn.pack(side="right", fill="y")

        # Settings button
        self.settings_btn = TitleBarButton(self.frame, "⚙", self.app.open_settings)
        self.settings_btn.pack(side="right", fill="y")
        ToolTip(self.settings_btn, "Настройки")

    def start_move(self, event):
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y

    def do_move(self, event):
        x = self.root.winfo_x() + (event.x - self._drag_data["x"])
        y = self.root.winfo_y() + (event.y - self._drag_data["y"])
        self.root.geometry(f"+{x}+{y}")


class StatusBar:
    def __init__(self, app, parent):
        self.app = app
        self.parent = parent
        self.labels = {}
        
        self.frame = tk.Frame(self.parent, bg=COLORS["bg_panel"], height=28)
        self.frame.pack(fill="x", side="bottom")
        self.frame.pack_propagate(False)
        
        # Left side: Sessions count
        left_frame = tk.Frame(self.frame, bg=COLORS["bg_panel"])
        left_frame.pack(side="left", padx=15, pady=4)
        
        self.labels["sessions"] = tk.Label(
            left_frame,
            text="🎮 Sessions: 0",
            bg=COLORS["bg_panel"],
            fg=COLORS["fg_dim"],
            font=("Segoe UI", 9)
        )
        self.labels["sessions"].pack(side="left")
        ToolTip(self.labels["sessions"], "Количество запущенных игровых сессий")
        
        # Separator
        tk.Frame(self.frame, bg=COLORS["border"], width=1).pack(side="left", fill="y", padx=10, pady=4)
        
        # Log Monitor status (clickable toggle)
        self.labels["log_monitor"] = tk.Label(
            self.frame,
            text="📊 Log: Off",
            bg=COLORS["bg_panel"],
            fg=COLORS["fg_dim"],
            font=("Segoe UI", 9),
            cursor="hand2"
        )
        self.labels["log_monitor"].pack(side="left", padx=5)
        self.labels["log_monitor"].bind("<Button-1>", lambda e: self._toggle_log_monitor())
        ToolTip(self.labels["log_monitor"], "Клик для вкл/выкл мониторинга лога")
        
        # Separator
        tk.Frame(self.frame, bg=COLORS["border"], width=1).pack(side="left", fill="y", padx=10, pady=4)
        
        self._create_slayer_labels()
        
    def _create_slayer_labels(self):
        # Slayer status (clickable toggle)
        self.labels["slayer"] = tk.Label(
            self.frame,
            text="⚔️ Slayer: Off",
            bg=COLORS["bg_panel"],
            fg=COLORS["fg_dim"],
            font=("Segoe UI", 9),
            cursor="hand2"
        )
        self.labels["slayer"].pack(side="left", padx=5)
        self.labels["slayer"].bind("<Button-1>", lambda e: self._toggle_slayer())
        ToolTip(self.labels["slayer"], "Клик для вкл/выкл Open Wounds")
        
        # Slayer hit counter
        self.labels["slayer_hits"] = tk.Label(
            self.frame,
            text="(0 hits)",
            bg=COLORS["bg_panel"],
            fg=COLORS["fg_dim"],
            font=("Segoe UI", 9)
        )
        self.labels["slayer_hits"].pack(side="left", padx=(0, 5))
        ToolTip(self.labels["slayer_hits"], "Счётчик срабатываний Slayer за сессию")
        
        # Separator before Hotkeys
        tk.Frame(self.frame, bg=COLORS["border"], width=1).pack(side="left", fill="y", padx=10, pady=4)
        
        # Hotkeys status (clickable toggle)
        self.labels["hotkeys"] = tk.Label(
            self.frame,
            text="⌨️ Hotkeys: Off",
            bg=COLORS["bg_panel"],
            fg=COLORS["fg_dim"],
            font=("Segoe UI", 9),
            cursor="hand2"
        )
        self.labels["hotkeys"].pack(side="left", padx=5)
        self.labels["hotkeys"].bind("<Button-1>", lambda e: self._toggle_hotkeys())
        ToolTip(self.labels["hotkeys"], "Клик для вкл/выкл горячих клавиш")
        
        # Separator before Auto-Fog
        tk.Frame(self.frame, bg=COLORS["border"], width=1).pack(side="left", fill="y", padx=10, pady=4)
        
        # Auto-Fog status (clickable toggle)
        self.labels["auto_fog"] = tk.Label(
            self.frame,
            text="🌫️ Fog: Off",
            bg=COLORS["bg_panel"],
            fg=COLORS["fg_dim"],
            font=("Segoe UI", 9),
            cursor="hand2"
        )
        self.labels["auto_fog"].pack(side="left", padx=5)
        self.labels["auto_fog"].bind("<Button-1>", lambda e: self._toggle_auto_fog())
        ToolTip(self.labels["auto_fog"], "Клик для вкл/выкл Auto-Fog")
    
    def _toggle_hotkeys(self):
        """Toggle hotkeys enabled state on click."""
        try:
            print("[StatusBar] _toggle_hotkeys clicked")
            hotkeys_cfg = getattr(self.app, 'hotkeys_config', {})
            new_enabled = not hotkeys_cfg.get('enabled', False)
            self.app.hotkeys_config['enabled'] = new_enabled
            print(f"[StatusBar] Hotkeys enabled = {new_enabled}")
            
            if new_enabled:
                # Start hotkeys using _apply_saved_hotkeys method
                if hasattr(self.app, '_apply_saved_hotkeys'):
                    self.app._apply_saved_hotkeys()
                    print("[StatusBar] Hotkeys applied via _apply_saved_hotkeys")
            else:
                # Stop hotkeys
                if hasattr(self.app, 'multi_hotkey_manager'):
                    print("[StatusBar] Stopping hotkeys")
                    self.app.multi_hotkey_manager.unregister_all()
            
            # Save settings
            if hasattr(self.app, 'save_data'):
                self.app.save_data()
                print("[StatusBar] Settings saved")
        except Exception as e:
            print(f"[StatusBar] Error in _toggle_hotkeys: {e}")
    
    def _toggle_log_monitor(self):
        """Toggle log monitor on click."""
        try:
            if hasattr(self.app, 'log_monitor_manager'):
                # Check if running
                is_running = self.app.log_monitor_state.monitor and self.app.log_monitor_state.monitor.is_running()
                if is_running:
                    self.app.log_monitor_manager.stop_log_monitor()
                    print("[StatusBar] Log Monitor stopped")
                else:
                    self.app.log_monitor_manager.start_log_monitor()
                    print("[StatusBar] Log Monitor started")
        except Exception as e:
            print(f"[StatusBar] Error in _toggle_log_monitor: {e}")
    
    def _toggle_slayer(self):
        """Toggle Slayer (Open Wounds) on click."""
        try:
            ow_cfg = self.app.log_monitor_state.config.get("open_wounds", {})
            new_enabled = not ow_cfg.get("enabled", False)
            self.app.log_monitor_state.config["open_wounds"]["enabled"] = new_enabled
            print(f"[StatusBar] Slayer enabled = {new_enabled}")
            
            # Update UI state
            if hasattr(self.app, 'log_monitor_manager'):
                self.app.log_monitor_manager.update_slayer_ui_state()
            
            # Start/stop slayer monitor if needed
            if hasattr(self.app, 'log_monitor_manager'):
                self.app.log_monitor_manager._ensure_slayer_if_enabled()
            
            # Save
            if hasattr(self.app, 'save_data'):
                self.app.save_data()
        except Exception as e:
            print(f"[StatusBar] Error in _toggle_slayer: {e}")
    
    def _toggle_auto_fog(self):
        """Toggle Auto-Fog on click."""
        try:
            af_cfg = self.app.log_monitor_state.config.get("auto_fog", {})
            new_enabled = not af_cfg.get("enabled", False)
            self.app.log_monitor_state.config["auto_fog"]["enabled"] = new_enabled
            print(f"[StatusBar] Auto-Fog enabled = {new_enabled}")
            
            # Save
            if hasattr(self.app, 'save_data'):
                self.app.save_data()
        except Exception as e:
            print(f"[StatusBar] Error in _toggle_auto_fog: {e}")

    def update(self):
        """Update all status bar labels"""
        try:
            # Sessions count
            session_count = len(getattr(self.app.sessions, "sessions", {}) or {})
            sessions_text = f"🎮 Sessions: {session_count}"
            sessions_fg = COLORS["success"] if session_count > 0 else COLORS["fg_dim"]
            self.labels["sessions"].config(text=sessions_text, fg=sessions_fg)
            
            # Log Monitor status
            log_on = self.app.log_monitor_state.monitor and self.app.log_monitor_state.monitor.is_running()
            log_text = "📊 Log: On" if log_on else "📊 Log: Off"
            log_fg = COLORS["success"] if log_on else COLORS["fg_dim"]
            self.labels["log_monitor"].config(text=log_text, fg=log_fg)
            
            # Slayer status
            slayer_cfg = self.app.log_monitor_state.config.get("open_wounds", {})
            slayer_enabled = slayer_cfg.get("enabled", False)
            slayer_monitor_on = self.app.log_monitor_state.slayer_monitor and self.app.log_monitor_state.slayer_monitor.is_running()
            slayer_active = slayer_enabled and (log_on or slayer_monitor_on)
            
            if slayer_active:
                slayer_text = f"⚔️ Slayer: On ({slayer_cfg.get('key', 'F1')})"
                slayer_fg = COLORS["warning"]
            elif slayer_enabled:
                slayer_text = "⚔️ Slayer: Waiting"
                slayer_fg = COLORS["accent"]
            else:
                slayer_text = "⚔️ Slayer: Off"
                slayer_fg = COLORS["fg_dim"]
            self.labels["slayer"].config(text=slayer_text, fg=slayer_fg)
            
            # Slayer hits
            hits_text = f"({self.app.log_monitor_state.slayer_hit_count} hits)"
            hits_fg = COLORS["warning"] if self.app.log_monitor_state.slayer_hit_count > 0 else COLORS["fg_dim"]
            self.labels["slayer_hits"].config(text=hits_text, fg=hits_fg)
            
            # Hotkeys status
            hotkeys_cfg = getattr(self.app, 'hotkeys_config', {})
            hotkeys_enabled = hotkeys_cfg.get('enabled', False)
            hotkeys_active = hasattr(self.app, 'multi_hotkey_manager') and self.app.multi_hotkey_manager._running
            
            if hotkeys_active:
                binds_count = len([b for b in hotkeys_cfg.get('binds', []) if b.get('enabled', True)])
                hotkeys_text = f"⌨️ Hotkeys: On ({binds_count})"
                hotkeys_fg = COLORS["success"]
            elif hotkeys_enabled:
                hotkeys_text = "⌨️ Hotkeys: Waiting"
                hotkeys_fg = COLORS["accent"]
            else:
                hotkeys_text = "⌨️ Hotkeys: Off"
                hotkeys_fg = COLORS["fg_dim"]
            self.labels["hotkeys"].config(text=hotkeys_text, fg=hotkeys_fg)
            
            # Auto-Fog status
            auto_fog_cfg = self.app.log_monitor_state.config.get("auto_fog", {})
            fog_enabled = auto_fog_cfg.get("enabled", False)
            log_on = self.app.log_monitor_state.monitor and self.app.log_monitor_state.monitor.is_running()
            fog_active = fog_enabled and log_on
            
            if fog_active:
                fog_text = "🌫️ Fog: On"
                fog_fg = COLORS["success"]
            elif fog_enabled:
                fog_text = "🌫️ Fog: Waiting"
                fog_fg = COLORS["accent"]
            else:
                fog_text = "🌫️ Fog: Off"
                fog_fg = COLORS["fg_dim"]
            self.labels["auto_fog"].config(text=fog_text, fg=fog_fg)
        except Exception:
            pass

    def apply_theme(self):
        """Update colors for theme switch"""
        self.frame.config(bg=COLORS["bg_panel"])
        for label in self.labels.values():
            label.config(bg=COLORS["bg_panel"])
            # Fg will be updated by next update() call which happens every second


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
        
        # (icon, text, screen, tooltip)
        btn_defs = [
            ("🏠", "Home", "home", "Главный экран - управление аккаунтами и запуск игры"),
            ("📊", "Log Monitor", "log_monitor", "Мониторинг лога игры"),
            ("⌨️", "Hotkeys", "hotkeys", "Настройка горячих клавиш"),
            ("🔨", "Craft", "craft", "Автокрафт и управление макросами"),
            ("❓", "Help", "help", "Справка и горячие клавиши"),
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
            icon_lbl = tk.Label(
                btn_frame,
                text=icon,
                bg=COLORS["bg_panel"],
                fg=COLORS["accent"],
                font=("Segoe UI Emoji", 12),
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
            
            # Tooltip
            ToolTip(btn_frame, tooltip_text)
    
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
