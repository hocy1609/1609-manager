"""
Keybind Manager for NWN Manager.

This module provides global hotkey functionality for triggering
custom key sequences in the game.
"""

import threading
import ctypes
import ctypes.wintypes
import time
from dataclasses import dataclass
from typing import Callable, Optional, Dict, List

from utils.win_automation import (
    user32, get_hwnd_from_pid, press_key_sequence, 
    right_click_and_send_sequence, press_key_with_modifiers, VK_MAP
)


# Windows API constants for RegisterHotKey
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000

WM_HOTKEY = 0x0312
WM_USER_UPDATE = 0x0400 + 1  # Custom message to trigger updates


@dataclass
class HotkeyAction:
    """Represents a hotkey action configuration."""
    trigger: str  # Trigger key (e.g., "1", "Q", "F10")
    sequence: List[str]  # Key sequence to send (e.g., ["NUMPAD0", "NUMPAD3", "NUMPAD2"])
    right_click: bool = False  # Right-click before sending
    comment: str = ""  # Description/comment
    enabled: bool = True  # Is this hotkey enabled
    
    def to_dict(self) -> dict:
        return {
            "trigger": self.trigger,
            "sequence": self.sequence,
            "rightClick": self.right_click,
            "comment": self.comment,
            "enabled": self.enabled,
        }
    
    @staticmethod
    def from_dict(d: dict) -> "HotkeyAction":
        return HotkeyAction(
            trigger=d.get("trigger", ""),
            sequence=d.get("sequence", []),
            right_click=d.get("rightClick", False),
            comment=d.get("comment", ""),
            enabled=d.get("enabled", True),
        )


