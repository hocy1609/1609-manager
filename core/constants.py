"""
Configuration constants for NWN Manager.

This module centralizes all "magic numbers" and configuration defaults
to make the codebase more maintainable and self-documenting.
"""

# === TIMING CONSTANTS (milliseconds) ===

# How often to check for dead processes
PROCESS_MONITOR_INTERVAL_MS = 1000

# Delay before checking paths silently on startup
STARTUP_PATH_CHECK_DELAY_MS = 500

# Delay before setting app window properties
APPWINDOW_SETUP_DELAY_MS = 10

# Debounce delay for saving data after changes
SAVE_DEBOUNCE_DELAY_MS = 3000

# Status bar update interval
STATUS_BAR_UPDATE_INTERVAL_MS = 1000

# Delay for inline action hide
INLINE_ACTION_HIDE_DELAY_MS = 150


# === TIMING CONSTANTS (seconds) ===

# Default exit speed for game automation
DEFAULT_EXIT_SPEED = 0.1

# Timeout for waiting for game process to exit during restart
GAME_EXIT_TIMEOUT_SECONDS = 5

# Sleep interval when waiting for game exit
GAME_EXIT_CHECK_INTERVAL = 0.1


# === UI CONSTANTS ===

# Default window dimensions
DEFAULT_WINDOW_WIDTH = 960
DEFAULT_WINDOW_HEIGHT = 680
MIN_WINDOW_WIDTH = 760
MIN_WINDOW_HEIGHT = 520

# Layout mode threshold
COMPACT_LAYOUT_THRESHOLD_WIDTH = 900

# Padding values (scaled by window size)
SIDEBAR_MIN_WIDTH = 200
SIDEBAR_MAX_WIDTH = 260

# Number of backups to keep per file type
MAX_BACKUPS_PER_FILE = 10


# === GAME AUTOMATION CONSTANTS ===

# Default exit button coordinates (relative to window)
DEFAULT_EXIT_COORDS_X = 950
DEFAULT_EXIT_COORDS_Y = 640

# Default confirm button coordinates
DEFAULT_CONFIRM_COORDS_X = 802
DEFAULT_CONFIRM_COORDS_Y = 613

# Default ESC key press count
DEFAULT_ESC_COUNT = 1

# Default clip margin for cursor positioning
DEFAULT_CLIP_MARGIN = 48


# === LOG MONITOR CONSTANTS ===

# Default Open Wounds key
DEFAULT_OPEN_WOUNDS_KEY = "F1"


# === CRAFT CONSTANTS ===

# Default craft iterations
DEFAULT_CRAFT_ITERATIONS = 1

# Default delay between craft actions (seconds)
DEFAULT_CRAFT_DELAY = 0.5


# === FILE PATHS ===

# Settings and session file names
SETTINGS_FILENAME = "nwn_settings.json"
SESSIONS_FILENAME = "nwn_sessions.json"
LOG_FILENAME = "nwn_manager.log"

# Backup directory name
BACKUP_DIR_NAME = "_manager_backups"

# Macro directory name
MACROS_DIR_NAME = "macros"


# === DEFAULT VALUES ===

# Default category for new profiles
DEFAULT_CATEGORY = "General"

# Default theme
DEFAULT_THEME = "dark"

# Default NWN executable name
DEFAULT_EXE_NAME = "nwmain.exe"

# Steam default path (fallback)
STEAM_DEFAULT_NWN_PATH = r"C:\Program Files (x86)\Steam\steamapps\common\Neverwinter Nights\bin\win32\nwmain.exe"


# === CD-KEY VALIDATION ===

# CD-Key segment length
CDKEY_SEGMENT_LENGTH = 5

# Number of segments in a CD-Key
CDKEY_SEGMENT_COUNT = 7

# Total length of CD-Key without dashes
CDKEY_TOTAL_LENGTH = CDKEY_SEGMENT_LENGTH * CDKEY_SEGMENT_COUNT  # 35
