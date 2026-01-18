"""
System Tray Manager for NWN Manager.

Provides minimize-to-tray functionality using pystray.
"""

import threading
from typing import Optional, Callable

try:
    import pystray
    from PIL import Image, ImageDraw
    TRAY_AVAILABLE = True
except ImportError:
    TRAY_AVAILABLE = False


import os
import sys

def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


def create_default_icon(size: int = 64) -> "Image.Image":
    """Create a simple default icon for the tray, or load 'logo.png'."""
    if not TRAY_AVAILABLE:
        return None
    
    # Try loading custom logo
    try:
        # Check for logo.png or logo.ico
        for name in ["logo.png", "logo.ico"]:
            icon_path = get_resource_path(name)
            if os.path.exists(icon_path):
                img = Image.open(icon_path)
                # Resize if needed, though pystray usually handles it
                return img
    except Exception as e:
        print(f"Failed to load custom icon: {e}")
    
    # Create a simple colored square icon as fallback
    image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    
    # Draw a rounded rectangle (16:09 themed)
    margin = 4
    draw.rounded_rectangle(
        [margin, margin, size - margin, size - margin],
        radius=8,
        fill=(126, 200, 227, 255),  # Accent color #7EC8E3
        outline=(30, 33, 40, 255),  # Dark border
        width=2
    )
    
    # Draw "16" text
    draw.text((size//4, size//4), "16", fill=(30, 33, 40, 255))
    
    return image


class TrayManager:
    """Manages system tray icon and menu."""
    
    def __init__(self, app):
        self.app = app
        self.icon: Optional["pystray.Icon"] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._minimized = False
    
    def is_available(self) -> bool:
        """Check if tray functionality is available."""
        return TRAY_AVAILABLE
    
    def setup(self, on_show: Callable = None, on_quit: Callable = None):
        """Setup the tray icon with menu and start it immediately."""
        if not TRAY_AVAILABLE:
            return False
        
        self._on_show = on_show or self._default_show
        self._on_quit = on_quit or self._default_quit
        
        # Create menu
        menu = pystray.Menu(
            pystray.MenuItem("Show", self._on_show, default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit", self._on_quit)
        )
        
        # Create icon
        icon_image = create_default_icon()
        self.icon = pystray.Icon(
            "1609_manager",
            icon_image,
            "16:09 Manager",
            menu
        )
        
        # Start icon thread - icon will be visible immediately
        self._start_tray()
        
        return True
    
    def _start_tray(self):
        """Start the tray icon in background thread."""
        if not self.icon or self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._run_icon, daemon=True)
        self._thread.start()
    
    def _run_icon(self):
        """Run the icon loop."""
        try:
            # Run the icon - it will stay running until stop() is called
            self.icon.run()
        except Exception as e:
            print(f"[TrayManager] Error: {e}")
        finally:
            self._running = False
    
    def stop(self):
        """Stop the tray icon."""
        if self.icon:
            try:
                self.icon.stop()
            except Exception:
                pass
        self._running = False
        self._minimized = False
    
    def minimize_to_tray(self):
        """Hide the window and show tray icon."""
        if not self.icon:
            return False
        
        try:
            # Hide the main window
            self.app.root.withdraw()
            self._minimized = True
            
            # Icon is already running from setup, just make sure it's visible
            if self.icon:
                try:
                    self.icon.visible = True
                except Exception:
                    pass
            
            return True
        except Exception as e:
            print(f"[TrayManager] Minimize error: {e}")
            return False
    
    def restore_from_tray(self):
        """Show the window from tray."""
        try:
            self._minimized = False
            self.app.root.deiconify()
            self.app.root.lift()
            self.app.root.focus_force()
        except Exception as e:
            print(f"[TrayManager] Restore error: {e}")
    
    def is_minimized(self) -> bool:
        """Check if window is currently minimized to tray."""
        return self._minimized
    
    def _default_show(self, icon=None, item=None):
        """Default action to show the window."""
        self.app.root.after(0, self.restore_from_tray)
    
    def _default_quit(self, icon=None, item=None):
        """Default quit action."""
        self.stop()
        self.app.root.after(0, self._force_quit)
    
    def _force_quit(self):
        """Actually quit the application."""
        try:
            self.app.root.destroy()
        except Exception:
            import sys
            sys.exit(0)
