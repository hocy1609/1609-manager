import ctypes
import os
import time
import re


def set_dpi_awareness():
    """Фикс DPI для Windows 10/11. Устанавливает Per-Monitor DPI Awareness v2."""
    try:
        # Try Per-Monitor DPI Awareness v2 (Windows 10 1703+)
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            # Fallback to System DPI Awareness
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass


def get_dpi_scale() -> float:
    """Получает коэффициент масштабирования DPI для основного монитора.
    
    Returns:
        float: Коэффициент масштабирования (1.0 для 100%, 1.5 для 150%, 2.0 для 200%)
    """
    try:
        # Try to get DPI from the primary monitor
        # GetDpiForSystem returns DPI value (96 = 100%, 144 = 150%, 192 = 200%)
        try:
            dpi = ctypes.windll.user32.GetDpiForSystem()
            return dpi / 96.0
        except Exception:
            pass
        
        # Fallback: GetDeviceCaps with LOGPIXELSX (index 88)
        try:
            hdc = ctypes.windll.user32.GetDC(0)
            if hdc:
                dpi = ctypes.windll.gdi32.GetDeviceCaps(hdc, 88)  # LOGPIXELSX
                ctypes.windll.user32.ReleaseDC(0, hdc)
                return dpi / 96.0
        except Exception:
            pass
        
        # Last fallback: check Windows scaling via registry
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Control Panel\Desktop\WindowMetrics"
            )
            # AppliedDPI is the actual DPI setting
            applied_dpi, _ = winreg.QueryValueEx(key, "AppliedDPI")
            winreg.CloseKey(key)
            return applied_dpi / 96.0
        except Exception:
            pass
    except Exception:
        pass
    
    return 1.0  # Default to no scaling


# === WINDOWS API CONSTANTS & STRUCTURES ===

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

INPUT_MOUSE = 0
INPUT_KEYBOARD = 1

KEYEVENTF_KEYUP = 0x0002
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004

VK_ESCAPE = 0x1B
VK_MENU = 0x12

SW_RESTORE = 9
SW_MINIMIZE = 6

KEYEVENTF_SCANCODE = 0x0008


WM_MOUSEMOVE = 0x0200
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
WM_INPUTLANGCHANGEREQUEST = 0x0050
MK_LBUTTON = 0x0001
HKL_NEXT = 1


GWL_EXSTYLE = -20
WS_EX_APPWINDOW = 0x00040000
WS_EX_TOOLWINDOW = 0x00000080

PROCESS_QUERY_INFORMATION = 0x0400
STILL_ACTIVE = 259


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long), ("right", ctypes.c_long), ("bottom", ctypes.c_long)]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.c_long),
        ("dy", ctypes.c_long),
        ("mouseData", ctypes.c_ulong),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        # Use integer/uintptr sized extra info to match KEYBDINPUT on 64-bit
        ("dwExtraInfo", ctypes.c_ulonglong),
    ]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", ctypes.c_ushort),
        ("wScan", ctypes.c_ushort),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        # Use integer/uintptr for dwExtraInfo so structure layout matches
        # the Win32 API across 32/64-bit. Previously a POINTER was used
        # which could lead to incorrect sizes and broken SendInput.
        ("dwExtraInfo", ctypes.c_ulonglong),
    ]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", ctypes.c_ulong),
        ("wParamL", ctypes.c_short),
        ("wParamH", ctypes.c_ushort),
    ]


class INPUT_UNION(ctypes.Union):
    _fields_ = [
        ("mi", MOUSEINPUT),
        ("ki", KEYBDINPUT),
        ("hi", HARDWAREINPUT),
    ]


class INPUT_STRUCT(ctypes.Structure):
    _fields_ = [("type", ctypes.c_ulong), ("u", INPUT_UNION)]


# === SAFE FILE REPLACEMENT ===

def safe_replace(src: str, dst: str) -> None:
    import shutil

    """
    Замена файла без использования shutil.replace, чтобы избежать бага
    'shutil has no attribute replace' на некоторых сборках.
    """
    try:
        if hasattr(os, "replace"):
            os.replace(src, dst)
        else:
            if os.path.exists(dst):
                os.remove(dst)
            os.rename(src, dst)
    except OSError:
        try:
            shutil.copy2(src, dst)
            os.remove(src)
        except Exception as e:
            print(f"Error replacing file: {e}")
            raise


# === AUTOMATION FUNCTIONS (SAFE EXIT) ===

def get_hwnd_from_pid(pid: int):
    hwnd_found = None

    def callback(hwnd, _):
        nonlocal hwnd_found
        lpdw_process_id = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(lpdw_process_id))
        if lpdw_process_id.value == pid and user32.IsWindowVisible(hwnd):
            hwnd_found = hwnd
            return False
        return True

    WNDENUMPROC = ctypes.WINFUNCTYPE(
        ctypes.c_bool, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int)
    )
    user32.EnumWindows(WNDENUMPROC(callback), 0)
    return hwnd_found