class MultiHotkeyManager:
    """
    Manages multiple global hotkeys for NWN Manager.
    
    Uses Windows RegisterHotKey API.
    Dynamically registers/unregisters hotkeys based on NWN window focus
    to prevent capturing keys when the game is not active.
    """
    
    def __init__(self, app):
        """
        Initialize the MultiHotkeyManager.
        
        Args:
            app: Reference to the NWNManagerApp instance
        """
        self.app = app
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._watcher_thread: Optional[threading.Thread] = None
        
        self._hotkeys: Dict[int, HotkeyAction] = {}  # hotkey_id -> action
        self._pending_actions: List[HotkeyAction] = [] # Actions waiting to be registered
        
        self._next_id = 1
        self._lock = threading.Lock()
        
        # State tracking
        self._are_keys_registered = False
        self._last_focus_check = False # True if NWN was focused
        self._thread_id: Optional[int] = None
        self._paused = False

    def pause(self):
        """Temporarily unregister all hotkeys."""
        if not self._running or self._paused:
            return
        
        print("[MultiHotkeyManager] Pausing hotkeys...")
        self._paused = True
        if self._thread_id:
            user32.PostThreadMessageW(self._thread_id, WM_USER_UPDATE, 0, 0)
    
    def resume(self):
        """Resume hotkey functionality."""
        if not self._running or not self._paused:
            return

        print("[MultiHotkeyManager] Resuming hotkeys...")
        self._paused = False
        if self._thread_id:
            # Force check to re-register if window is focused
            user32.PostThreadMessageW(self._thread_id, WM_USER_UPDATE, 0, 0)

    def register_hotkeys(self, actions: List[HotkeyAction]) -> int:
        """
        Register multiple global hotkeys.
        
        Args:
            actions: List of HotkeyAction to register
            
        Returns:
            Number of enabled actions (not necessarily registered yet)
        """
        self._pending_actions = [a for a in actions if a.enabled and a.trigger]
        
        if not self._running:
            self._start()
        else:
            # Signal thread to update
            if self._thread_id:
                user32.PostThreadMessageW(self._thread_id, WM_USER_UPDATE, 0, 0)
        
        count = len(self._pending_actions)
        print(f"[MultiHotkeyManager] Configured {count} hotkeys (waiting for focus)")
        return count
    
    def unregister_all(self):
        """Stop manager and unregister all hooks."""
        self._running = False
        
        if self._thread and self._thread.is_alive():
            try:
                if self._thread_id:
                    user32.PostThreadMessageW(self._thread_id, 0x0012, 0, 0)  # WM_QUIT
            except Exception:
                pass
            try:
                self._thread.join(timeout=1.0)
            except Exception:
                pass
        
        if self._watcher_thread and self._watcher_thread.is_alive():
             try:
                self._watcher_thread.join(timeout=0.5)
             except Exception:
                 pass

        with self._lock:
            self._hotkeys.clear()
        
        self._thread = None
        self._watcher_thread = None
        self._thread_id = None
        self._are_keys_registered = False
        self._paused = False
        print("[MultiHotkeyManager] Stopped")
    
    def _start(self):
        """Start the message loop and watcher threads."""
        self._running = True
        
        # 1. Message Loop Thread (handles RegisterHotKey)
        self._thread = threading.Thread(target=self._msg_loop, daemon=True)
        self._thread.start()
        
        # 2. Focus Watcher Thread
        self._watcher_thread = threading.Thread(target=self._focus_watcher_loop, daemon=True)
        self._watcher_thread.start()
    
    def _msg_loop(self):
        """Thread that runs the Windows Message Loop."""
        self._thread_id = ctypes.windll.kernel32.GetCurrentThreadId()
        print(f"[MultiHotkeyManager] Message loop started (TID={self._thread_id})")
        
        # Create message structure
        msg = ctypes.wintypes.MSG()
        
        while self._running:
            # GetMessage blocks until a message is received
            # We use it to handle WM_HOTKEY and our custom WM_USER_UPDATE
            result = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
            
            if result == 0 or result == -1: # WM_QUIT or error
                break
            
            if msg.message == WM_HOTKEY:
                self._handle_hotkey_press(msg.wParam)
                
            elif msg.message == WM_USER_UPDATE:
                # Signal to re-evaluate registration (e.g. config changed or focus changed)
                # wParam: 1 = Force Register, 0 = Check Focus/Config
                force_register = (msg.wParam == 1)
                self._update_registration(force_register)
        
        # Cleanup on exit
        self._forced_unregister_all()
        print("[MultiHotkeyManager] Message loop ended")

    def _focus_watcher_loop(self):
        """Monitors active window and signals message loop when focus changes."""
        while self._running:
            time.sleep(0.5)
            
            is_nwn_focused = self._is_nwn_focused()
            
            # If focus state changed
            if is_nwn_focused != self._last_focus_check:
                self._last_focus_check = is_nwn_focused
                
                # Signal message loop to update registration
                if self._thread_id:
                    # wParam=1 means "Register" (if focused), if not focused it checks and unregisters
                    # Actually _update_registration checks _is_nwn_focused internally or we pass it?
                    # Let's trust _update_registration to check focus again or use internal state.
                    # Ideally, we just wake it up.
                    user32.PostThreadMessageW(self._thread_id, WM_USER_UPDATE, 0, 0)

    def _update_registration(self, force: bool = False):
        """
        Called within the message loop thread.
        Syncs registered hotkeys with current config and focus state.
        """
        # Smart pause if >1 session running and setting enabled
        session_count = len(getattr(self.app.sessions, "sessions", {}) or {})
        multi_session_pause = False
        if session_count > 1:
            settings = getattr(self.app, "settings", None)
            if settings and getattr(settings, "disable_hotkeys_on_multi_session", False):
                multi_session_pause = True

        should_be_registered = (self._is_nwn_focused() or force) and not self._paused and not multi_session_pause
        
        # If state implies change
        if should_be_registered and not self._are_keys_registered:
            self._do_register_all()
        elif not should_be_registered and self._are_keys_registered:
            self._forced_unregister_all()
        elif should_be_registered and self._are_keys_registered:
            # If already registered, but config might have changed (pending_actions)
            # We just re-register everything to be safe/sync
            self._forced_unregister_all()
            self._do_register_all()

    def _do_register_all(self):
        """Register all pending actions."""
        self._hotkeys.clear()
        self._next_id = 1
        
        registered_count = 0
        print(f"[MultiHotkeyManager] Registering {len(self._pending_actions)} pending actions...")
        
        for action in self._pending_actions:
            key_upper = action.trigger.upper()
            vk_code = VK_MAP.get(key_upper)
            
            if not vk_code:
                print(f"[MultiHotkeyManager] Unknown key: {key_upper}")
                continue
            
            hotkey_id = self._next_id
            self._next_id += 1
            
            # Register
            res = user32.RegisterHotKey(None, hotkey_id, MOD_NOREPEAT, vk_code)
            if res:
                self._hotkeys[hotkey_id] = action
                registered_count += 1
                print(f"[MultiHotkeyManager] Registered: {key_upper} (id={hotkey_id})")
            else:
                err = ctypes.get_last_error()
                print(f"[MultiHotkeyManager] FAILED to register {key_upper}: error={err}")
        
        if registered_count > 0:
            self._are_keys_registered = True
            print(f"[MultiHotkeyManager] Hooks Active ({registered_count} keys)")
        else:
            self._are_keys_registered = False
            print("[MultiHotkeyManager] No hooks registered")

    def _forced_unregister_all(self):
        """Unregister all current hotkeys."""
        if not self._are_keys_registered:
            return
            
        for hid in list(self._hotkeys.keys()):
            user32.UnregisterHotKey(None, hid)
        
        self._hotkeys.clear()
        self._are_keys_registered = False
        # print("[MultiHotkeyManager] Hooks Released")

    def _handle_hotkey_press(self, hotkey_id):
        """Handle WM_HOTKEY message."""
        action = self._hotkeys.get(hotkey_id)
        if action:
            # Double check focus just in case (though loop handles it)
            # if self._is_nwn_focused():
            print(f"[MultiHotkeyManager] Hotkey: {action.trigger}")
            threading.Thread(target=self._execute_action, args=(action,), daemon=True).start()

    def _execute_action(self, action: HotkeyAction):
        """Execute a hotkey action."""
        try:
            # Check if current foreground window is one of our sessions
            fg_hwnd = user32.GetForegroundWindow()
            is_nwn_focused = False
            
            if fg_hwnd:
                fg_pid = ctypes.c_ulong()
                user32.GetWindowThreadProcessId(fg_hwnd, ctypes.byref(fg_pid))
                current_pid = fg_pid.value
                
                sessions = getattr(self.app.sessions, 'sessions', None) or {}
                # Check if currently focused PID is a known session
                focused_profile = None
                for k, pid_str in sessions.items():
                    try:
                        if int(pid_str) == current_pid:
                            is_nwn_focused = True
                            # Find profile by cdKey (k)
                            for prof in getattr(self.app, 'profiles', []):
                                if prof.get("cdKey") == k:
                                    focused_profile = prof
                                    break
                            break
                    except (ValueError, TypeError):
                        continue
                
                # Per-profile hotkey check: only trigger if profile has hotkey_on=True
                if is_nwn_focused:
                    if focused_profile and not focused_profile.get("hotkey_on", False):
                        print(f"[MultiHotkeyManager] Hotkey IGNORED: profile '{focused_profile.name}' has hotkeys OFF")
                        return
                    elif not focused_profile:
                        # Session found but no profile match (shouldn't happen)? 
                        print("[MultiHotkeyManager] Hotkey IGNORED: No profile match for session")
                        return

            # Ensure hotkeys only fire when their profile is actually focused
            if not is_nwn_focused:
                print("[MultiHotkeyManager] Hotkey IGNORED: Active window is not an NWN session")
                return
            
            if action.right_click:
                right_click_and_send_sequence(action.sequence)
            else:
                press_key_sequence(action.sequence)
        except Exception as e:
            print(f"[MultiHotkeyManager] Error executing action: {e}")
            if hasattr(self.app, 'log_error'):
                self.app.log_error("execute_hotkey_action", e)
    
    def _is_nwn_focused(self) -> bool:
        """Check if any known NWN session window is currently in foreground."""
        try:
            foreground_hwnd = user32.GetForegroundWindow()
            if not foreground_hwnd:
                return False
            
            # Get process ID of the foreground window
            fg_pid = ctypes.c_ulong()
            user32.GetWindowThreadProcessId(foreground_hwnd, ctypes.byref(fg_pid))
            current_pid = fg_pid.value
            
            sessions = getattr(self.app.sessions, 'sessions', None) or {}
            if not sessions:
                return False
                
            for k, pid_str in sessions.items():
                try:
                    pid = int(pid_str)
                    if pid == current_pid:
                        return True
                except (ValueError, TypeError):
                    continue
            return False
        except Exception:
            return False

    def _get_hotkey_target_hwnd(self):
        """Find the HWND of the session that has hotkey_on=True."""
        try:
            sessions = getattr(self.app.sessions, 'sessions', None) or {}
            for prof in getattr(self.app, 'profiles', []):
                if prof.get("hotkey_on", False):
                    pid_str = sessions.get(prof.get("cdKey"))
                    if pid_str:
                        return get_hwnd_from_pid(int(pid_str))
        except Exception:
            pass
        return None

    def _focus_game_window(self):
        """DEPRECATED: Use _get_hotkey_target_hwnd in _execute_action instead."""
        pass
    
    def is_active(self) -> bool:
        """Check if hotkeys are actively registered."""
        return self._are_keys_registered
    
    def get_registered_count(self) -> int:
        """Get the number of configured hotkeys."""
        return len(self._pending_actions)


