"""
Log Monitor Management for NWN Manager.

This module handles all log monitoring operations including:
- Discord webhook notifications for keywords
- Open Wounds (Slayer) detection and auto-key press
- Log monitor lifecycle (start/stop/toggle)
"""

import time
import threading
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

    def initialize_state(self):
        """Initialize log monitor-related state on the app (idempotent)."""
        if getattr(self.app, "_log_monitor_state_initialized", False):
            return

        from app import LogMonitorState

        self.app.log_monitor_state = LogMonitorState(
            config={
                "enabled": False,
                "log_path": "",
                "webhooks": [],
                "keywords": [],
            },
            monitor=None,
            slayer_monitor=None,
            slayer_hit_count=0,
        )

        self.app._log_monitor_state_initialized = True
    
    def on_log_match(self, text: str):
        """Callback when LogMonitor finds a keyword."""
        def _update():
            try:
                self.app.log_match_var.set(text)
            except Exception:
                pass
        self.app.root.after(0, _update)



    def on_log_line(self, line: str):
        """Callback for every new line in log - used for Open Wounds and Auto-Fog detection."""
        try:
            # Check for triggers concurrently
            self.app.root.after(0, lambda l=line: self._check_triggers(l))
        except Exception:
            pass

    def _check_triggers(self, line: str):
        """Check line against multiple triggers (Open Wounds, Auto-Fog)."""
        self._handle_open_wounds_detection(line)
        self._handle_auto_fog_detection(line)

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
        """Start the log monitor (waits for game if not running)."""
        # Check if game is running
        try:
            has_sessions = bool(getattr(self.app.sessions, "sessions", None))
        except Exception:
            has_sessions = False

        if not has_sessions:
            # No game running - mark as enabled but waiting
            try:
                if self.app.log_monitor_state.enabled_var:
                    self.app.log_monitor_state.enabled_var.set(True)
                self.update_log_monitor_status_label(waiting=True)
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

    def update_log_monitor_status_label(self, waiting: bool = False):
        """Update the log monitor status indicator in UI."""
        try:
            running = self.app.log_monitor_state.monitor.is_running() if self.app.log_monitor_state.monitor else False
            enabled = self.app.log_monitor_state.config.get("enabled", False)
            
            if running:
                text = "● Running"
                fg = COLORS.get("success", "#00a000")
            elif waiting or (enabled and not running):
                text = "● Waiting for game"
                fg = COLORS.get("accent", "#4a9eff")
            else:
                text = "● Stopped"
                fg = COLORS.get("fg_dim", "#888888")

            if hasattr(self.app, "log_monitor_status_lbl") and self.app.log_monitor_status_lbl:
                self.app.log_monitor_status_lbl.config(text=text, fg=fg)
        except Exception as e:
            self.app.log_error("update_log_monitor_status_label", e)

    def _handle_open_wounds_detection(self, line: str):
        """If a log line indicates an Open Wounds hit, optionally press configured F-key.
        
        Includes a 2-second cooldown to match game ability cooldown.
        If hit detected during cooldown, schedules delayed press for when cooldown ends.
        """
        try:
            if not line:
                return
            ll = line.lower()
            if "open wounds hit" in ll:
                cfg = self.app.log_monitor_state.config.get("open_wounds", {})
                if cfg and cfg.get("enabled"):
                    key = cfg.get("key", "F1")
                    current_time = time.time()
                    last_activation = getattr(self, '_last_open_wounds_activation', 0)
                    time_since_last = current_time - last_activation
                    
                    if time_since_last < 2.0:
                        # Still on cooldown - schedule delayed press for when cooldown ends
                        remaining_cooldown = 2.0 - time_since_last
                        delay_ms = int(remaining_cooldown * 1000) + 50  # +50ms buffer
                        
                        # Cancel any existing pending press
                        pending_id = getattr(self, '_pending_open_wounds_press', None)
                        if pending_id:
                            try:
                                self.app.root.after_cancel(pending_id)
                            except Exception:
                                pass
                        
                        # Schedule new pending press
                        self._pending_open_wounds_press = self.app.root.after(
                            delay_ms, 
                            lambda: self._execute_pending_open_wounds(key)
                        )
                        return
                    
                    # Cooldown is over - press immediately
                    self._last_open_wounds_activation = current_time
                    self._send_function_key_to_active_session(key)
                    
                    # Increment slayer hit counter
                    self.app.log_monitor_state.slayer_hit_count += 1
                    self._update_slayer_hit_counter_ui()
        except Exception as e:
            self.app.log_error("open_wounds_detection", e)

    def _handle_auto_fog_detection(self, line: str):
        """Detect 'You are now in a Full PVP Area.' and trigger Auto-Fog command."""
        try:
            if not line:
                return
            
            # Trigger text: "You are now in a Full PVP Area."
            if "You are now in a Full PVP Area." in line:
                # Deduplication: Check timestamp
                import re
                # Match [Sat Jan 10 02:55:15] or similar. We care about the time part.
                # Regex for time HH:MM:SS inside brackets
                ts_match = re.search(r'\[.*?(\d{2}:\d{2}:\d{2})\]', line)
                current_ts = ts_match.group(1) if ts_match else None
                
                # If we found a timestamp, check against last processed
                if current_ts:
                    last_ts = getattr(self, "_last_auto_fog_ts", None)
                    if last_ts == current_ts:
                        print(f"[LogMonitor] Skipping duplicate Auto-Fog event at {current_ts}")
                        return
                    self._last_auto_fog_ts = current_ts

                cfg = self.app.log_monitor_state.config.get("auto_fog", {})
                if cfg and cfg.get("enabled"):
                    # Check session count - fog only works with exactly 1 session
                    session_count = len(getattr(self.app.sessions, 'sessions', {}) or {})
                    if session_count > 1:
                        print(f"[AutoFog] SKIPPING - multiple sessions active ({session_count})")
                        return
                    
                    print(f"[LogMonitor] Auto-Fog triggered at {current_ts}!")
                    
                    # Instant execution in thread to not block UI/monitor
                    threading.Thread(target=lambda: self._send_console_command("mainscene.fog 0"), daemon=True).start()

        except Exception as e:
            self.app.log_error("auto_fog_detection", e)


    def _send_console_command(self, command: str):
        """Open console with tilde (~), type command, and press Enter.
        Only sends if NWN window is found and can be focused.
        """
        try:
            from utils.win_automation import press_key_by_name, get_keyboard_layout, set_keyboard_layout
            import time
            
            print(f"[AutoFog] Starting console command: {command}")
            
            # 1. Find and focus game window using session PIDs
            hwnd = self._focus_game_by_pid()
            if not hwnd:
                print("[AutoFog] SKIPPING - No NWN window found")
                return
            
            time.sleep(0.1)

            # --- Layout Management ---
            # Check current layout
            TRANS_DELAY_MS = 100
            current_hkl = get_keyboard_layout(hwnd)
            target_lang = 0x0409 # English (US)
            layout_changed = False
            
            if current_hkl != target_lang:
                print(f"[AutoFog] Layout is {hex(current_hkl)}, switching to English ({hex(target_lang)})...")
                set_keyboard_layout(hwnd, target_lang)
                layout_changed = True
                time.sleep(0.15) # Wait for switch
            
            try:
                # 2. Open Console with tilde (~)
                print("[AutoFog] Pressing tilde to open console...")
                
                # PAUSE HOTKEYS so typing doesn't trigger them (e.g. 'E' key)
                if hasattr(self.app, "multi_hotkey_manager"):
                    self.app.multi_hotkey_manager.pause()
                
                press_key_by_name("`")
                
                # Wait for console to open
                time.sleep(0.1)
                
                # 3. Type Command
                print(f"[AutoFog] Typing command: {command}")
                for char in command:
                    if char == " ":
                        press_key_by_name("SPACE")
                    elif char == ".":
                        press_key_by_name(".")
                    else:
                        press_key_by_name(char)
                    time.sleep(0.01) # Very fast typing
                
                # 4. Press Enter (Execute)
                time.sleep(0.05)
                print("[AutoFog] Pressing Enter to execute...")
                press_key_by_name("ENTER")
                
                print(f"[AutoFog] Command sent successfully: {command}")
            finally:
                # RESUME HOTKEYS
                if hasattr(self.app, "multi_hotkey_manager"):
                    self.app.multi_hotkey_manager.resume()
                
                # Restore layout
                if layout_changed:
                    print(f"[AutoFog] Restoring layout to {hex(current_hkl)}...")
                    time.sleep(0.1)
                    set_keyboard_layout(hwnd, current_hkl)

            
        except Exception as e:
            print(f"[AutoFog] Error: {e}")
            self.app.log_error("send_console_command", e)

    def _focus_game_by_pid(self):
        """Focus game window using session PIDs. Returns hwnd if successful, None otherwise."""
        try:
            sess = getattr(self.app.sessions, 'sessions', None) or {}
            print(f"[AutoFog] Looking for game in sessions: {list(sess.keys())}")
            
            for k, v in sess.items():
                try:
                    pid = int(v)
                    hwnd = get_hwnd_from_pid(pid)
                    if hwnd:
                        print(f"[AutoFog] Found NWN window: hwnd={hwnd}, pid={pid}")
                        user32.SetForegroundWindow(hwnd)
                        time.sleep(0.1)
                        return hwnd
                except Exception as e:
                    print(f"[AutoFog] Error finding window for pid {v}: {e}")
                    continue
            
            print("[AutoFog] No game window found in any session")
            return None
        except Exception as e:
            print(f"[AutoFog] Error in _focus_game_by_pid: {e}")
            return None

    def _ensure_game_focused(self):
        """Helper to focus game window."""
        return self._focus_game_by_pid()

    
    def _execute_pending_open_wounds(self, key: str):
        """Execute a pending Open Wounds key press after cooldown."""
        try:
            self._pending_open_wounds_press = None
            self._last_open_wounds_activation = time.time()
            self._send_function_key_to_active_session(key)
            
            # Increment counter for the delayed activation
            self.app.log_monitor_state.slayer_hit_count += 1
            self._update_slayer_hit_counter_ui()
        except Exception as e:
            self.app.log_error("execute_pending_open_wounds", e)
    
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

    def on_log_monitor_toggle(self):
        """Handle toggle switch change - auto apply."""
        enabled_var = self.app.log_monitor_state.enabled_var
        if not enabled_var:
            return
        enabled = enabled_var.get()
        self.app.log_monitor_state.config["enabled"] = enabled
        self.app.log_monitor_state.config["log_path"] = self.app.log_monitor_state.log_path_var.get()
        
        # Filter out placeholder text when saving (including legacy placeholders)
        webhooks_placeholders = ["https://discord.com/api/webhooks/...", "YOUR_WEBHOOK_URL_HERE"]
        keywords_placeholders = ["Enemy Spotted, Player Killed, ...", "Enemy Spotted", "Enemy_Spotted"]
        
        self.app.log_monitor_state.config["webhooks"] = [
            w.strip()
            for w in self.app.log_monitor_state.webhooks_text.get("1.0", "end").strip().split("\n")
            if w.strip() and w.strip() not in webhooks_placeholders
        ]
        self.app.log_monitor_state.config["keywords"] = [
            k.strip()
            for k in self.app.log_monitor_state.keywords_text.get("1.0", "end").strip().split("\n")
            if k.strip() and k.strip() not in keywords_placeholders
        ]

        self.app.save_data()
        self.update_slayer_ui_state()

        if enabled:
            self.start_log_monitor()
            self.app.log_monitor_status.config(text="Status: Running", fg=COLORS["success"])
        else:
            self.stop_log_monitor()
            self.app.log_monitor_status.config(text="Status: Stopped", fg=COLORS["danger"])

    def update_slayer_ui_state(self):
        """Update slayer (Open Wounds) and Auto-Fog UI elements."""

        try:
            slayer_cfg = self.app.log_monitor_state.config.get("open_wounds", {})
            slayer_on = slayer_cfg.get("enabled", False)
            log_monitor_on = self.app.log_monitor_state.monitor and self.app.log_monitor_state.monitor.is_running()
            slayer_monitor_on = self.app.log_monitor_state.slayer_monitor and self.app.log_monitor_state.slayer_monitor.is_running()
            slayer_active = slayer_on and (log_monitor_on or slayer_monitor_on)

            fg_color = COLORS["fg_text"]

            if hasattr(self.app, "ow_label"):
                self.app.ow_label.config(fg=fg_color)
            if hasattr(self.app, "ow_key_label"):
                self.app.ow_key_label.config(fg=fg_color)

            if hasattr(self.app, "ow_frame"):
                if slayer_active:
                    self.app.ow_frame.config(
                        fg=COLORS["warning"],
                        highlightbackground=COLORS["warning"],
                        highlightcolor=COLORS["warning"],
                        highlightthickness=2,
                    )
                elif slayer_on:
                    self.app.ow_frame.config(
                        fg=COLORS["accent"],
                        highlightbackground=COLORS["border"],
                        highlightcolor=COLORS["border"],
                        highlightthickness=1,
                    )
                else:
                    self.app.ow_frame.config(
                        fg=COLORS["fg_dim"],
                        highlightbackground=COLORS["border"],
                        highlightcolor=COLORS["border"],
                        highlightthickness=1,
                    )

            if hasattr(self.app, "ow_note"):
                if slayer_active:
                    mode = "via Log Monitor" if log_monitor_on else "standalone"
                    self.app.ow_note.config(
                        fg=COLORS["warning"],
                        text=f"⚔️ Slayer is ACTIVE ({mode})",
                    )
                elif slayer_on:
                    self.app.ow_note.config(
                        fg=COLORS["accent"],
                        text="⏳ Slayer enabled - waiting for game",
                    )
                else:
                    self.app.ow_note.config(
                        fg=COLORS["fg_dim"],
                        text="Slayer works independently from Log Monitor",
                    )

            if hasattr(self.app, "slayer_counter_label"):
                self.app.slayer_counter_label.config(text=f"Hits: {self.app.log_monitor_state.slayer_hit_count}")
        except Exception:
            pass

    def browse_log_path(self):
        from tkinter import filedialog

        path = filedialog.askopenfilename(
            title="Select Log File",
            filetypes=[("Log files", "*.txt *.log"), ("All files", "*.*")],
        )
        if path:
            if self.app.log_monitor_state.log_path_var:
                self.app.log_monitor_state.log_path_var.set(path)

    def save_log_monitor_settings(self, silent: bool = False):
        """Save log monitor settings."""
        from tkinter import messagebox

        try:
            enabled_var = self.app.log_monitor_state.enabled_var
            log_path_var = self.app.log_monitor_state.log_path_var
            webhooks_text = self.app.log_monitor_state.webhooks_text
            keywords_text = self.app.log_monitor_state.keywords_text
            if not (enabled_var and log_path_var and webhooks_text and keywords_text):
                return
            self.app.log_monitor_state.config["enabled"] = enabled_var.get()
            self.app.log_monitor_state.config["log_path"] = log_path_var.get()
            
            # Filter out placeholder text when saving (including legacy placeholders)
            webhooks_placeholders = ["https://discord.com/api/webhooks/...", "YOUR_WEBHOOK_URL_HERE"]
            keywords_placeholders = ["Enemy Spotted, Player Killed, ...", "Enemy Spotted", "Enemy_Spotted"]
            
            self.app.log_monitor_state.config["webhooks"] = [
                w.strip()
                for w in webhooks_text.get("1.0", "end").strip().split("\n")
                if w.strip() and w.strip() not in webhooks_placeholders
            ]
            self.app.log_monitor_state.config["keywords"] = [
                k.strip()
                for k in keywords_text.get("1.0", "end").strip().split("\n")
                if k.strip() and k.strip() not in keywords_placeholders
            ]
            try:
                self.app.log_monitor_state.config["open_wounds"] = {
                    "enabled": bool(self.app.log_monitor_state.open_wounds_enabled_var.get()),
                    "key": str(self.app.log_monitor_state.open_wounds_key_var.get() or "F1"),
                }
            except Exception:
                self.app.log_monitor_state.config["open_wounds"] = {"enabled": False, "key": "F1"}
            
            # Save Auto-Fog
            try:
                self.app.log_monitor_state.config["auto_fog"] = {
                    "enabled": bool(self.app.log_monitor_state.auto_fog_enabled_var.get()),
                }
            except Exception:
                self.app.log_monitor_state.config["auto_fog"] = {"enabled": False}

            self.app.save_data()

            if self.app.log_monitor_state.config["enabled"]:
                self.start_log_monitor()
                self.app.log_monitor_status.config(text="Status: Running", fg=COLORS["success"])
            else:
                self.stop_log_monitor()
                self.app.log_monitor_status.config(text="Status: Stopped", fg=COLORS["danger"])

            if not silent:
                messagebox.showinfo("Success", "Log monitor settings saved!")
        except Exception as e:
            if not silent:
                messagebox.showerror("Error", f"Failed to save: {e}")
            else:
                self.app.log_error("save_log_monitor_settings", e)

    def schedule_save_log_monitor_settings(self, delay_ms: int = 500):
        """Debounced save of log monitor settings."""
        if hasattr(self, "_lm_save_after_id") and self._lm_save_after_id:
            try:
                self.app.root.after_cancel(self._lm_save_after_id)
            except Exception:
                pass
        self._lm_save_after_id = self.app.root.after(
            delay_ms, 
            lambda: (setattr(self, '_lm_save_after_id', None), self.save_log_monitor_settings(silent=True))
        )

    def toggle_log_monitor_enabled(self):
        """Toggle log monitor on/off from UI or StatusBar."""
        try:
            # Determine current state and toggle
            enabled_var = self.app.log_monitor_state.enabled_var
            
            if enabled_var:
                new_state = not enabled_var.get()
                enabled_var.set(new_state)
            else:
                current_config_state = self.app.log_monitor_state.config.get("enabled", False)
                new_state = not current_config_state
            
            # Persist desired state
            self.app.log_monitor_state.config["enabled"] = new_state
            
            # Save data (debounced or immediate)
            if hasattr(self.app, 'schedule_save'):
                self.app.schedule_save()
            else:
                self.app.save_data()

            # Update or create monitor
            self.ensure_log_monitor()

            if new_state:
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
            pass  # No longer need to check for running game - will wait for game to start

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