def safe_exit_sequence(
    pid: int,
    rel_exit_x: int,
    rel_exit_y: int,
    rel_confirm_x: int,
    rel_confirm_y: int,
    speed: float | None = None,
    esc_count: int | None = None,
    clip_margin: int | None = None,
) -> None:
    """Автоматическая последовательность выхода из игры с кликами по координатам."""
    import subprocess

    try:
        hwnd = get_hwnd_from_pid(pid)
        if not hwnd:
            subprocess.run(f"taskkill /f /pid {pid}", shell=True)
            return

        if user32.IsIconic(hwnd):
            user32.ShowWindow(hwnd, SW_RESTORE)

        # Отключаем липкие клавиши
        user32.SystemParametersInfoW(0x2001, 0, 0, 0)

        # Alt для фокуса
        # Allow adjusting sleep timings via NWN_EXIT_SPEED env var (multiplier, e.g. 0.5 for faster)
        # Determine speed multiplier: explicit arg -> env var -> default
        try:
            if speed is not None:
                _speed = float(speed)
            else:
                _speed = float(os.environ.get("NWN_EXIT_SPEED", "0.4"))
            if _speed <= 0:
                _speed = 0.4
        except Exception:
            _speed = 0.4

        user32.keybd_event(VK_MENU, 0, 0, 0)
        time.sleep(0.03 * _speed)
        user32.keybd_event(VK_MENU, 0, KEYEVENTF_KEYUP, 0)

        user32.SetForegroundWindow(hwnd)
        time.sleep(0.25 * _speed)

        # Try to block user input (mouse & keyboard) for the duration of the automation
        _blocked = False
        _cursor_clipped = False
        _original_clip = RECT()
        _had_original_clip = False
        try:
            # BlockInput blocks mouse and keyboard input system-wide while True
            # It may require elevated privileges on some systems; check return value.
            if hasattr(user32, "BlockInput"):
                try:
                    ret = user32.BlockInput(True)
                    # ret == 0 -> failed; non-zero -> success
                    if ret:
                        _blocked = True
                        # give system a moment to apply the block
                        time.sleep(0.02)
                    else:
                        _blocked = False
                except Exception:
                    _blocked = False

            # If BlockInput failed or is unavailable, we'll attempt a ClipCursor fallback
            # but defer setting the clipping rectangle until we know the absolute
            # screen coordinates we need to click (so the automation can still
            # move the cursor between those points).
            # The actual ClipCursor attempt is performed later after computing
            # absolute click positions.
            if not _blocked:
                try:
                    try:
                        res = user32.GetClipCursor(ctypes.byref(_original_clip))
                        if res:
                            _had_original_clip = True
                    except Exception:
                        _had_original_clip = False
                except Exception:
                    _had_original_clip = False
        except Exception:
            _blocked = False
            _cursor_clipped = False

        pt = POINT(0, 0)
        user32.ClientToScreen(hwnd, ctypes.byref(pt))
        origin_x = pt.x
        origin_y = pt.y

        abs_exit_x = origin_x + rel_exit_x
        abs_exit_y = origin_y + rel_exit_y
        abs_conf_x = origin_x + rel_confirm_x
        abs_conf_y = origin_y + rel_confirm_y

        # If BlockInput failed earlier, try ClipCursor now but include both
        # the exit and confirm coordinates (and current cursor) in the clip
        # rectangle so the automation can still move and click between them.
        try:
            if not _blocked:
                try:
                    cur = POINT(0, 0)
                    try:
                        user32.GetCursorPos(ctypes.byref(cur))
                    except Exception:
                        cur.x, cur.y = origin_x, origin_y

                    # margin: explicit arg -> default 48
                    try:
                        margin = int(clip_margin) if clip_margin is not None else 48
                    except Exception:
                        margin = 48
                    left = min(cur.x, abs_exit_x, abs_conf_x) - margin
                    top = min(cur.y, abs_exit_y, abs_conf_y) - margin
                    right = max(cur.x, abs_exit_x, abs_conf_x) + margin
                    bottom = max(cur.y, abs_exit_y, abs_conf_y) + margin

                    # Clamp to reasonable screen bounds to avoid invalid rects
                    try:
                        sx = user32.GetSystemMetrics(0)
                        sy = user32.GetSystemMetrics(1)
                        if left < 0:
                            left = 0
                        if top < 0:
                            top = 0
                        if right > sx:
                            right = sx
                        if bottom > sy:
                            bottom = sy
                    except Exception:
                        pass

                    clip_rect = RECT(int(left), int(top), int(right), int(bottom))
                    try:
                        if user32.ClipCursor(ctypes.byref(clip_rect)):
                            _cursor_clipped = True
                    except Exception:
                        _cursor_clipped = False
                except Exception:
                    _cursor_clipped = False
        except Exception:
            _cursor_clipped = False

        # Prefer using SendInput, but if game doesn't register synthetic
        # inputs, fall back to the older keybd_event (which is often
        # better recognized by some games). Use discrete down/up pairs
        # (no holding) for each ESC press.
        # Determine ESC count: explicit arg -> env var -> default
        try:
            if esc_count is not None:
                _esc_count = int(esc_count)
            else:
                _esc_count = int(os.environ.get("NWN_ESC_COUNT", "6"))
            if _esc_count <= 0:
                _esc_count = 6
        except Exception:
            _esc_count = 6

        # Ensure the target window is foreground and has a short moment to
        # accept keyboard events. Retry a few times if necessary.
        for _try in range(6):
            try:
                user32.SetForegroundWindow(hwnd)
            except Exception:
                pass
            time.sleep(0.04 * _speed)
            try:
                if user32.GetForegroundWindow() == hwnd:
                    break
            except Exception:
                pass

        # Translate to scan code for better compatibility with games
        try:
            scan = user32.MapVirtualKeyW(VK_ESCAPE, 0)
        except Exception:
            scan = 0

        # Helper: send one ESC press (down/up). Prefer SendInput with scan code,
        # fallback to keybd_event. Returns True if any method executed without exception.
        def _send_one_esc():
            try:
                _dwinfo = ctypes.c_ulonglong(0)
                ki_down = KEYBDINPUT(wVk=0, wScan=scan, dwFlags=KEYEVENTF_SCANCODE, time=0, dwExtraInfo=_dwinfo)
                ki_up = KEYBDINPUT(wVk=0, wScan=scan, dwFlags=KEYEVENTF_SCANCODE | KEYEVENTF_KEYUP, time=0, dwExtraInfo=_dwinfo)
                inp_down = INPUT_STRUCT(type=INPUT_KEYBOARD, u=INPUT_UNION(ki=ki_down))
                inp_up = INPUT_STRUCT(type=INPUT_KEYBOARD, u=INPUT_UNION(ki=ki_up))
                user32.SendInput(1, ctypes.byref(inp_down), ctypes.sizeof(INPUT_STRUCT))
                time.sleep(0.02 * _speed)
                user32.SendInput(1, ctypes.byref(inp_up), ctypes.sizeof(INPUT_STRUCT))
                return True
            except Exception:
                try:
                    if scan:
                        user32.keybd_event(0, scan, 0, 0)
                        time.sleep(0.03 * _speed)
                        user32.keybd_event(0, scan, KEYEVENTF_KEYUP, 0)
                    else:
                        user32.keybd_event(VK_ESCAPE, 0, 0, 0)
                        time.sleep(0.03 * _speed)
                        user32.keybd_event(VK_ESCAPE, 0, KEYEVENTF_KEYUP, 0)
                    return True
                except Exception:
                    return False

        # New behaviour: send a single ESC press, wait briefly, then proceed to clicks.
        try:
            # Send ESC _esc_count times (default 1-6). This allows older
            # configurations to request multiple presses; defaults remain fast.
            for _ in range(max(1, _esc_count)):
                _send_one_esc()
                time.sleep(0.02 * _speed)
            # Short wait to allow menu to appear before clicking
            time.sleep(0.25 * _speed)
        except Exception:
            pass

        def click_at(x: int, y: int):
            user32.SetCursorPos(x, y)
            # Short pause to ensure UI has time to react
            time.sleep(0.12 * _speed)
            mi_down = MOUSEINPUT(
                dx=0,
                dy=0,
                mouseData=0,
                dwFlags=MOUSEEVENTF_LEFTDOWN,
                time=0,
                dwExtraInfo=ctypes.c_ulonglong(0),
            )
            mi_up = MOUSEINPUT(
                dx=0,
                dy=0,
                mouseData=0,
                dwFlags=MOUSEEVENTF_LEFTUP,
                time=0,
                dwExtraInfo=ctypes.c_ulonglong(0),
            )
            inp_m_down = INPUT_STRUCT(type=INPUT_MOUSE, u=INPUT_UNION(mi=mi_down))
            inp_m_up = INPUT_STRUCT(type=INPUT_MOUSE, u=INPUT_UNION(mi=mi_up))
            user32.SendInput(1, ctypes.byref(inp_m_down), ctypes.sizeof(INPUT_STRUCT))
            time.sleep(0.06 * _speed)
            user32.SendInput(1, ctypes.byref(inp_m_up), ctypes.sizeof(INPUT_STRUCT))

        def _attach_and_send_click(target_hwnd: int, sx: int, sy: int) -> bool:
            """Attach to the target window's input thread and send SendInput clicks.
            Useful as a last-resort when PostMessage or raw SendInput are ignored in
            exclusive fullscreen contexts.
            """
            try:
                # Obtain the thread id for the target window
                pid = ctypes.c_ulong()
                tid = user32.GetWindowThreadProcessId(target_hwnd, ctypes.byref(pid))
                # Current thread id
                cur_tid = kernel32.GetCurrentThreadId()
                attached = False
                try:
                    user32.AttachThreadInput(cur_tid, tid, True)
                    attached = True
                except Exception:
                    attached = False

                try:
                    user32.SetForegroundWindow(target_hwnd)
                except Exception:
                    pass

                try:
                    user32.SetCursorPos(sx, sy)
                    time.sleep(0.03)
                    mi_down = MOUSEINPUT(dx=0, dy=0, mouseData=0, dwFlags=MOUSEEVENTF_LEFTDOWN, time=0, dwExtraInfo=ctypes.c_ulonglong(0))
                    mi_up = MOUSEINPUT(dx=0, dy=0, mouseData=0, dwFlags=MOUSEEVENTF_LEFTUP, time=0, dwExtraInfo=ctypes.c_ulonglong(0))
                    inp_m_down = INPUT_STRUCT(type=INPUT_MOUSE, u=INPUT_UNION(mi=mi_down))
                    inp_m_up = INPUT_STRUCT(type=INPUT_MOUSE, u=INPUT_UNION(mi=mi_up))
                    user32.SendInput(1, ctypes.byref(inp_m_down), ctypes.sizeof(INPUT_STRUCT))
                    time.sleep(0.02)
                    user32.SendInput(1, ctypes.byref(inp_m_up), ctypes.sizeof(INPUT_STRUCT))
                    return True
                except Exception:
                    return False
                finally:
                    if attached:
                        try:
                            user32.AttachThreadInput(cur_tid, tid, False)
                        except Exception:
                            pass
            except Exception:
                return False

        # Fallback: post mouse messages directly to the game's window so clicks
        # work even if the physical cursor is moved by the user.
        def _post_click_to_hwnd(target_hwnd: int, sx: int, sy: int) -> bool:
            try:
                pt = POINT(sx, sy)
                # Convert screen coords to client coords for the target window
                user32.ScreenToClient(target_hwnd, ctypes.byref(pt))
                x_c = pt.x & 0xFFFF
                y_c = pt.y & 0xFFFF
                lparam = (y_c << 16) | (x_c & 0xFFFF)
                # Move, down, up
                user32.PostMessageW(target_hwnd, WM_MOUSEMOVE, 0, lparam)
                user32.PostMessageW(target_hwnd, WM_LBUTTONDOWN, MK_LBUTTON, lparam)
                time.sleep(0.03 * _speed)
                user32.PostMessageW(target_hwnd, WM_LBUTTONUP, 0, lparam)
                return True
            except Exception:
                return False

        # Try normal SendInput-based clicks first; if they don't work (or the
        # user moved the mouse), fall back to posting messages directly to
        # the game's window so clicks still register.
        try:
            click_at(abs_exit_x, abs_exit_y)
        except Exception:
            pass
        time.sleep(0.22 * _speed)
        try:
            click_at(abs_conf_x, abs_conf_y)
        except Exception:
            pass

        # Ensure clicks via messages if needed (covers cases where SendInput
        # or physical cursor is interfered with).
        try:
            ok = _post_click_to_hwnd(hwnd, abs_exit_x, abs_exit_y)
            if not ok:
                _attach_and_send_click(hwnd, abs_exit_x, abs_exit_y)
            time.sleep(0.12 * _speed)
            ok2 = _post_click_to_hwnd(hwnd, abs_conf_x, abs_conf_y)
            if not ok2:
                _attach_and_send_click(hwnd, abs_conf_x, abs_conf_y)
        except Exception:
            pass
        time.sleep(0.6 * _speed)
        try:
            if _blocked and hasattr(user32, "BlockInput"):
                try:
                    user32.BlockInput(False)
                except Exception:
                    pass
        except Exception:
            pass
        # If we applied a ClipCursor fallback, restore original state (or clear)
        try:
            if '_cursor_clipped' in locals() and _cursor_clipped:
                try:
                    if '_had_original_clip' in locals() and _had_original_clip:
                        user32.ClipCursor(ctypes.byref(_original_clip))
                    else:
                        user32.ClipCursor(None)
                except Exception:
                    try:
                        user32.ClipCursor(None)
                    except Exception:
                        pass
        except Exception:
            pass
    except Exception as e:
        print(f"Automation error: {e}")
        try:
            subprocess.run(f"taskkill /f /pid {pid}", shell=True)
        except Exception:
            pass
        # also attempt to unblock on unexpected errors
        try:
            if _blocked and hasattr(user32, "BlockInput"):
                user32.BlockInput(False)
        except Exception:
            pass


