"""
Centralized error handler for NWN Manager.

Provides consistent error logging and optional user notification.
"""

import logging
from datetime import datetime
from typing import Optional, Any

# Try to import messagebox, but make it optional for testing
try:
    from tkinter import messagebox
    _HAS_MESSAGEBOX = True
except ImportError:
    _HAS_MESSAGEBOX = False


class ErrorHandler:
    """
    Centralized error handler for the NWN Manager application.
    
    Usage:
        from core.error_handler import ErrorHandler
        
        try:
            risky_operation()
        except Exception as e:
            ErrorHandler.handle("risky_operation", e, show_user=True)
    """
    
    _log_path: Optional[str] = None
    _root: Optional[Any] = None
    
    @classmethod
    def configure(cls, log_path: str, root: Any = None) -> None:
        """
        Configure the error handler with log path and optional root window.
        
        Args:
            log_path: Path to the log file
            root: Optional tkinter root window for messagebox parent
        """
        cls._log_path = log_path
        cls._root = root
    
    @classmethod
    def handle(
        cls,
        context: str,
        exc: Exception,
        show_user: bool = False,
        user_message: Optional[str] = None,
        level: str = "error"
    ) -> None:
        """
        Handle an exception with consistent logging and optional user notification.
        
        Args:
            context: Description of where the error occurred (e.g., "save_data", "launch_game")
            exc: The exception that was caught
            show_user: Whether to show a messagebox to the user
            user_message: Custom message for the user (defaults to str(exc))
            level: Log level - "error", "warning", or "info"
        """
        # Log to file
        cls._log_to_file(context, exc, level)
        
        # Log to logging module
        log_func = getattr(logging, level, logging.error)
        log_func(f"{context}: {exc}", exc_info=True)
        
        # Show to user if requested
        if show_user and _HAS_MESSAGEBOX:
            cls._show_to_user(context, exc, user_message)
    
    @classmethod
    def _log_to_file(cls, context: str, exc: Exception, level: str) -> None:
        """Write error to the log file."""
        if not cls._log_path:
            return
        
        try:
            import os
            os.makedirs(os.path.dirname(cls._log_path), exist_ok=True)
            
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(cls._log_path, "a", encoding="utf-8") as f:
                f.write(f"[{ts}] [{level.upper()}] {context}: {exc}\n")
        except Exception:
            # Logger should never crash the application
            logging.exception("Failed to write to error log")
    
    @classmethod
    def _show_to_user(
        cls,
        context: str,
        exc: Exception,
        user_message: Optional[str]
    ) -> None:
        """Show error message to the user."""
        try:
            title = "Error"
            message = user_message or str(exc)
            messagebox.showerror(title, message, parent=cls._root)
        except Exception:
            logging.exception("Failed to show error messagebox")
    
    @classmethod
    def warning(cls, context: str, message: str, show_user: bool = False) -> None:
        """Log a warning (not tied to an exception)."""
        logging.warning(f"{context}: {message}")
        cls._log_to_file(context, Exception(message), "warning")
        
        if show_user and _HAS_MESSAGEBOX:
            try:
                messagebox.showwarning("Warning", message, parent=cls._root)
            except Exception:
                logging.exception("Failed to show warning messagebox")
    
    @classmethod
    def info(cls, context: str, message: str) -> None:
        """Log an info message."""
        logging.info(f"{context}: {message}")


# Shortcut functions for convenience
def handle_error(context: str, exc: Exception, show_user: bool = False, **kwargs) -> None:
    """Shortcut for ErrorHandler.handle()."""
    ErrorHandler.handle(context, exc, show_user=show_user, **kwargs)


def log_warning(context: str, message: str, show_user: bool = False) -> None:
    """Shortcut for ErrorHandler.warning()."""
    ErrorHandler.warning(context, message, show_user=show_user)
