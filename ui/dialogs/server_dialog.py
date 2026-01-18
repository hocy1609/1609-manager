import tkinter as tk
from tkinter import ttk, messagebox
from ui.ui_base import BaseDialog, ModernButton, COLORS

class AddServerDialog(BaseDialog):
    def __init__(self, parent, on_save):
        super().__init__(parent, "Add Server", 400, 250)
        self.on_save = on_save

        content = tk.Frame(self, bg=COLORS["bg_root"])
        content.pack(fill="both", expand=True, padx=20, pady=20)

        self.name_var = tk.StringVar()
        self.ip_var = tk.StringVar()

        tk.Label(
            content,
            text="Server Name:",
            bg=COLORS["bg_root"],
            fg=COLORS["fg_dim"],
        ).pack(anchor="w")
        tk.Entry(
            content,
            textvariable=self.name_var,
            bg=COLORS["bg_input"],
            fg=COLORS["fg_text"],
            relief="flat",
        ).pack(fill="x", pady=(0, 10), ipady=3)

        tk.Label(
            content,
            text="Server Address (IP/Domain):",
            bg=COLORS["bg_root"],
            fg=COLORS["fg_dim"],
        ).pack(anchor="w")
        tk.Entry(
            content,
            textvariable=self.ip_var,
            bg=COLORS["bg_input"],
            fg=COLORS["fg_text"],
            relief="flat",
        ).pack(fill="x", pady=(0, 10), ipady=3)

        btn_frame = tk.Frame(content, bg=COLORS["bg_root"])
        btn_frame.pack(fill="x", pady=10, side="bottom")

        ModernButton(
            btn_frame,
            COLORS["success"],
            COLORS["success_hover"],
            text="Add",
            width=10,
            command=self.save,
        ).pack(side="right", padx=(10, 0))

        ModernButton(
            btn_frame,
            COLORS["bg_panel"],
            COLORS["border"],
            text="Cancel",
            width=10,
            command=self.destroy,
        ).pack(side="right")

        self.finalize_window(parent)

    def save(self):
        name = self.name_var.get().strip()
        ip = self.ip_var.get().strip()
        if name and ip:
            self.on_save({"name": name, "ip": ip})
            self.destroy()
        else:
            messagebox.showwarning(
                "Error",
                "Both fields are required",
                parent=self,
            )