# === UTILS ===

def auto_detect_nwn_path() -> str | None:
    """Попытка найти путь к nwmain.exe через реестр Steam/GOG."""
    import winreg
    paths_to_check = [
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Steam App 704450",
        r"SOFTWARE\GOG.com\Games\1207658960",
        r"SOFTWARE\WOW6432Node\GOG.com\Games\1207658960",
    ]

    for subkey in paths_to_check:
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, subkey) as key:
                path, _ = winreg.QueryValueEx(key, "InstallLocation")
                exe_candidates = [
                    os.path.join(path, "bin", "win32", "nwmain.exe"),
                    os.path.join(path, "bin", "win64", "nwmain.exe"),
                    os.path.join(path, "nwmain.exe"),
                ]
                for exe in exe_candidates:
                    if os.path.exists(exe):
                        return exe
        except OSError:
            continue
    return None


def robust_update_settings_tml(path: str, new_player_name: str) -> None:
    """
    Безопасно обновляет name в [client.identity] секции settings.tml,
    сохраняя формат и отступы.
    """
    if not os.path.exists(path):
        return

    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        if not content.strip():
            return

        lines = content.splitlines()
        new_lines = []
        in_identity = False
        updated = False

        for line in lines:
            stripped = line.strip()

            if stripped == "[client.identity]":
                in_identity = True
            elif stripped.startswith("[") and stripped.endswith("]"):
                in_identity = False

            if in_identity and re.match(r"^\s*name\s*=", line):
                match = re.match(r"^(\s*)name\s*=", line)
                indent = match.group(1) if match else ""
                new_lines.append(f'{indent}name = "{new_player_name}"')
                updated = True
            else:
                new_lines.append(line)

        if updated:
            tmp_path = path + ".tmp"
            with open(tmp_path, "w", encoding="utf-8") as f:
                f.write("\n".join(new_lines))
            safe_replace(tmp_path, path)
    except Exception as e:
        print(f"TML Update Error: {e}")

