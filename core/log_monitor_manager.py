"""
Log Monitor Management for NWN Manager.

This module handles all log monitoring operations including:
- Discord webhook notifications for keywords (Spy Mode)
- Open Wounds (Slayer) detection and auto-key press (Automation Mode)
- Log monitor lifecycle (start/stop/toggle)
"""

import time
import threading
import ctypes
import ctypes.wintypes
from typing import Optional

from core.error_handler import ErrorHandler
import tkinter as tk
from utils.log_monitor import LogMonitor
from ui.ui_base import COLORS
from utils.win_automation import user32, get_hwnd_from_pid, KEYEVENTF_KEYUP


class LogMonitorManager:
    """
    Manages log monitoring, Spy mode, and Automation (Slayer/Fog) for NWN Manager.
    """
    
    def __init__(self, app):
        self.app = app
        self._pending_open_wounds_press: Optional[str] = None
        self._last_open_wounds_activation: float = 0.0
        self._last_auto_fog_ts: Optional[str] = None
        self._lm_save_after_id: Optional[str] = None

    def initialize_state(self):
        """Initialize log monitor-related state on the app (idempotent)."""
        if getattr(self.app, "_log_monitor_state_initialized", False):
            return

        import os
        import tkinter as tk
        from app import LogMonitorState
        
        cfg = self.app.log_monitor_state.config if hasattr(self.app, 'log_monitor_state') else {}
        
        # Calculate default log path if empty
        log_path = cfg.get("log_path", "")
        if not log_path:
            docs = os.path.join(os.path.expanduser("~"), "Documents")
            nwn_docs = os.path.join(docs, "Neverwinter Nights")
            log_path = os.path.join(nwn_docs, "logs", "nwClientLog1.txt")
            if not os.path.exists(log_path):
                log_path = os.path.join(nwn_docs, "logs")

        enabled_var = tk.BooleanVar(value=cfg.get("enabled", False))
        spy_enabled_var = tk.BooleanVar(value=cfg.get("spy_enabled", False))
        auto_fog_enabled_var = tk.BooleanVar(value=cfg.get("auto_fog", {}).get("enabled", False))
        open_wounds_enabled_var = tk.BooleanVar(value=cfg.get("open_wounds", {}).get("enabled", False))
        log_match_var = tk.StringVar(value="")
        log_path_var = tk.StringVar(value=log_path)
        mention_here_var = tk.BooleanVar(value=cfg.get("mention_here", False))
        mention_everyone_var = tk.BooleanVar(value=cfg.get("mention_everyone", False))

        self.app.log_monitor_state = LogMonitorState(
            config={
                "enabled": cfg.get("enabled", False),
                "spy_enabled": cfg.get("spy_enabled", False),
                "log_path": log_path,
                "webhooks": cfg.get("webhooks", []),
                "keywords": cfg.get("keywords", []),
                "mention_here": cfg.get("mention_here", False),
                "mention_everyone": cfg.get("mention_everyone", False),
                "auto_fog": cfg.get("auto_fog", {"enabled": False}),
                "open_wounds": cfg.get("open_wounds", {"enabled": False, "key": "F1"}),
            },
            enabled_var=enabled_var,
            spy_enabled_var=spy_enabled_var,
            log_match_var=log_match_var,
            log_path_var=log_path_var,
            auto_fog_enabled_var=auto_fog_enabled_var,
            open_wounds_enabled_var=open_wounds_enabled_var,
            mention_here_var=mention_here_var,
            mention_everyone_var=mention_everyone_var,
            monitor=None,
            slayer_monitor=None,
            slayer_hit_count=0,
        )

        self.app._log_monitor_state_initialized = True
    
    def on_log_match(self, text: str):
        """Callback when LogMonitor finds a keyword."""
        def _update():
            from datetime import datetime
            try:
                self.app.log_match_var.set(text)
                if hasattr(self.app, 'log_history_text') and self.app.log_history_text:
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    history_line = f"[{timestamp}] {text}\n"
                    self.app.log_history_text.config(state="normal")
                    self.app.log_history_text.insert("1.0", history_line)
                    self.app.log_history_text.config(state="disabled")
            except Exception: pass
        self.app.root.after(0, _update)

    def on_log_line(self, line: str):
        """Callback for every new line in log."""
        try:
            if self.app.log_monitor_state.config.get("enabled", False):
                self.app.root.after(0, lambda l=line: self._check_triggers(l))
        except Exception: pass

    def _check_triggers(self, line: str):
        self._handle_open_wounds_detection(line)
        self._handle_auto_fog_detection(line)

    def ensure_log_monitor(self):
        """Create or update LogMonitor object based on current config."""
        state = self.app.log_monitor_state
        spy_on = state.config.get("spy_enabled", False)
        auto_on = state.config.get("enabled", False)
        
        if not state.monitor:
            state.monitor = LogMonitor(
                state.config["log_path"],
                state.config["keywords"],
                state.config["webhooks"],
                on_error=lambda e: self.app.log_error("LogMonitor", e),
                on_match=self.on_log_match,
                on_line=self.on_log_line,
                slayer_mode=state.open_wounds_enabled_var.get() if state.open_wounds_enabled_var else False,
                spy_enabled=spy_on,
                mention_here=state.mention_here_var.get() if state.mention_here_var else False,
                mention_everyone=state.mention_everyone_var.get() if state.mention_everyone_var else False,
            )
        else:
            state.monitor.on_match = self.on_log_match
            state.monitor.on_line = self.on_log_line
            state.monitor.set_slayer_mode(state.open_wounds_enabled_var.get() if state.open_wounds_enabled_var else False)
            state.monitor.set_spy_enabled(spy_on)
            state.monitor.update_config(
                log_path=state.config["log_path"],
                keywords=state.config["keywords"],
                webhooks=state.config["webhooks"],
                mention_here=state.mention_here_var.get() if state.mention_here_var else False,
                mention_everyone=state.mention_everyone_var.get() if state.mention_everyone_var else False,
            )

    def _save_config(self):
        """Save all log-related settings into app.settings"""
        state = self.app.log_monitor_state
        
        # Update path and vars
        if state.enabled_var: state.config["enabled"] = state.enabled_var.get()
        if state.spy_enabled_var: state.config["spy_enabled"] = state.spy_enabled_var.get()
        if state.log_path_var: state.config["log_path"] = state.log_path_var.get()
        if state.mention_here_var: state.config["mention_here"] = state.mention_here_var.get()
        if state.mention_everyone_var: state.config["mention_everyone"] = state.mention_everyone_var.get()

        # Update keywords from text widget if it exists
        try:
            if hasattr(state, 'keywords_text') and state.keywords_text:
                kw_text = state.keywords_text.get("1.0", tk.END).strip()
                state.config["keywords"] = [line.strip() for line in kw_text.splitlines() if line.strip()]
        except Exception: pass
            
        # Update webhooks from text widget ONLY if it's available (legacy mode)
        # In new UI, webhooks are updated directly in config by buttons.
        try:
            if hasattr(state, 'webhooks_text') and state.webhooks_text:
                wh_text = state.webhooks_text.get("1.0", tk.END).strip()
                if wh_text:
                    state.config["webhooks"] = [line.strip() for line in wh_text.splitlines() if line.strip()]
        except Exception: pass
            
        if state.auto_fog_enabled_var:
            state.config["auto_fog"] = {"enabled": state.auto_fog_enabled_var.get()}

        if state.open_wounds_enabled_var:
            state.config["open_wounds"] = {
                "enabled": state.open_wounds_enabled_var.get(),
                "key": state.open_wounds_key_var.get() if state.open_wounds_key_var else "F1"
            }

        # Save to disk
        self.app.settings.log_monitor = self.app.settings.log_monitor.from_dict(state.config)
        self.app.save_data()
        self.ensure_log_monitor()

    def start_log_monitor(self):
        try:
            has_sessions = bool(getattr(self.app.sessions, "sessions", None) and self.app.sessions.sessions)
        except Exception: has_sessions = False

        state = self.app.log_monitor_state
        spy_on = state.config.get("spy_enabled", False)
        auto_on = state.config.get("enabled", False)

        if not (spy_on or auto_on): return
        if not has_sessions:
            self.update_log_monitor_status_label(waiting=True)
            return

        self.ensure_log_monitor()
        if state.monitor and not state.monitor.is_running():
            print(">>> ЗАПУСК ПОТОКА МОНИТОРИНГА (Independent) <<<")
            state.monitor.start()
        
        self._stop_slayer_monitor()
        self.update_log_monitor_status_label()

    def stop_log_monitor(self, force=False):
        state = self.app.log_monitor_state
        spy_on = state.config.get("spy_enabled", False)
        auto_on = state.config.get("enabled", False)

        if force or (not spy_on and not auto_on):
            if state.monitor and state.monitor.is_running():
                state.monitor.stop()
            self.update_log_monitor_status_label()
            self._ensure_slayer_if_enabled()
        else:
            self.ensure_log_monitor()

    def on_log_monitor_toggle(self):
        state = self.app.log_monitor_state
        if not state.enabled_var: return
        enabled = state.enabled_var.get()
        state.config["enabled"] = enabled
        self._save_config()
        self.update_slayer_ui_state()
        if enabled: self.start_log_monitor()
        else: self.stop_log_monitor()

    def toggle_spy_enabled(self, force_state: Optional[bool] = None):
        try:
            state = self.app.log_monitor_state
            old_state = state.config.get("spy_enabled", False)
            new_state = not old_state if force_state is None else force_state
            state.config["spy_enabled"] = new_state
            if state.spy_enabled_var: state.spy_enabled_var.set(new_state)
            
            self._save_config()
            if new_state: self.start_log_monitor()
            else: self.stop_log_monitor()
            
            if hasattr(self.app, 'status_bar_comp'): self.app.status_bar_comp.update()
        except Exception: pass

    def update_log_monitor_status_label(self, waiting: bool = False):
        try:
            state = self.app.log_monitor_state
            running = state.monitor.is_running() if state.monitor else False
            spy_on = state.config.get("spy_enabled", False)
            auto_on = state.config.get("enabled", False)
            
            if running:
                text = "● Running"
                fg = COLORS["success"]
            elif waiting or ((spy_on or auto_on) and not running):
                text = "● Waiting for game"
                fg = COLORS["accent"]
            else:
                text = "● Stopped"
                fg = COLORS["fg_dim"]

            if hasattr(self.app, "log_monitor_status"):
                self.app.log_monitor_status.config(text=f"Automation: {'Running' if auto_on and running else 'Stopped'}", 
                                                 fg=COLORS["success"] if auto_on and running else COLORS["danger"])
            if hasattr(self.app, "log_monitor_status_lbl") and self.app.log_monitor_status_lbl:
                self.app.log_monitor_status_lbl.config(text=text, fg=fg)
        except Exception: pass

    def update_slayer_ui_state(self):
        try:
            state = self.app.log_monitor_state
            slayer_on = state.config.get("open_wounds", {}).get("enabled", False)
            log_running = state.monitor and state.monitor.is_running()
            slayer_active = slayer_on and (log_running or (state.slayer_monitor and state.slayer_monitor.is_running()))
            if hasattr(self.app, "ow_frame"):
                color = COLORS["warning"] if slayer_active else (COLORS["accent"] if slayer_on else COLORS["fg_dim"])
                self.app.ow_frame.config(fg=color)
        except Exception: pass

    def _ensure_slayer_if_enabled(self):
        try:
            state = self.app.log_monitor_state
            slayer_on = state.config.get("open_wounds", {}).get("enabled", False)
            main_running = state.monitor and state.monitor.is_running()
            if slayer_on and not main_running: self._start_slayer_monitor()
            elif not slayer_on: self._stop_slayer_monitor()
        except Exception: pass

    def _start_slayer_monitor(self):
        try:
            has_sessions = bool(getattr(self.app.sessions, "sessions", None) and self.app.sessions.sessions)
            if not has_sessions or (self.app.log_monitor_state.monitor and self.app.log_monitor_state.monitor.is_running()): return
            log_path = self.app.log_monitor_state.config.get("log_path", "")
            if not log_path: return
            if not self.app.log_monitor_state.slayer_monitor:
                self.app.log_monitor_state.slayer_monitor = LogMonitor(log_path, [], [], on_line=self.on_log_line, slayer_mode=True)
            else:
                self.app.log_monitor_state.slayer_monitor.update_config(log_path=log_path)
            if not self.app.log_monitor_state.slayer_monitor.is_running():
                self.app.log_monitor_state.slayer_monitor.start()
        except Exception: pass

    def _stop_slayer_monitor(self):
        if self.app.log_monitor_state.slayer_monitor and self.app.log_monitor_state.slayer_monitor.is_running():
            self.app.log_monitor_state.slayer_monitor.stop()

    def _handle_open_wounds_detection(self, line: str):
        if not line or "open wounds hit" not in line.lower(): return
        cfg = self.app.log_monitor_state.config.get("open_wounds", {})
        if not cfg.get("enabled"): return
        current_time = time.time()
        if current_time - self._last_open_wounds_activation < 2.0: return
        self._last_open_wounds_activation = current_time
        self._send_function_key_to_active_session(cfg.get("key", "F1"))
        self.app.log_monitor_state.slayer_hit_count += 1
        self._update_slayer_hit_counter_ui()

    def _handle_auto_fog_detection(self, line: str):
        if not line or "You are now in a Full PVP Area." not in line: return
        cfg = self.app.log_monitor_state.config.get("auto_fog", {})
        if not cfg.get("enabled"): return
        import re
        ts_match = re.search(r'\[.*?(\d{2}:\d{2}:\d{2})\]', line)
        ts = ts_match.group(1) if ts_match else None
        if ts and ts == self._last_auto_fog_ts: return
        self._last_auto_fog_ts = ts
        if len(getattr(self.app.sessions, 'sessions', {}) or {}) == 1:
            threading.Thread(target=lambda: self._send_console_command("mainscene.fog 0"), daemon=True).start()

    def _send_console_command(self, command: str):
        try:
            from utils.win_automation import press_key_by_name, get_keyboard_layout, set_keyboard_layout
            hwnd = self._focus_game_by_pid()
            if not hwnd: return
            hkl = get_keyboard_layout(hwnd)
            if hkl != 0x0409: 
                set_keyboard_layout(hwnd, 0x0409)
                time.sleep(0.15)
            try:
                if hasattr(self.app, "multi_hotkey_manager"): self.app.multi_hotkey_manager.pause()
                press_key_by_name("`")
                time.sleep(0.1)
                for char in command:
                    c = "SPACE" if char == " " else ("." if char == "." else char)
                    press_key_by_name(c, hold_time=0.01)
                time.sleep(0.02)
                press_key_by_name("ENTER", hold_time=0.01)
            finally:
                if hasattr(self.app, "multi_hotkey_manager"): self.app.multi_hotkey_manager.resume()
                if hkl != 0x0409: set_keyboard_layout(hwnd, hkl)
        except Exception: pass

    def _focus_game_by_pid(self):
        sess = getattr(self.app.sessions, 'sessions', None) or {}
        for pid in sess.values():
            hwnd = get_hwnd_from_pid(int(pid))
            if hwnd:
                user32.SetForegroundWindow(hwnd)
                return hwnd
        return None

    def _update_slayer_hit_counter_ui(self):
        try:
            if hasattr(self.app, 'status_bar_labels') and "slayer_hits" in self.app.status_bar_labels:
                self.app.status_bar_labels["slayer_hits"].config(text=f"({self.app.log_monitor_state.slayer_hit_count} hits)", fg=COLORS["warning"])
            if hasattr(self.app, 'slayer_counter_label'):
                self.app.slayer_counter_label.config(text=f"Hits: {self.app.log_monitor_state.slayer_hit_count}")
        except Exception: pass

    def _send_function_key_to_active_session(self, key_name: str):
        try:
            num = int(key_name[1:])
            vk = 0x6F + num
            hwnd = self._focus_game_by_pid()
            if hwnd: time.sleep(0.05)
            self._send_key_via_sendinput(vk, num)
        except Exception: pass

    def _send_key_via_sendinput(self, vk: int, fkey_num: int):
        try:
            scan = {1:0x3B, 2:0x3C, 3:0x3D, 4:0x3E, 5:0x3F, 6:0x40, 7:0x41, 8:0x42, 9:0x43, 10:0x44, 11:0x57, 12:0x58}.get(fkey_num, 0)
            class KBD(ctypes.Structure): _fields_ = [("wVk",ctypes.wintypes.WORD),("wScan",ctypes.wintypes.WORD),("dwFlags",ctypes.wintypes.DWORD),("time",ctypes.wintypes.DWORD),("dwExtraInfo",ctypes.POINTER(ctypes.c_ulong))]
            class INP(ctypes.Structure): _fields_ = [("type",ctypes.wintypes.DWORD),("ki",KBD),("padding",ctypes.c_ubyte*8)]
            for flags in [0x0008, 0x0008|0x0002]:
                i = INP(type=1, ki=KBD(wVk=vk, wScan=scan, dwFlags=flags))
                user32.SendInput(1, ctypes.byref(i), ctypes.sizeof(INP))
                if flags == 0x0008: time.sleep(0.05)
        except Exception: pass

    def browse_log_path(self):
        from tkinter import filedialog
        path = filedialog.askopenfilename(filetypes=[("Log files", "*.txt *.log"), ("All files", "*.*")])
        if path and self.app.log_monitor_state.log_path_var:
            self.app.log_monitor_state.log_path_var.set(path)
            self._save_config()

    def save_log_monitor_settings(self, silent: bool = False):
        try:
            self._save_config()
            if not silent: messagebox.showinfo("Success", "Settings saved!")
        except Exception as e:
            if not silent: messagebox.showerror("Error", str(e))

    def schedule_save_log_monitor_settings(self, delay_ms: int = 500):
        if hasattr(self, "_lm_save_after_id") and self._lm_save_after_id:
            try: self.app.root.after_cancel(self._lm_save_after_id)
            except Exception: pass
        self._lm_save_after_id = self.app.root.after(delay_ms, self._save_config)
