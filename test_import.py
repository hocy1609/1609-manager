import sys
import os

print(f"CWD: {os.getcwd()}")
print(f"Sys Path: {sys.path}")

try:
    import core
    print(f"Core imported: {core}")
    from core import log_monitor_manager
    print(f"LogMonitorManager imported: {log_monitor_manager}")
except ImportError as e:
    print(f"Import Error: {e}")
except Exception as e:
    print(f"Other Error: {e}")
