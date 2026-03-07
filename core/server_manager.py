"""
Server management for NWN Manager.

Handles server CRUD, selection updates.
"""

import subprocess
import threading
from tkinter import messagebox

from ui.ui_base import COLORS
from ui.dialogs import AddServerDialog


class ServerManager:
    """Manages servers and server selection."""

    def __init__(self, app):
        self.app = app

    def on_server_selected(self):
        """Called when user selects a server from combobox - save to current profile."""
        try:
            selected_server = self.app.server_var.get()
            if self.app.current_profile and selected_server:
                self.app.current_profile.server = selected_server
                self.app.save_data()
        except Exception as e:
            self.app.log_error("_on_server_selected", e)

    def add_server(self):
        def on_add(data: dict):
            if not data.get("ip"):
                return
            from core.models import Server
            new_srv = Server.from_dict(data)
            self.app.servers.append(new_srv)
            self.app.save_data()
            self.refresh_server_list()
            self.app.server_var.set(new_srv.name)
        
        AddServerDialog(self.app.root, on_add)

    def remove_server(self):
        selected = self.app.server_var.get()
        if not selected:
            return
        
        if messagebox.askyesno("Confirm", f"Remove server '{selected}'?"):
            self.app.servers = [s for s in self.app.servers if s.name != selected]
            self.app.save_data()
            self.refresh_server_list()
            
            # Reset selection if any
            if self.app.servers:
                self.app.server_var.set(self.app.servers[0].name)
            else:
                self.app.server_var.set("")

    def refresh_server_list(self):
        """Refresh server buttons."""
        if hasattr(self.app, '_create_server_buttons'):
            self.app._create_server_buttons()

    def toggle_server_ui(self, enable=True):
        """Refresh server buttons."""
        self.refresh_server_list()