# === KEYBOARD MAPPING & GENERIC PRESS ===

VK_MAP = {
    # Number keys
    "0": 0x30, "1": 0x31, "2": 0x32, "3": 0x33, "4": 0x34,
    "5": 0x35, "6": 0x36, "7": 0x37, "8": 0x38, "9": 0x39,
    # Letter keys
    "A": 0x41, "B": 0x42, "C": 0x43, "D": 0x44, "E": 0x45,
    "F": 0x46, "G": 0x47, "H": 0x48, "I": 0x49, "J": 0x4A,
    "K": 0x4B, "L": 0x4C, "M": 0x4D, "N": 0x4E, "O": 0x4F,
    "P": 0x50, "Q": 0x51, "R": 0x52, "S": 0x53, "T": 0x54,
    "U": 0x55, "V": 0x56, "W": 0x57, "X": 0x58, "Y": 0x59, "Z": 0x5A,
    # Function keys
    "F1": 0x70, "F2": 0x71, "F3": 0x72, "F4": 0x73, "F5": 0x74,
    "F6": 0x75, "F7": 0x76, "F8": 0x77, "F9": 0x78, "F10": 0x79,
    "F11": 0x7A, "F12": 0x7B,
    # Special keys
    "SPACE": 0x20, "ENTER": 0x0D, "TAB": 0x09, "ESCAPE": 0x1B,
    "BACKSPACE": 0x08, "DELETE": 0x2E, "INSERT": 0x2D,
    "HOME": 0x24, "END": 0x23, "PAGEUP": 0x21, "PAGEDOWN": 0x22,
    "UP": 0x26, "DOWN": 0x28, "LEFT": 0x25, "RIGHT": 0x27,
    # Modifier keys
    "CTRL": 0x11, "CONTROL": 0x11, "SHIFT": 0x10, "ALT": 0x12, "MENU": 0x12,
    "LCTRL": 0xA2, "RCTRL": 0xA3, "LSHIFT": 0xA0, "RSHIFT": 0xA1,
    "LALT": 0xA4, "RALT": 0xA5,
    # Numpad keys
    "NUMPAD0": 0x60, "NUMPAD1": 0x61, "NUMPAD2": 0x62, "NUMPAD3": 0x63,
    "NUMPAD4": 0x64, "NUMPAD5": 0x65, "NUMPAD6": 0x66, "NUMPAD7": 0x67,
    "NUMPAD8": 0x68, "NUMPAD9": 0x69,
    # Symbols
    "MINUS": 0xBD, "-": 0xBD, "PLUS": 0xBB, "=": 0xBB,
    "COMMA": 0xBC, ",": 0xBC, "PERIOD": 0xBE, ".": 0xBE,
    "SEMICOLON": 0xBA, ";": 0xBA, "SLASH": 0xBF, "/": 0xBF,
    "TILDE": 0xC0, "`": 0xC0, "~": 0xC0,
    "LBRACKET": 0xDB, "[": 0xDB, "RBRACKET": 0xDD, "]": 0xDD,
    "BACKSLASH": 0xDC, "\\": 0xDC, "QUOTE": 0xDE, "'": 0xDE,
}

