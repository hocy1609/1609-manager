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
        
        # Log Monitor status
        self.labels["log_monitor"] = tk.Label(
            self.frame,
            text="📊 Log: Off",
            bg=COLORS["bg_panel"],
            fg=COLORS["fg_dim"],
            font=("Segoe UI", 9)
        )
        self.labels["log_monitor"].pack(side="left", padx=5)
        ToolTip(self.labels["log_monitor"], "Статус мониторинга лог-файла игры")
        
        # Separator
        tk.Frame(self.frame, bg=COLORS["border"], width=1).pack(side="left", fill="y", padx=10, pady=4)
        
        # Slayer status
        self.labels["slayer"] = tk.Label(
            self.frame,
            text="⚔️ Slayer: Off",
            bg=COLORS["bg_panel"],
            fg=COLORS["fg_dim"],
            font=("Segoe UI", 9)
        )
        self.labels["slayer"].pack(side="left", padx=5)
        ToolTip(self.labels["slayer"], "Автонажатие клавиши при Open Wounds")
        
        # Slayer hit counter
        self.labels["slayer_hits"] = tk.Label(
            self.frame,
            text="(0 hits)",
            bg=COLORS["bg_panel"],
            fg=COLORS["fg_dim"],
            font=("Segoe UI", 9)
        )
        self.labels["slayer_hits"].pack(side="left", padx=(0, 10))
        ToolTip(self.labels["slayer_hits"], "Счётчик срабатываний Slayer за сессию")

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
        except Exception:
            pass

    def apply_theme(self):
        """Update colors for theme switch"""
        self.frame.config(bg=COLORS["bg_panel"])
        for label in self.labels.values():
            label.config(bg=COLORS["bg_panel"])
            # Fg will be updated by next update() call which happens every second


class NavigationBar:
    """Navigation bar using Frame+Label structure to avoid tk.Button hover flickering with emoji."""
    
    def __init__(self, app, parent):
        self.app = app
        self.parent = parent
        self.buttons = {}  # screen -> frame widget
        self._labels = {}  # screen -> label widget
        self._hovered = set()  # Currently hovered buttons
        
        self.frame = tk.Frame(self.parent, bg=COLORS["bg_panel"])
        self.frame.pack(side="left", padx=20, pady=10)
        
        btn_defs = [
            ("🏠 Home", "home", "Главный экран - управление аккаунтами и запуск игры"),
            ("🔨 Craft", "craft", "Автокрафт и управление макросами"),
            ("⚙️ Settings", "settings", "Настройки приложения"),
            ("📊 Log Monitor", "log_monitor", "Мониторинг лога игры"),
            ("❓ Help", "help", "Справка и горячие клавиши"),
        ]
        
        for text, screen, tooltip_text in btn_defs:
            # Container frame acts as the button
            btn_frame = tk.Frame(
                self.frame,
                bg=COLORS["bg_panel"],
                cursor="hand2",
                padx=15,
                pady=8,
            )
            btn_frame.pack(side="left", padx=3)
            
            # Label inside frame shows text
            label = tk.Label(
                btn_frame,
                text=text,
                bg=COLORS["bg_panel"],
                fg=COLORS["fg_text"],
                font=("Segoe UI", 10),
                cursor="hand2",
            )
            label.pack()
            
            # Store references
            self.buttons[screen] = btn_frame
            self._labels[screen] = label
            
            # Bind click to both frame and label
            btn_frame.bind("<Button-1>", lambda e, s=screen: self._on_click(s))
            label.bind("<Button-1>", lambda e, s=screen: self._on_click(s))
            
            # Simple hover - bind to frame only, label inherits
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
    
    def _set_colors(self, screen, bg, fg):
        """Set colors for a button."""
        try:
            self.buttons[screen].configure(bg=bg)
            self._labels[screen].configure(bg=bg, fg=fg)
        except Exception:
            pass
    
    def _update_style(self, screen):
        """Update button style based on active screen."""
        if screen == self.app.current_screen:
            self._set_colors(screen, COLORS["accent"], COLORS["text_dark"])
        else:
            self._set_colors(screen, COLORS["bg_panel"], COLORS["fg_text"])

    def update_btn_style(self, btn, screen_name):
        """Legacy method for compatibility."""
        self._update_style(screen_name)

    def update_indicators(self):
        """Update indicators on navigation buttons."""
        try:
            # Home sessions indicator
            session_count = len(getattr(self.app.sessions, "sessions", {}) or {})
            home_text = f"🏠 Home ({session_count})" if session_count > 0 else "🏠 Home"
            if "home" in self._labels:
                current = self._labels["home"].cget("text")
                if current != home_text:
                    self._labels["home"].config(text=home_text)
            
            # Log monitor active indicator
            log_on = self.app.log_monitor_state.monitor and self.app.log_monitor_state.monitor.is_running()
            log_text = "📊 Log Monitor 🟢" if log_on else "📊 Log Monitor"
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