class ServerManagementDialog(BaseDialog):
    """Dialog for managing servers (add/edit/delete) in current group."""
    
    def __init__(self, parent, servers: list, on_save):
        super().__init__(parent, "Manage Servers", 500, 400)
        self.servers = [dict(s) for s in servers]  # Copy
        self.on_save = on_save
        
        content = tk.Frame(self, bg=COLORS["bg_root"])
        content.pack(fill="both", expand=True, padx=20, pady=20)
        
        tk.Label(
            content,
            text="Servers in current group:",
            bg=COLORS["bg_root"],
            fg=COLORS["fg_dim"],
            font=("Segoe UI", 10),
        ).pack(anchor="w")
        
        # Server listbox
        list_frame = tk.Frame(content, bg=COLORS["bg_root"])
        list_frame.pack(fill="both", expand=True, pady=(5, 10))
        
        self.lb = tk.Listbox(
            list_frame,
            bg=COLORS["bg_input"],
            fg=COLORS["fg_text"],
            bd=0,
            highlightthickness=1,
            highlightbackground=COLORS["border"],
            font=("Segoe UI", 10),
        )
        self.lb.pack(fill="both", expand=True, side="left")
        
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.lb.yview)
        scrollbar.pack(side="right", fill="y")
        self.lb.config(yscrollcommand=scrollbar.set)
        
        self._refresh_list()
        
        # Action buttons
        btn_frame = tk.Frame(content, bg=COLORS["bg_root"])
        btn_frame.pack(fill="x", pady=(0, 10))
        
        ModernButton(
            btn_frame,
            COLORS["success"],
            COLORS["success_hover"],
            text="Add",
            width=6,
            command=self._add_server,
        ).pack(side="left", padx=(0, 3))
        
        ModernButton(
            btn_frame,
            COLORS["bg_panel"],
            COLORS["border"],
            text="Edit",
            width=6,
            command=self._edit_server,
        ).pack(side="left", padx=(0, 3))
        
        ModernButton(
            btn_frame,
            COLORS["danger"],
            COLORS["danger_hover"],
            text="Delete",
            width=6,
            command=self._delete_server,
        ).pack(side="left", padx=(0, 10))
        
        # Move buttons
        ModernButton(
            btn_frame,
            COLORS["bg_panel"],
            COLORS["border"],
            text="▲",
            width=3,
            command=self._move_up,
        ).pack(side="left", padx=(0, 3))
        
        ModernButton(
            btn_frame,
            COLORS["bg_panel"],
            COLORS["border"],
            text="▼",
            width=3,
            command=self._move_down,
        ).pack(side="left")
        
        # Save/Cancel
        bottom_frame = tk.Frame(self, bg=COLORS["bg_root"])
        bottom_frame.pack(fill="x", padx=20, pady=10, side="bottom")
        
        ModernButton(
            bottom_frame,
            COLORS["success"],
            COLORS["success_hover"],
            text="Save",
            width=10,
            command=self._save_and_close,
        ).pack(side="right", padx=(10, 0))
        
        ModernButton(
            bottom_frame,
            COLORS["bg_panel"],
            COLORS["border"],
            text="Cancel",
            width=10,
            command=self.destroy,
        ).pack(side="right")
        
        self.finalize_window(parent)
    
    def _refresh_list(self):
        self.lb.delete(0, tk.END)
        for s in self.servers:
            self.lb.insert(tk.END, f"{s['name']} - {s['ip']}")
    
    def _add_server(self):
        def on_add(data):
            self.servers.append(data)
            self._refresh_list()
        AddServerDialog(self, on_add)
    
    def _edit_server(self):
        sel = self.lb.curselection()
        if not sel:
            return
        idx = sel[0]
        srv = self.servers[idx]
        
        # Create simple Toplevel dialog (not BaseDialog to avoid grab conflicts)
        edit_win = tk.Toplevel(self)
        edit_win.title("Edit Server")
        edit_win.geometry("400x180")
        edit_win.configure(bg=COLORS["bg_root"])
        edit_win.transient(self)
        edit_win.resizable(False, False)
        
        name_var = tk.StringVar(value=srv["name"])
        ip_var = tk.StringVar(value=srv["ip"])
        
        frame = tk.Frame(edit_win, bg=COLORS["bg_root"])
        frame.pack(fill="both", expand=True, padx=20, pady=15)
        
        tk.Label(frame, text="Name:", bg=COLORS["bg_root"], fg=COLORS["fg_dim"]).pack(anchor="w")
        tk.Entry(frame, textvariable=name_var, bg=COLORS["bg_input"], fg=COLORS["fg_text"], relief="flat").pack(fill="x", pady=(0, 10), ipady=3)
        
        tk.Label(frame, text="IP/Address:", bg=COLORS["bg_root"], fg=COLORS["fg_dim"]).pack(anchor="w")
        tk.Entry(frame, textvariable=ip_var, bg=COLORS["bg_input"], fg=COLORS["fg_text"], relief="flat").pack(fill="x", pady=(0, 10), ipady=3)
        
        def do_save():
            name = name_var.get().strip()
            ip = ip_var.get().strip()
            if name and ip:
                self.servers[idx] = {"name": name, "ip": ip}
                self._refresh_list()
                edit_win.destroy()
        
        btn_f = tk.Frame(frame, bg=COLORS["bg_root"])
        btn_f.pack(fill="x", pady=5)
        ModernButton(btn_f, COLORS["success"], COLORS["success_hover"], text="Save", width=8, command=do_save).pack(side="right", padx=5)
        ModernButton(btn_f, COLORS["bg_panel"], COLORS["border"], text="Cancel", width=8, command=edit_win.destroy).pack(side="right")
        
        # Center on parent
        edit_win.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - 400) // 2
        y = self.winfo_y() + (self.winfo_height() - 180) // 2
        edit_win.geometry(f"+{x}+{y}")
        edit_win.focus_force()
    
    def _delete_server(self):
        sel = self.lb.curselection()
        if not sel:
            return
        idx = sel[0]
        srv = self.servers[idx]
        if messagebox.askyesno("Confirm", f"Delete server '{srv['name']}'?", parent=self):
            del self.servers[idx]
            self._refresh_list()
    
    def _move_up(self):
        sel = self.lb.curselection()
        if not sel:
            return
        idx = sel[0]
        if idx > 0:
            self.servers[idx], self.servers[idx - 1] = self.servers[idx - 1], self.servers[idx]
            self._refresh_list()
            self.lb.selection_set(idx - 1)
    
    def _move_down(self):
        sel = self.lb.curselection()
        if not sel:
            return
        idx = sel[0]
        if idx < len(self.servers) - 1:
            self.servers[idx], self.servers[idx + 1] = self.servers[idx + 1], self.servers[idx]
            self._refresh_list()
            self.lb.selection_set(idx + 1)
    
    def _save_and_close(self):
        self.on_save(self.servers)
        self.destroy()
