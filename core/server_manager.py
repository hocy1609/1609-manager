"""
Server management for NWN Manager.

Handles server CRUD, selection updates, and status checks.
"""

import subprocess
import threading
from tkinter import messagebox

from ui.ui_base import COLORS
from ui.dialogs import AddServerDialog


class ServerManager:
    """Manages servers and server status checks."""

    def __init__(self, app):
        self.app = app

    def on_server_selected(self):
        """Called when user selects a server from combobox - save to current profile."""
        try:
            selected_server = self.app.server_var.get()
            if self.app.current_profile and selected_server:
                self.app.current_profile["server"] = selected_server
                self.app.save_data()
        except Exception as e:
            self.app.log_error("_on_server_selected", e)
        self.check_server_status()

    def check_server_status(self):
        # Show status only when game NOT running; hide detailed status when running
        try:
            has_sessions = bool(getattr(self.app.sessions, "sessions", None))
        except Exception:
            has_sessions = False
        if has_sessions and self.app.sessions.sessions:
            try:
                if self.app.status_lbl.cget("text") != "Game Running":
                    self.app.status_lbl.config(text="Game Running", fg=COLORS.get("accent", "#ffaa00"))
            except Exception:
                pass
            return

        srv_val = self.app.cb_server.get().strip()
        if not srv_val:
            return

        srv_ip_full = next(
            (s["ip"] for s in self.app.servers if s["name"] == srv_val),
            srv_val,
        )

        def ping_thread(ip_str: str):
            try:
                host = ip_str.split(":")[0] if ":" in ip_str else ip_str
                cmd = ["ping", "-n", "1", "-w", "1000", host]
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                proc = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    startupinfo=startupinfo,
                )

                new_text = "● Server Online" if proc.returncode == 0 else "● Server Offline"
                new_fg = COLORS["success"] if proc.returncode == 0 else COLORS["offline"]

                def _update():
                    try:
                        if self.app.status_lbl.cget("text") != new_text:
                            self.app.status_lbl.config(text=new_text, fg=new_fg)
                    except Exception:
                        pass
                self.app.root.after(0, _update)

            except Exception as e:
                self.app.log_error("check_server_status", e)
                self.app.root.after(
                    0,
                    lambda: self.app.status_lbl.config(
                        text="● Connection Error",
                        fg=COLORS["offline"],
                    ),
                )

        threading.Thread(target=ping_thread, args=(srv_ip_full,)).start()

    def add_server(self):
        def on_add(data: dict):
            if not data.get("ip"):
                return
            self.app.servers.append(data)
            self.app.save_data()
            self.refresh_server_list()
            self.app.server_var.set(data["name"])
            self.check_server_status()

        AddServerDialog(self.app.root, on_add)

    def remove_server(self):
        current = self.app.server_var.get()
        if not current:
            return
        is_saved = any(s["name"] == current for s in self.app.servers)
        if not is_saved:
            messagebox.showinfo(
                "Info",
                "This IP is not saved in the list.",
                parent=self.app.root,
            )
            return
        if len(self.app.servers) <= 1:
            messagebox.showwarning(
                "Warning",
                "Cannot remove the last server!",
                parent=self.app.root,
            )
            return
        if messagebox.askyesno(
            "Confirm",
            f"Remove server '{current}'?",
            parent=self.app.root,
        ):
            self.app.servers = [
                s for s in self.app.servers if s["name"] != current
            ]
            self.app.save_data()
            self.refresh_server_list()
            self.app.server_var.set(self.app.servers[0]["name"])
            self.check_server_status()

    def refresh_server_list(self):
        names = [s["name"] for s in self.app.servers]
        self.app.cb_server["values"] = names

    def toggle_server_ui(self):
        """Refresh server combobox and status."""
        try:
            srv_names = [s.get("name", "") for s in self.app.servers if s.get("ip")]
            self.app.cb_server.configure(values=srv_names)
        except Exception:
            pass
        try:
            self.check_server_status()
        except Exception:
            pass
