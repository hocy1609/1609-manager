"""
Log Monitor Management for NWN Manager.

This module handles all log monitoring operations including:
- Discord webhook notifications for keywords
- Open Wounds (Slayer) detection and auto-key press
- Log monitor lifecycle (start/stop/toggle)
"""

import time
import ctypes
import ctypes.wintypes

from utils.log_monitor import LogMonitor
from ui.ui_base import COLORS
from utils.win_automation import user32, get_hwnd_from_pid, KEYEVENTF_KEYUP


class LogMonitorManager:
    """
    Manages log monitoring and Open Wounds (Slayer) detection for NWN Manager.
    
    Takes a reference to the main app to access its state and UI elements.
    """
    
    def __init__(self, app):
        """
        Initialize the LogMonitorManager.
        
        Args:
            app: Reference to the NWNManagerApp instance
        """
        self.app = app
    
    def on_log_match(self, text: str):
        """Callback when LogMonitor finds a keyword."""
        def _update():
            try:
                self.app.log_match_var.set(text)
            except Exception:
                pass
        self.app.root.after(0, _update)

    def on_log_line(self, line: str):
        """Callback for every new line in log - used for Open Wounds detection."""
        try:
            self.app.root.after(0, lambda l=line: self._handle_open_wounds_detection(l))
        except Exception:
            pass

    def ensure_log_monitor(self):
        """Create or update LogMonitor object based on current config."""
        # Check if slayer mode (Open Wounds) is enabled for high-priority polling
        state = self.app.log_monitor_state
        ow_cfg = state.config.get("open_wounds", {})
        slayer_mode = bool(ow_cfg.get("enabled", False))
        
        if not state.monitor:
            state.monitor = LogMonitor(
                state.config["log_path"],
                state.config["keywords"],
                state.config["webhooks"],
                on_error=lambda e: self.app.log_error("LogMonitor", e),
                on_match=self.on_log_match,
                on_line=self.on_log_line,
                slayer_mode=slayer_mode,
            )
        else:
            state.monitor.on_match = self.on_log_match
            state.monitor.on_line = self.on_log_line
            state.monitor.set_slayer_mode(slayer_mode)
            state.monitor.update_config(
                log_path=state.config["log_path"],
                keywords=state.config["keywords"],
                webhooks=state.config["webhooks"],
            )

    def start_log_monitor(self):
        """Start the log monitor if a game is running."""
        from tkinter import messagebox
        
        # Prevent starting monitor if no game is running
        try:
            has_sessions = bool(getattr(self.app.sessions, "sessions", None))
        except Exception:
            has_sessions = False

        if not has_sessions:
            try:
                messagebox.showinfo(
                    "Log Monitor",
                    "Cannot start log monitor: no running game detected.",
                    parent=self.app.root,
                )
            except Exception:
                pass
            try:
                if self.app.log_monitor_state.enabled_var:
                    self.app.log_monitor_state.enabled_var.set(False)
                self.app.log_monitor_state.config["enabled"] = False
                self.update_log_monitor_status_label()
            except Exception:
                pass
            return

        # Create or update monitor
        self.ensure_log_monitor()

        # Start thread if not running
        if self.app.log_monitor_state.monitor and not self.app.log_monitor_state.monitor.is_running():
            print(">>> ЗАПУСК ПОТОКА СЛЕЖЕНИЯ <<<")
            self.app.log_monitor_state.monitor.start()
        # Stop slayer monitor if log monitor is running (log monitor handles both)
        self._stop_slayer_monitor()
        # Update UI indicator and sync checkbox
        try:
            if self.app.log_monitor_state.enabled_var:
                self.app.log_monitor_state.enabled_var.set(True)
            self.update_log_monitor_status_label()
        except Exception:
            pass

    def stop_log_monitor(self):
        """Stop the log monitor."""
        if self.app.log_monitor_state.monitor and self.app.log_monitor_state.monitor.is_running():
            self.app.log_monitor_state.monitor.stop()
        try:
            if self.app.log_monitor_state.enabled_var:
                self.app.log_monitor_state.enabled_var.set(False)
            self.update_log_monitor_status_label()
        except Exception:
            pass
        # If slayer is still enabled, start slayer-only monitor
        self._ensure_slayer_if_enabled()

    def _ensure_slayer_if_enabled(self):
        """Start slayer-only monitor if slayer is enabled and log monitor is not running."""
        try:
            ow_cfg = self.app.log_monitor_state.config.get("open_wounds", {})
            slayer_enabled = ow_cfg.get("enabled", False)
            log_monitor_running = self.app.log_monitor_state.monitor and self.app.log_monitor_state.monitor.is_running()
            
            if slayer_enabled and not log_monitor_running:
                # Start slayer-only monitor
                self._start_slayer_monitor()
            elif not slayer_enabled:
                # Stop slayer monitor if slayer disabled
                self._stop_slayer_monitor()
        except Exception as e:
            self.app.log_error("_ensure_slayer_if_enabled", e)

    def _start_slayer_monitor(self):
        """Start a lightweight monitor just for Open Wounds detection."""
        try:
            # Don't start if no game running
            has_sessions = bool(getattr(self.app.sessions, "sessions", None) and self.app.sessions.sessions)
            if not has_sessions:
                return
            
            # Don't start if log monitor is already running (it handles slayer too)
            if self.app.log_monitor_state.monitor and self.app.log_monitor_state.monitor.is_running():
                return
            
            log_path = self.app.log_monitor_state.config.get("log_path", "")
            if not log_path:
                return
            
            if not self.app.log_monitor_state.slayer_monitor:
                self.app.log_monitor_state.slayer_monitor = LogMonitor(
                    log_path,
                    keywords=[],  # No keywords - slayer only
                    webhooks=[],  # No webhooks - slayer only
                    on_error=lambda e: self.app.log_error("SlayerMonitor", e),
                    on_match=None,  # No match callback
                    on_line=self.on_log_line,  # For Open Wounds detection
                    slayer_mode=True,  # High priority polling
                )
            else:
                self.app.log_monitor_state.slayer_monitor.update_config(log_path=log_path, keywords=[], webhooks=[])
                self.app.log_monitor_state.slayer_monitor.on_line = self.on_log_line
                self.app.log_monitor_state.slayer_monitor.set_slayer_mode(True)
            
            if not self.app.log_monitor_state.slayer_monitor.is_running():
                print(">>> ЗАПУСК SLAYER MONITOR <<<")
                self.app.log_monitor_state.slayer_monitor.start()
        except Exception as e:
            self.app.log_error("_start_slayer_monitor", e)

    def _stop_slayer_monitor(self):
        """Stop the slayer-only monitor."""
        try:
            if self.app.log_monitor_state.slayer_monitor and self.app.log_monitor_state.slayer_monitor.is_running():
                print(">>> ОСТАНОВКА SLAYER MONITOR <<<")
                self.app.log_monitor_state.slayer_monitor.stop()
        except Exception as e:
            self.app.log_error("_stop_slayer_monitor", e)

    def update_log_monitor_status_label(self):
        """Update the log monitor status indicator in UI."""
        try:
            running = self.app.log_monitor_state.monitor.is_running() if self.app.log_monitor_state.monitor else False
            if running:
                text = "● Running"
                fg = COLORS.get("success", "#00a000")
            else:
                text = "● Stopped"
                fg = COLORS.get("fg_dim", "#888888")

            if hasattr(self.app, "log_monitor_status_lbl") and self.app.log_monitor_status_lbl:
                self.app.log_monitor_status_lbl.config(text=text, fg=fg)
        except Exception as e:
            self.app.log_error("update_log_monitor_status_label", e)

    def _handle_open_wounds_detection(self, line: str):
        """If a log line indicates an Open Wounds hit, optionally press configured F-key."""
        try:
            if not line:
                return
            ll = line.lower()
            if "open wounds hit" in ll:
                cfg = self.app.log_monitor_state.config.get("open_wounds", {})
                if cfg and cfg.get("enabled"):
                    key = cfg.get("key", "F1")
                    self._send_function_key_to_active_session(key)
                    # Increment slayer hit counter
                    self.app.log_monitor_state.slayer_hit_count += 1
                    self._update_slayer_hit_counter_ui()
        except Exception as e:
            self.app.log_error("open_wounds_detection", e)
    
    def _update_slayer_hit_counter_ui(self):
        """Update slayer hit counter in UI."""
        try:
            # Update status bar
            if hasattr(self.app, 'status_bar_labels') and "slayer_hits" in self.app.status_bar_labels:
                hits_text = f"({self.app.log_monitor_state.slayer_hit_count} hits)"
                self.app.status_bar_labels["slayer_hits"].config(text=hits_text, fg=COLORS["warning"])
            # Update log monitor screen counter if exists
            if hasattr(self.app, 'slayer_counter_label'):
                self.app.slayer_counter_label.config(text=f"Hits: {self.app.log_monitor_state.slayer_hit_count}")
        except Exception:
            pass

    def _send_function_key_to_active_session(self, key_name: str):
        """Bring a running NWN session to foreground and send a function key (F1..F12)."""
        try:
            if not key_name:
                return
            key_name = key_name.strip().upper()
            if not key_name.startswith("F"):
                return
            try:
                num = int(key_name[1:])
            except Exception:
                return
            if num < 1 or num > 12:
                return

            # Virtual-key codes: VK_F1..VK_F12 are 0x70..0x7B
            vk = 0x6F + num

            # Get running session pid
            pid = None
            try:
                sess = getattr(self.app.sessions, 'sessions', None) or {}
                for k, v in sess.items():
                    pid = int(v)
                    break
            except Exception:
                pid = None

            # Set foreground window if we have pid
            if pid:
                try:
                    hwnd = get_hwnd_from_pid(pid)
                    if hwnd:
                        user32.SetForegroundWindow(hwnd)
                        time.sleep(0.05)
                except Exception:
                    pass

            # Send key using SendInput
            self._send_key_via_sendinput(vk, num)
        except Exception as e:
            self.app.log_error("send_function_key", e)

    def _send_key_via_sendinput(self, vk: int, fkey_num: int):
        """Send a key press using SendInput API."""
        try:
            # Scan codes for F1-F12
            scan_codes = {1: 0x3B, 2: 0x3C, 3: 0x3D, 4: 0x3E, 5: 0x3F, 6: 0x40, 
                          7: 0x41, 8: 0x42, 9: 0x43, 10: 0x44, 11: 0x57, 12: 0x58}
            scan = scan_codes.get(fkey_num, 0)
            
            INPUT_KEYBOARD = 1
            KEYEVENTF_SCANCODE = 0x0008
            KEYEVENTF_KEYUP_FLAG = 0x0002
            
            class KEYBDINPUT(ctypes.Structure):
                _fields_ = [
                    ("wVk", ctypes.wintypes.WORD),
                    ("wScan", ctypes.wintypes.WORD),
                    ("dwFlags", ctypes.wintypes.DWORD),
                    ("time", ctypes.wintypes.DWORD),
                    ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))
                ]
            
            class INPUT(ctypes.Structure):
                _fields_ = [
                    ("type", ctypes.wintypes.DWORD),
                    ("ki", KEYBDINPUT),
                    ("padding", ctypes.c_ubyte * 8)
                ]
            
            # Key down
            inp_down = INPUT()
            inp_down.type = INPUT_KEYBOARD
            inp_down.ki.wVk = vk
            inp_down.ki.wScan = scan
            inp_down.ki.dwFlags = KEYEVENTF_SCANCODE
            inp_down.ki.time = 0
            inp_down.ki.dwExtraInfo = None
            
            # Key up
            inp_up = INPUT()
            inp_up.type = INPUT_KEYBOARD
            inp_up.ki.wVk = vk
            inp_up.ki.wScan = scan
            inp_up.ki.dwFlags = KEYEVENTF_SCANCODE | KEYEVENTF_KEYUP_FLAG
            inp_up.ki.time = 0
            inp_up.ki.dwExtraInfo = None
            
            user32.SendInput(1, ctypes.byref(inp_down), ctypes.sizeof(INPUT))
            time.sleep(0.05)
            user32.SendInput(1, ctypes.byref(inp_up), ctypes.sizeof(INPUT))
        except Exception as e:
            # Fallback to keybd_event
            try:
                user32.keybd_event(vk, 0, 0, 0)
                time.sleep(0.03)
                user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)
            except Exception:
                pass

    def toggle_log_monitor_enabled(self):
        """Toggle log monitor on/off from UI."""
        from tkinter import messagebox
        
        try:
            enabled_var = self.app.log_monitor_state.enabled_var
            if not enabled_var:
                return
            enabled = bool(enabled_var.get())
            # If user tries to enable but no game is running — prevent it
            if enabled:
                has_sessions = bool(getattr(self.app.sessions, "sessions", None))
                if not has_sessions:
                    try:
                        messagebox.showinfo(
                            "Log Monitor",
                            "Cannot enable log monitor: no running game detected.",
                            parent=self.app.root,
                        )
                    except Exception:
                        pass
                    # Revert checkbox and do not save
                    try:
                        enabled_var.set(False)
                    except Exception:
                        pass
                    return

            # Persist desired state
            self.app.log_monitor_state.config["enabled"] = enabled
            self.app.log_monitor_state.config["enabled"] = enabled
            if hasattr(self.app, 'schedule_save'):
                self.app.schedule_save()
            else:
                self.app.save_data()

            # Update or create monitor
            self.ensure_log_monitor()

            if enabled:
                self.start_log_monitor()
            else:
                self.stop_log_monitor()
        except Exception as e:
            self.app.log_error("toggle_log_monitor_enabled", e)

    def open_log_monitor_dialog(self):
        """Open the log monitor configuration dialog."""
        from tkinter import messagebox
        from ui.dialogs import LogMonitorDialog
        
        def on_save_config(cfg: dict):
            try:
                want_enabled = bool(cfg.get("enabled", False))
            except Exception:
                want_enabled = False

            if want_enabled:
                has_sessions = bool(getattr(self.app.sessions, "sessions", None))
                if not has_sessions:
                    try:
                        messagebox.showinfo(
                            "Log Monitor",
                            "Cannot enable log monitor: no running game detected.",
                            parent=self.app.root,
                        )
                    except Exception:
                        pass
                    cfg["enabled"] = False

            # Save settings
            self.app.log_monitor_state.config.update(cfg)
            self.app.save_data()

            # Update monitor
            self.ensure_log_monitor()

            # Start/stop based on enabled state
            try:
                if self.app.log_monitor_state.config.get("enabled"):
                    self.start_log_monitor()
                else:
                    self.stop_log_monitor()
            except Exception as e:
                self.app.log_error("open_log_monitor_dialog.on_save_config", e)

        running = self.app.log_monitor_state.monitor.is_running() if self.app.log_monitor_state.monitor else False

        LogMonitorDialog(
            self.app.root,
            self.app.log_monitor_state.config,
            on_save_config,
            self.start_log_monitor,
            self.stop_log_monitor,
            is_running=running,
        )
