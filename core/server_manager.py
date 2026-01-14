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

    PING_INTERVAL_MS = 60000  # 60 seconds

    def __init__(self, app):
        self.app = app
        self._auto_ping_job = None

    def start_auto_ping(self):
        """Start automatic ping refresh every 60 seconds."""
        self._schedule_next_ping()

    def _schedule_next_ping(self):
        """Schedule the next ping check."""
        if self._auto_ping_job:
            try:
                self.app.root.after_cancel(self._auto_ping_job)
            except Exception:
                pass
        self._auto_ping_job = self.app.root.after(self.PING_INTERVAL_MS, self._do_auto_ping)

    def _do_auto_ping(self):
        """Perform auto ping and schedule next."""
        self.ping_all_servers()
        self._schedule_next_ping()

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

        srv_val = self.app.server_var.get().strip()
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
        selected = self.app.server_var.get()
        if not selected:
            return
        
        if messagebox.askyesno("Confirm", f"Remove server '{selected}'?"):
            self.app.servers = [s for s in self.app.servers if s["name"] != selected]
            self.app.save_data()
            self.refresh_server_list()
            
            # Reset selection if any
            if self.app.servers:
                self.app.server_var.set(self.app.servers[0]["name"])
            else:
                self.app.server_var.set("")
            self.check_server_status()

    def refresh_server_list(self):
        """Refresh server buttons."""
        if hasattr(self.app, '_create_server_buttons'):
            self.app._create_server_buttons()
            # Trigger ping check
            self.ping_all_servers()

    def toggle_server_ui(self, enable=True):
        """Refresh server buttons and status."""
        self.refresh_server_list()

    def ping_all_servers(self):
        """Pings all servers in background and updates UI."""
        threading.Thread(target=self._run_batched_ping, daemon=True).start()

    def _run_batched_ping(self):
        import concurrent.futures
        import subprocess
        import time
        
        def _ping_task(srv):
            name = srv["name"]
            ip = srv["ip"]
            try:
                host = ip.split(":")[0] if ":" in ip else ip
                cmd = ["ping", "-n", "1", "-w", "1000", host]
                
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                
                t0 = time.time()
                proc = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    startupinfo=startupinfo
                )
                dt = int((time.time() - t0) * 1000)
                
                if proc.returncode == 0:
                    try:
                        out = proc.stdout.decode("cp866", errors="ignore")
                        if "time=" in out: # Windows output: "time=15ms"
                            part = out.split("time=")[1]
                            ms_str = part.split("ms")[0].strip()
                            return name, int(ms_str)
                        if "time<" in out:
                            return name, 1
                    except:
                        pass
                    return name, dt
                else:
                    return name, -1 # Offline
            except:
                return name, -1

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            if not hasattr(self.app, 'servers'):
                return
            futures = [executor.submit(_ping_task, s) for s in self.app.servers]
            
            for future in concurrent.futures.as_completed(futures):
                try:
                    name, ms = future.result()
                    if hasattr(self.app, 'update_server_latency'):
                        self.app.root.after(0, lambda n=name, m=ms: self.app.update_server_latency(n, m))
                except:
                    pass