# Legacy single hotkey manager for backward compatibility
class KeybindManager:
    """
    Manages a single global hotkey for NWN Manager.
    For backward compatibility with existing code.
    """
    
    def __init__(self, app):
        self.app = app
        self._hotkey_id = 1
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._registered_key: Optional[str] = None
        self._callback: Optional[Callable] = None
    
    def register_hotkey(self, key_name: str, callback: Callable) -> bool:
        self.unregister_hotkey()
        
        key_upper = key_name.upper()
        vk_code = VK_MAP.get(key_upper)
        
        if not vk_code:
            print(f"[KeybindManager] Unknown key: {key_name}")
            return False
        
        self._callback = callback
        self._registered_key = key_upper
        
        self._running = True
        self._thread = threading.Thread(target=self._hotkey_loop, args=(vk_code,), daemon=True)
        self._thread.start()
        
        print(f"[KeybindManager] Registered hotkey: {key_upper}")
        return True
    
    def unregister_hotkey(self):
        self._running = False
        
        if self._thread and self._thread.is_alive():
            try:
                user32.PostThreadMessageW(self._thread.ident, 0x0012, 0, 0)
            except Exception:
                pass
            try:
                self._thread.join(timeout=1.0)
            except Exception:
                pass
        
        self._thread = None
        self._registered_key = None
        self._callback = None
        print("[KeybindManager] Hotkey unregistered")
    
    def _hotkey_loop(self, vk_code: int):
        try:
            # Legacy implementation always registers, doesn't use the new smart focus logic
            # Use MultiHotkeyManager if you need smart focus
            result = user32.RegisterHotKey(None, self._hotkey_id, MOD_NOREPEAT, vk_code)
            
            if not result:
                error = ctypes.get_last_error()
                print(f"[KeybindManager] Failed to register hotkey, error: {error}")
                return
            
            msg = ctypes.wintypes.MSG()
            
            while self._running:
                result = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
                
                if result == 0 or result == -1:
                    break
                
                if msg.message == WM_HOTKEY and msg.wParam == self._hotkey_id:
                    print(f"[KeybindManager] Hotkey pressed: {self._registered_key}")
                    if self._callback:
                        try:
                            self._callback()
                        except Exception as e:
                            print(f"[KeybindManager] Callback error: {e}")
            
        except Exception as e:
            print(f"[KeybindManager] Error in hotkey loop: {e}")
        finally:
            try:
                user32.UnregisterHotKey(None, self._hotkey_id)
            except Exception:
                pass
    
    def is_active(self) -> bool:
        return self._running and self._thread and self._thread.is_alive()
    
    def get_registered_key(self) -> Optional[str]:
        return self._registered_key if self.is_active() else None


def send_numpad_sequence_to_nwn(app, sequence: list = None):
    """
    Focus NWN window and send numpad key sequence.
    
    Args:
        app: Reference to the NWNManagerApp instance
        sequence: List of numpad keys to send (default: ['NUMPAD0', 'NUMPAD3', 'NUMPAD2'])
    """
    if sequence is None:
        sequence = ['NUMPAD0', 'NUMPAD3', 'NUMPAD2']
    
    try:
        # Get running session PID
        pid = None
        try:
            sessions = getattr(app.sessions, 'sessions', None) or {}
            for k, v in sessions.items():
                pid = int(v)
                break
        except Exception:
            pid = None
        
        if pid:
            hwnd = get_hwnd_from_pid(pid)
            if hwnd:
                user32.SetForegroundWindow(hwnd)
                time.sleep(0.1)
        
        press_key_sequence(sequence, delay=0.1)
        print(f"[Keybind] Sent numpad sequence: {sequence}")
        
    except Exception as e:
        print(f"[Keybind] Error sending numpad sequence: {e}")
        if hasattr(app, 'log_error'):
            app.log_error("send_numpad_sequence", e)