# Mouse button constants
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010


def right_click():
    """Выполняет правый клик мыши."""
    try:
        user32.mouse_event(MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
        user32.mouse_event(MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)
    except Exception as e:
        print(f"[RightClick] Error: {e}")


def press_key_with_modifiers(key_name: str, ctrl: bool = False, shift: bool = False, alt: bool = False):
    """Нажимает клавишу с модификаторами (Ctrl, Shift, Alt).
    
    Args:
        key_name: Имя клавиши (например, 'F4', 'A')
        ctrl: Зажать Ctrl
        shift: Зажать Shift
        alt: Зажать Alt
    """
    key_upper = key_name.upper()
    vk = VK_MAP.get(key_upper)
    
    if not vk:
        try:
            res = user32.VkKeyScanW(ord(key_upper[0]))
            if res != -1:
                vk = res & 0xFF
        except Exception:
            pass
    
    if not vk:
        return
    
    try:
        # Press modifiers
        if ctrl:
            user32.keybd_event(0x11, 0, 0, 0)
        if shift:
            user32.keybd_event(0x10, 0, 0, 0)
        if alt:
            user32.keybd_event(0x12, 0, 0, 0)
        
        time.sleep(0.02)
        
        # Press key
        scan = user32.MapVirtualKeyW(vk, 0)
        user32.keybd_event(vk, scan, 0, 0)
        time.sleep(0.05)
        user32.keybd_event(vk, scan, KEYEVENTF_KEYUP, 0)
        
        time.sleep(0.02)
        
        # Release modifiers
        if alt:
            user32.keybd_event(0x12, 0, KEYEVENTF_KEYUP, 0)
        if shift:
            user32.keybd_event(0x10, 0, KEYEVENTF_KEYUP, 0)
        if ctrl:
            user32.keybd_event(0x11, 0, KEYEVENTF_KEYUP, 0)
    except Exception as e:
        print(f"[KeyWithModifiers] Error: {e}")


def right_click_and_send_sequence(keys: list, delay: float = 0.05):
    """Выполняет правый клик и затем отправляет последовательность клавиш.
    
    Args:
        keys: Список имен клавиш
        delay: Задержка между нажатиями
    """
    right_click()
    press_key_sequence(keys, delay)

def press_key_by_name(key_name: str):
    """Нажимает клавишу по её строковому имени (например, 'F10', '4', 'R', 'SHIFT+F1')."""
    key_upper = key_name.upper().strip()
    
    # Check for combinations (e.g. "SHIFT+F1", "CTRL+C")
    if "+" in key_upper:
        parts = [p.strip() for p in key_upper.split("+")]
        modifiers = {"CTRL": False, "SHIFT": False, "ALT": False}
        main_key = None
        
        for part in parts:
            if part in ["CTRL", "CONTROL", "LCTRL", "RCTRL"]:
                modifiers["CTRL"] = True
            elif part in ["SHIFT", "LSHIFT", "RSHIFT"]:
                modifiers["SHIFT"] = True
            elif part in ["ALT", "MENU", "LALT", "RALT"]:
                modifiers["ALT"] = True
            else:
                main_key = part
        
        if main_key:
            press_key_with_modifiers(main_key, ctrl=modifiers["CTRL"], shift=modifiers["SHIFT"], alt=modifiers["ALT"])
            return

    vk = VK_MAP.get(key_upper)
    
    if not vk:
        # Если не нашли в словаре, пробуем получить код через API (для символов)
        try:
             # VkKeyScan возвращает low-order byte как virtual key code
            res = user32.VkKeyScanW(ord(key_upper[0]))
            if res != -1:
                vk = res & 0xFF
        except Exception:
            pass

    if vk:
        try:
            scan = user32.MapVirtualKeyW(vk, 0)
            user32.keybd_event(vk, scan, 0, 0)  # Down
            time.sleep(0.03)  # 30ms hold — NWN needs time to register the keypress
            user32.keybd_event(vk, scan, KEYEVENTF_KEYUP, 0)  # Up
        except Exception:
            pass


def left_click():
    """Выполняет левый клик мыши."""
    try:
        user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        time.sleep(0.02)
        user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
    except Exception as e:
        print(f"[LeftClick] Error: {e}")


def press_key_sequence(keys: list, delay: float = 0.05):
    """Нажимает последовательность клавиш/действий с задержкой между ними.
    
    Поддерживаемые специальные команды:
        - LEFTCLICK: Левый клик мыши в текущей позиции курсора
        - RIGHTCLICK: Правый клик мыши в текущей позиции курсора
        - Обычные клавиши: NUMPAD0-9, F1-F12, A-Z, и т.д.
    
    Args:
        keys: Список имен клавиш/команд (например, ['F2', 'LEFTCLICK', 'F2'])
        delay: Задержка между действиями в секундах
    """
    for key in keys:
        key_upper = key.upper().strip()
        
        if key_upper == "LEFTCLICK":
            left_click()
        elif key_upper == "RIGHTCLICK":
            right_click()
        else:
            press_key_by_name(key)
        
        time.sleep(delay)


def focus_nwn_window(delay: float = 0):
    """Активирует окно Neverwinter Nights и ждет задержку"""
    try:
        if delay > 0:
            time.sleep(delay)
        
        # Ищем окно Neverwinter Nights
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        
        # Поиск окна по названию
        hwnd = user32.FindWindowW(None, "Neverwinter Nights: Enhanced Edition")
        if not hwnd:
            hwnd = user32.FindWindowW(None, "Neverwinter Nights")
        if not hwnd:
            hwnd = user32.FindWindowW(None, "nwmain")
        
        if hwnd:
            # Активируем окно
            user32.SetForegroundWindow(hwnd)
            time.sleep(0.1)
            print(f"[Focus] NWN window activated")
            return True
        else:
            print("[Focus] NWN window not found")
            return False
    except Exception as e:
        print(f"[Focus] Error: {e}")
        return False


def drag_mouse(from_x: int, from_y: int, to_x: int, to_y: int, duration: float = 0.3):
    """Перетягивает мышь от одной позиции к другой"""
    try:
        import ctypes
        
        # Нажимаем левую кнопку мыши в исходной позиции
        ctypes.windll.user32.SetCursorPos(from_x, from_y)
        time.sleep(0.05)
        ctypes.windll.user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        time.sleep(0.1)
        
        # Движимся к целевой позиции
        steps = max(2, int(duration * 30))
        for i in range(steps + 1):
            t = i / steps
            # Smoothstep интерполяция
            t_smooth = t * t * (3 - 2 * t)
            x = int(from_x + (to_x - from_x) * t_smooth)
            y = int(from_y + (to_y - from_y) * t_smooth)
            ctypes.windll.user32.SetCursorPos(x, y)
            time.sleep(duration / (steps + 1))
        
        # Отпускаем кнопку
        time.sleep(0.05)
        ctypes.windll.user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        time.sleep(0.1)
        
    except Exception as e:
        print(f"[Drag] Error: {e}")


def get_keyboard_layout(hwnd: int) -> int:
    """Returns the keyboard layout identifier (HKL) for the thread of the given window."""
    try:
        tid = user32.GetWindowThreadProcessId(hwnd, None)
        hkl = user32.GetKeyboardLayout(tid)
        return hkl & 0xFFFF  # Return only the language ID (low word)
    except Exception:
        return 0

def set_keyboard_layout(hwnd: int, lang_id: int):
    """Requests a keyboard layout switch for the given window (e.g., 0x0409 for English)."""
    try:
        # Load the keyboard layout first to ensure it's available
        # string format "00000409"
        hkl_str = f"{lang_id:08x}"
        hkl = user32.LoadKeyboardLayoutW(hkl_str, 1) # 1 = KLF_ACTIVATE
        
        # Send message to switch
        user32.PostMessageW(hwnd, WM_INPUTLANGCHANGEREQUEST, 0, hkl)
    except Exception as e:
        print(f"[SetLayout] Error: {e}")



# === MACRO RECORDING ===

class MacroRecorder:
    """Records mouse movements and clicks for macro playback"""
    
    def __init__(self):
        self.recording = False
        self.events = []  # List of (timestamp, event_type, x, y)
        self.start_time = 0
        self._hook = None
        self._stop_requested = False
    
    def start_recording(self, callback_on_stop=None):
        """Start recording mouse events. Stops on Alt+Tab (window focus loss)."""
        import threading
        
        self.recording = True
        self.events = []
        self.start_time = time.time()
        self._stop_requested = False
        self._callback = callback_on_stop
        
        # Get current foreground window (should be NWN)
        self._target_hwnd = user32.GetForegroundWindow()
        
        # Start recording thread
        self._record_thread = threading.Thread(target=self._record_loop, daemon=True)
        self._record_thread.start()
        
        return True
    
    def stop_recording(self):
        """Stop recording and return events"""
        self._stop_requested = True
        self.recording = False
        return self.events.copy()
    
    def _record_loop(self):
        """Main recording loop - polls mouse state"""
        last_pos = None
        last_button_state = False
        
        while self.recording and not self._stop_requested:
            # Check if foreground window changed (Alt+Tab detection)
            current_hwnd = user32.GetForegroundWindow()
            if current_hwnd != self._target_hwnd:
                # Window changed - stop recording
                self.recording = False
                break
            
            # Get current mouse position
            point = POINT()
            user32.GetCursorPos(ctypes.byref(point))
            x, y = point.x, point.y
            
            # Get mouse button state
            button_down = (user32.GetAsyncKeyState(0x01) & 0x8000) != 0
            
            timestamp = time.time() - self.start_time
            
            # Record position changes (with throttling)
            if last_pos is None or (abs(x - last_pos[0]) > 2 or abs(y - last_pos[1]) > 2):
                if button_down:  # Only record movement while dragging
                    self.events.append((timestamp, "move", x, y))
                last_pos = (x, y)
            
            # Record button state changes
            if button_down and not last_button_state:
                self.events.append((timestamp, "down", x, y))
            elif not button_down and last_button_state:
                self.events.append((timestamp, "up", x, y))
            
            last_button_state = button_down
            time.sleep(0.01)  # 100Hz polling
        
        # Call callback when done
        if self._callback:
            try:
                self._callback(self.events)
            except Exception as e:
                print(f"[MacroRecorder] Callback error: {e}")
    
    def is_recording(self):
        return self.recording


def play_macro(events: list, speed_multiplier: float = 1.0):
    """Play back recorded mouse events"""
    if not events:
        return
    
    try:
        last_time = 0
        for event in events:
            timestamp, event_type, x, y = event
            
            # Wait for timing
            delay = (timestamp - last_time) / speed_multiplier
            if delay > 0:
                time.sleep(delay)
            last_time = timestamp
            
            # Execute event
            if event_type == "move":
                user32.SetCursorPos(x, y)
            elif event_type == "down":
                user32.SetCursorPos(x, y)
                time.sleep(0.02)
                user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            elif event_type == "up":
                user32.SetCursorPos(x, y)
                time.sleep(0.02)
                user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        
        # Ensure mouse is released at end
        user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        
    except Exception as e:
        print(f"[PlayMacro] Error: {e}")


# Global recorder instance
_macro_recorder = MacroRecorder()

def get_macro_recorder() -> MacroRecorder:
    return _macro_recorder


# === CUSTOM FONT LOADING ===

# Windows GDI constant for AddFontResource
FR_PRIVATE = 0x10

gdi32 = ctypes.windll.gdi32

# Cache flag to avoid loading fonts multiple times
_fonts_loaded = False

def load_custom_fonts(fonts_dir: str = None) -> list:
    """Load custom TTF fonts from the fonts directory for this app session.
    
    Uses Windows GDI AddFontResourceEx to temporarily add fonts.
    Fonts are only available to this process and are removed when app exits.
    
    Args:
        fonts_dir: Path to fonts directory. Defaults to 'fonts' in app root.
        
    Returns:
        List of successfully loaded font file names.
    """
    global _fonts_loaded
    
    # Skip if already loaded
    if _fonts_loaded:
        return []
    
    _fonts_loaded = True
    loaded = []
    
    try:
        if fonts_dir is None:
            # Get the app's root directory
            import sys
            if getattr(sys, 'frozen', False):
                app_dir = os.path.dirname(sys.executable)
            else:
                app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            fonts_dir = os.path.join(app_dir, 'fonts')
        
        if not os.path.exists(fonts_dir):
            print(f"[Fonts] Directory not found: {fonts_dir}")
            return loaded
        
        # Load all TTF files
        for filename in os.listdir(fonts_dir):
            if filename.lower().endswith('.ttf'):
                font_path = os.path.join(fonts_dir, filename)
                try:
                    # AddFontResourceExW returns number of fonts loaded (0 on failure)
                    result = gdi32.AddFontResourceExW(font_path, FR_PRIVATE, 0)
                    if result > 0:
                        loaded.append(filename)
                        print(f"[Fonts] Loaded: {filename}")
                    else:
                        print(f"[Fonts] Failed to load: {filename}")
                except Exception as e:
                    print(f"[Fonts] Error loading {filename}: {e}")
        
        # Notify all windows about font change
        if loaded:
            try:
                user32.SendMessageW(0xFFFF, 0x001D, 0, 0)  # HWND_BROADCAST, WM_FONTCHANGE
            except Exception:
                pass
                
    except Exception as e:
        print(f"[Fonts] Error: {e}")
    
    return loaded
def set_run_on_startup(enabled: bool) -> bool:
    import winreg
    """Add or remove the application from Windows Startup (HKCU\\...\\Run)."""
    try:
        import sys
        if getattr(sys, 'frozen', False):
            exe_path = sys.executable
        else:
            # If running as script, use pythonw.exe to avoid console window if possible,
            # or just python.exe. Correctly quoting the path is crucial.
            exe_path = sys.executable + ' "' + os.path.abspath(sys.argv[0]) + '"'
        
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        app_name = "NWNManager1609"
        
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_ALL_ACCESS) as key:
            if enabled:
                winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, exe_path)
            else:
                try:
                    winreg.DeleteValue(key, app_name)
                except FileNotFoundError:
                    pass
        return True
    except Exception as e:
        print(f"[StartupRegistry] Error: {e}")
        return False
