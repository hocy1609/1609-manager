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
            log_on = self.app.log_monitor and self.app.log_monitor.is_running()
            log_text = "📊 Log: On" if log_on else "📊 Log: Off"
            log_fg = COLORS["success"] if log_on else COLORS["fg_dim"]
            self.labels["log_monitor"].config(text=log_text, fg=log_fg)
            
            # Slayer status
            slayer_cfg = self.app.log_monitor_config.get("open_wounds", {})
            slayer_enabled = slayer_cfg.get("enabled", False)
            slayer_monitor_on = self.app.slayer_monitor and self.app.slayer_monitor.is_running()
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
            hits_text = f"({self.app.slayer_hit_count} hits)"
            hits_fg = COLORS["warning"] if self.app.slayer_hit_count > 0 else COLORS["fg_dim"]
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
    def __init__(self, app, parent):
        self.app = app
        self.parent = parent
        self.buttons = {}
        
        self.frame = tk.Frame(self.parent, bg=COLORS["bg_panel"])
        self.frame.pack(side="left", padx=20, pady=10)
        
        # (text, screen, tooltip)
        btn_defs = [
            ("🏠 Home", "home", "Главный экран - управление аккаунтами и запуск игры"),
            ("🔨 Craft", "craft", "Автокрафт и управление макросами"),
            ("⚙️ Settings", "settings", "Настройки приложения"),
            ("📊 Log Monitor", "log_monitor", "Мониторинг лога игры и Slayer"),
            ("❓ Help", "help", "Справка и горячие клавиши"),
        ]
        
        for text, screen, tooltip_text in btn_defs:
            btn = tk.Button(
                self.frame,
                text=text,
                command=lambda s=screen: self.app.show_screen(s),
                bg=COLORS["bg_panel"],
                fg=COLORS["fg_text"],
                activebackground=COLORS["bg_input"],
                activeforeground=COLORS["fg_text"],
                bd=0,
                relief="flat",
                font=("Segoe UI", 10),
                padx=15,
                pady=8,
                cursor="hand2"
            )
            btn.pack(side="left", padx=3)
            # Hover effects
            btn.bind("<Enter>", lambda e, b=btn: b.configure(bg=COLORS["bg_input"]))
            btn.bind("<Leave>", lambda e, b=btn, s=screen: self.update_btn_style(b, s))
            self.buttons[screen] = btn
            # Add tooltip
            ToolTip(btn, tooltip_text)

    def update_btn_style(self, btn, screen_name):
        """Update button style based on whether it's the active screen"""
        if screen_name == self.app.current_screen:
            btn.configure(bg=COLORS["accent"], fg=COLORS["text_dark"])
        else:
            btn.configure(bg=COLORS["bg_panel"], fg=COLORS["fg_text"])

    def update_indicators(self):
        """Update indicators on navigation buttons (e.g. session count)"""
        try:
            # Home sessions indicator
            session_count = len(getattr(self.app.sessions, "sessions", {}) or {})
            home_text = f"🏠 Home ({session_count})" if session_count > 0 else "🏠 Home"
            if "home" in self.buttons:
                self.buttons["home"].config(text=home_text)
            
            # Log monitor active indicator
            log_on = self.app.log_monitor and self.app.log_monitor.is_running()
            log_text = "📊 Log Monitor 🟢" if log_on else "📊 Log Monitor"
            if "log_monitor" in self.buttons:
                self.buttons["log_monitor"].config(text=log_text)
        except Exception:
            pass

    def apply_theme(self):
        """Update all buttons for theme switch"""
        self.frame.config(bg=COLORS["bg_panel"])
        for screen, btn in self.buttons.items():
            self.update_btn_style(btn, screen)
