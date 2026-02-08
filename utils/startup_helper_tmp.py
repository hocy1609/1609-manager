
def set_run_on_startup(enabled: bool) -> bool:
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
