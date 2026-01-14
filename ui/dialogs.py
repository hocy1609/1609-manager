import os
import stat
import tkinter as tk

from tkinter import ttk, messagebox, filedialog

from ui.ui_base import BaseDialog, ModernButton, COLORS, ToggleSwitch, ToolTip
from utils.win_automation import safe_replace


class SettingsDialog(BaseDialog):
    def __init__(self, parent, settings, on_save, on_export, on_import, on_open_backup=None, on_change=None, on_import_xnwn=None, on_log_monitor=None):
        super().__init__(parent, "Settings", 500, 600)
        self.on_save = on_save
        self.on_export = on_export
        self.on_import = on_import
        self.on_open_backup = on_open_backup
        self.on_change = on_change
        self.on_import_xnwn = on_import_xnwn
        self.on_log_monitor = on_log_monitor

        content = tk.Frame(self, bg=COLORS["bg_root"])
        content.pack(fill="both", expand=True, padx=20, pady=20)

        self.vars = {
            "doc_path": tk.StringVar(value=settings.get("doc_path", "")),
            "exe_path": tk.StringVar(value=settings.get("exe_path", "")),
            "exit_x": tk.StringVar(
                value=str(settings.get("exit_coords_x", 1031))
            ),
            "exit_y": tk.StringVar(
                value=str(settings.get("exit_coords_y", 639))
            ),
            "confirm_x": tk.StringVar(
                value=str(settings.get("confirm_coords_x", 802))
            ),
            "confirm_y": tk.StringVar(
                value=str(settings.get("confirm_coords_y", 613))
            ),
            "exit_speed": tk.StringVar(value=str(settings.get("exit_speed", 0.4))),
            "esc_count": tk.StringVar(value=str(settings.get("esc_count", 6))),
            "clip_margin": tk.StringVar(value=str(settings.get("clip_margin", 48))),
            "theme": tk.StringVar(value=settings.get("theme", "dark")),
            "show_tooltips": tk.BooleanVar(value=settings.get("show_tooltips", True)),
        }

        self.create_path_field(
            content, "Documents Path:", self.vars["doc_path"], True
        )
        self.create_path_field(
            content, "Game Exe Path:", self.vars["exe_path"], False
        )

        coord_frame = tk.Frame(content, bg=COLORS["bg_root"])
        coord_frame.pack(fill="x", pady=10)

        self.create_coord_group(
            coord_frame,
            "Exit Button:",
            self.vars["exit_x"],
            self.vars["exit_y"],
            "left",
        )
        self.create_coord_group(
            coord_frame,
            "Confirm Button:",
            self.vars["confirm_x"],
            self.vars["confirm_y"],
            "right",
        )

        data_frame = tk.LabelFrame(
            content,
            text=" Data Management ",
            bg=COLORS["bg_root"],
            fg=COLORS["fg_dim"],
            bd=1,
            relief="solid",
        )
        data_frame.pack(fill="x", pady=15, ipady=5)

        btn_inner = tk.Frame(data_frame, bg=COLORS["bg_root"])
        btn_inner.pack(fill="x", padx=10, pady=5)

        ModernButton(
            btn_inner,
            COLORS["bg_input"],
            COLORS["border"],
            text="Export Profiles",
            command=lambda: self.on_export(self),
            width=14,
            tooltip="Сохранить профили в JSON",
        ).pack(side="left", padx=(0, 8))
        ModernButton(
            btn_inner,
            COLORS["bg_input"],
            COLORS["border"],
            text="Import Profiles",
            command=lambda: self.on_import(self),
            width=14,
            tooltip="Загрузить профили из JSON",
        ).pack(side="left", padx=(0, 8))
        ModernButton(
            btn_inner,
            COLORS["accent"],
            COLORS["accent_hover"],
            text="Open Backups",
            command=lambda: (self.destroy(), self._open_backup()),
            width=14,
            tooltip="Открыть окно восстановления/бэкапов",
        ).pack(side="left")

        # Extra tools row
        tools_inner = tk.Frame(data_frame, bg=COLORS["bg_root"])
        tools_inner.pack(fill="x", padx=10, pady=(5, 5))

        if self.on_import_xnwn:
            ModernButton(
                tools_inner,
                COLORS["success"],
                COLORS["success_hover"],
                text="Import xNwN.ini",
                command=lambda: (self.destroy(), self.on_import_xnwn()),
                width=14,
                tooltip="Импорт из xNwN.ini",
            ).pack(side="left", padx=(0, 8))

        btn_frame = tk.Frame(content, bg=COLORS["bg_root"])
        btn_frame.pack(fill="x", pady=10, side="bottom")
        # Help button
        ModernButton(
            btn_frame,
            COLORS["bg_panel"],
            COLORS["border"],
            text="Help",
            width=8,
            command=self.open_help,
            tooltip="Quick help about toggles and Clip Margin",
        ).pack(side="left")

        ModernButton(
            btn_frame,
            COLORS["success"],
            COLORS["success_hover"],
            text="Save",
            width=10,
            command=self.save_and_close,
        ).pack(side="right", padx=(10, 0))

        ModernButton(
            btn_frame,
            COLORS["bg_panel"],
            COLORS["border"],
            text="Cancel",
            width=10,
            command=self.destroy,
        ).pack(side="right")

        # --- Automation / Behavior settings ---
        auto_frame = tk.LabelFrame(
            content,
            text=" Automation ",
            bg=COLORS["bg_root"],
            fg=COLORS["fg_dim"],
            bd=1,
            relief="solid",
        )
        auto_frame.pack(fill="x", pady=10, ipady=5)

        af = tk.Frame(auto_frame, bg=COLORS["bg_root"])
        af.pack(fill="x", padx=10, pady=5)

        # Exit speed (multiplier)
        tk.Label(af, text="Exit Speed (multiplier):", bg=COLORS["bg_root"], fg=COLORS["fg_dim"]).grid(row=0, column=0, sticky="w")
        tk.Entry(af, textvariable=self.vars["exit_speed"], width=8, bg=COLORS["bg_input"], fg=COLORS["fg_text"], relief="flat").grid(row=0, column=1, padx=8, sticky="w")

        # ESC count
        tk.Label(af, text="ESC Count:", bg=COLORS["bg_root"], fg=COLORS["fg_dim"]).grid(row=0, column=2, sticky="w", padx=(20,0))
        tk.Entry(af, textvariable=self.vars["esc_count"], width=5, bg=COLORS["bg_input"], fg=COLORS["fg_text"], relief="flat").grid(row=0, column=3, sticky="w")

        # Clip margin
        tk.Label(af, text="Clip Margin (px):", bg=COLORS["bg_root"], fg=COLORS["fg_dim"]).grid(row=1, column=0, sticky="w", pady=(6,0))
        tk.Entry(af, textvariable=self.vars["clip_margin"], width=8, bg=COLORS["bg_input"], fg=COLORS["fg_text"], relief="flat").grid(row=1, column=1, padx=8, sticky="w", pady=(6,0))

        # Tooltips toggle (label + switch)
        tk.Label(af, text="Enable tooltips", bg=COLORS["bg_root"], fg=COLORS["fg_text"]).grid(row=1, column=2, sticky="w", padx=(20,4), pady=(6,0))
        ts_tooltips = ToggleSwitch(af, variable=self.vars["show_tooltips"])
        ts_tooltips.grid(row=1, column=3, sticky="w", pady=(6,0))

        # bind changes to live callback
        try:
            self.vars["show_tooltips"].trace_add("write", lambda *a: self._notify_change({"show_tooltips": self.vars["show_tooltips"].get()}))
        except Exception:
            try:
                self.vars["show_tooltips"].trace("w", lambda *a: self._notify_change({"show_tooltips": self.vars["show_tooltips"].get()}))
            except Exception:
                pass

        # Theme selector
        tk.Label(af, text="Theme:", bg=COLORS["bg_root"], fg=COLORS["fg_dim"]).grid(row=2, column=0, sticky="w", pady=(8,0))
        theme_cb = ttk.Combobox(af, textvariable=self.vars["theme"], values=["dark","purple","blue","light","mint","rose","bw"], width=12)
        theme_cb.grid(row=2, column=1, sticky="w", pady=(8,0))
        # Theme is applied on Save, not live

        # Live-update numeric fields too
        try:
            self.vars["exit_speed"].trace_add("write", lambda *a: self._notify_change({"exit_speed": self.vars["exit_speed"].get()}))
            self.vars["esc_count"].trace_add("write", lambda *a: self._notify_change({"esc_count": self.vars["esc_count"].get()}))
            self.vars["clip_margin"].trace_add("write", lambda *a: self._notify_change({"clip_margin": self.vars["clip_margin"].get()}))
        except Exception:
            try:
                self.vars["exit_speed"].trace("w", lambda *a: self._notify_change({"exit_speed": self.vars["exit_speed"].get()}))
                self.vars["esc_count"].trace("w", lambda *a: self._notify_change({"esc_count": self.vars["esc_count"].get()}))
                self.vars["clip_margin"].trace("w", lambda *a: self._notify_change({"clip_margin": self.vars["clip_margin"].get()}))
            except Exception:
                pass

        self.finalize_window(parent)

    def open_help(self):
        try:
            HelpDialog(self)
        except Exception:
            try:
                HelpDialog(self.master)
            except Exception:
                pass

    def _open_backup(self):
        try:
            if self.on_open_backup:
                self.on_open_backup()
        except Exception:
            pass

    def create_path_field(self, parent, label, var, is_dir: bool):
        tk.Label(
            parent,
            text=label,
            bg=COLORS["bg_root"],
            fg=COLORS["fg_dim"],
        ).pack(anchor="w")
        f = tk.Frame(parent, bg=COLORS["bg_root"])
        f.pack(fill="x", pady=(0, 10))

        e = tk.Entry(
            f,
            textvariable=var,
            bg=COLORS["bg_input"],
            fg=COLORS["fg_text"],
            relief="flat",
        )
        e.pack(side="left", fill="x", expand=True, ipady=3)

        cmd = (
            (lambda: self.browse_dir(var))
            if is_dir
            else (lambda: self.browse_file(var))
        )
        ModernButton(
            f,
            COLORS["bg_panel"],
            COLORS["border"],
            text="...",
            width=3,
            command=cmd,
        ).pack(side="right", padx=(5, 0))

    def create_coord_group(self, parent, title, var_x, var_y, side):
        f = tk.Frame(parent, bg=COLORS["bg_root"])
        f.pack(side=side, fill="x", expand=True, padx=5)

        tk.Label(
            f,
            text=title,
            bg=COLORS["bg_root"],
            fg=COLORS["accent"],
        ).pack(anchor="w")

        row = tk.Frame(f, bg=COLORS["bg_root"])
        row.pack(fill="x")

        tk.Label(
            row,
            text="X:",
            bg=COLORS["bg_root"],
            fg=COLORS["fg_text"],
        ).pack(side="left")
        tk.Entry(
            row,
            textvariable=var_x,
            width=5,
            bg=COLORS["bg_input"],
            fg=COLORS["fg_text"],
            relief="flat",
        ).pack(side="left", padx=5)

        tk.Label(
            row,
            text="Y:",
            bg=COLORS["bg_root"],
            fg=COLORS["fg_text"],
        ).pack(side="left")
        tk.Entry(
            row,
            textvariable=var_y,
            width=5,
            bg=COLORS["bg_input"],
            fg=COLORS["fg_text"],
            relief="flat",
        ).pack(side="left", padx=5)

    def browse_dir(self, var):
        d = filedialog.askdirectory()
        if d:
            var.set(d)

    def browse_file(self, var):
        f = filedialog.askopenfilename(filetypes=[("EXE", "*.exe")])
        if f:
            var.set(f)

    def save_and_close(self):
        try:
            res = {
                "doc_path": self.vars["doc_path"].get(),
                "exe_path": self.vars["exe_path"].get(),
                "exit_x": int(self.vars["exit_x"].get()),
                "exit_y": int(self.vars["exit_y"].get()),
                "confirm_x": int(self.vars["confirm_x"].get()),
                "confirm_y": int(self.vars["confirm_y"].get()),
            }
            # Optional automation settings
            try:
                res["exit_speed"] = float(self.vars["exit_speed"].get())
            except Exception:
                res["exit_speed"] = 0.4
            try:
                res["esc_count"] = int(self.vars["esc_count"].get())
            except Exception:
                res["esc_count"] = 6
            try:
                res["clip_margin"] = int(self.vars["clip_margin"].get())
            except Exception:
                res["clip_margin"] = 48
            res["show_tooltips"] = bool(self.vars["show_tooltips"].get())
            res["theme"] = self.vars["theme"].get()
            self.on_save(res)
            self.destroy()
        except ValueError:
            messagebox.showerror(
                "Error", "Coordinates must be integers!", parent=self
            )

    def _notify_change(self, delta: dict):
        """Notify parent/app about a live change (called on var traces)."""
        if not self.on_change:
            return
        try:
            # convert simple string numeric values to appropriate types where possible
            for k, v in list(delta.items()):
                if k in ("exit_speed",):
                    try:
                        delta[k] = float(v)
                    except Exception:
                        continue
                elif k in ("esc_count", "clip_margin"):
                    try:
                        delta[k] = int(v)
                    except Exception:
                        continue
            self.on_change(delta)
        except Exception:
            pass


class HelpDialog(BaseDialog):
    """Simple help dialog with concise explanations for toggles and Clip Margin."""

    def __init__(self, parent):
        super().__init__(parent, "Settings Help", 520, 280)
        content = tk.Frame(self, bg=COLORS["bg_root"])
        content.pack(fill="both", expand=True, padx=16, pady=16)

        lines = [
            ("Show tooltips:", "Toggle on to show small helper text when hovering action buttons; toggle off to reduce visual noise. Recommended: On for new users, Off for power users."),
            ("Clip Margin (px):", "When mouse-clipping fallback is used during automated Safe Exit, `clip_margin` expands the rectangle kept under control around the target coordinates. Larger margins tolerate small cursor movement; smaller margins are more precise. Recommended: 32–64 px (48 default)."),
            ("Exit Speed / ESC Count:", "Adjust how quickly the automated Safe Exit sequence sends ESCs and confirms; increase ESC Count if logout dialog is slow to appear.")
        ]

        for title, text in lines:
            tk.Label(content, text=title, bg=COLORS["bg_root"], fg=COLORS["fg_dim"], font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(8, 0))
            tk.Label(content, text=text, bg=COLORS["bg_root"], fg=COLORS["fg_text"], wraplength=480, justify="left").pack(anchor="w")

        btn = tk.Button(content, text="Close", command=self.destroy, bg=COLORS["bg_panel"], fg=COLORS["fg_text"], relief="flat", cursor="hand2")
        btn.pack(side="bottom", pady=12)
        
        # Center window without grab_set to avoid freezing parent
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = (sw - 520) // 2
        y = (sh - 280) // 2
        self.geometry(f"520x280+{x}+{y}")
        self.lift()
        self.focus_force()


class EditDialog(BaseDialog):
    def __init__(self, parent, profile_data=None, existing_categories=None, on_save=None, *, title=None, categories=None, server_list=None, is_new=False, saved_keys=None):
        # Support both calling conventions
        cats = categories or existing_categories or ["General"]
        profile = profile_data if profile_data else {}
        dialog_title = title or ("Add Profile" if is_new else "Edit Profile")
        super().__init__(parent, dialog_title, 500, 560)
        self.on_save = on_save
        self.saved_keys = saved_keys or []

        self.name_var = tk.StringVar(value=profile.get("name", ""))
        self.cat_var = tk.StringVar(
            value=profile.get("category", "General")
        )
        self.key_var = tk.StringVar(value=profile.get("cdKey", ""))
        self.player_var = tk.StringVar(
            value=profile.get("playerName", "")
        )
        self.args_var = tk.StringVar(
            value=profile.get("launchArgs", "")
        )

        padding = 30
        content = tk.Frame(self, bg=COLORS["bg_root"])
        content.pack(fill="both", expand=True, padx=5, pady=5)

        self.create_field(content, "Profile Name:", self.name_var, padding)

        tk.Label(
            content,
            text="Category:",
            bg=COLORS["bg_root"],
            fg=COLORS["fg_dim"],
            font=("Segoe UI", 10),
        ).pack(anchor="w", padx=padding, pady=(5, 2))

        cat_cb = ttk.Combobox(
            content,
            textvariable=self.cat_var,
            values=cats,
            font=("Segoe UI", 11),
        )
        cat_cb.pack(fill="x", padx=padding, ipady=4)

        # CD Key section with saved keys dropdown
        key_frame = tk.Frame(content, bg=COLORS["bg_root"])
        key_frame.pack(fill="x", padx=padding, pady=(10, 0))
        
        tk.Label(
            key_frame,
            text="CD Key:",
            bg=COLORS["bg_root"],
            fg=COLORS["fg_dim"],
            font=("Segoe UI", 10),
        ).pack(anchor="w")
        
        # Saved keys dropdown
        if self.saved_keys:
            key_select_frame = tk.Frame(content, bg=COLORS["bg_root"])
            key_select_frame.pack(fill="x", padx=padding, pady=(2, 5))
            
            tk.Label(
                key_select_frame,
                text="Use saved:",
                bg=COLORS["bg_root"],
                fg=COLORS["fg_dim"],
                font=("Segoe UI", 9),
            ).pack(side="left")
            
            key_names = [""] + [k.get("name", "Key") for k in self.saved_keys]
            self.key_select_var = tk.StringVar(value="")
            
            def on_key_select(event=None):
                selected = self.key_select_var.get()
                for k in self.saved_keys:
                    if k.get("name") == selected:
                        self.key_var.set(k.get("key", ""))
                        break
            
            key_combo = ttk.Combobox(
                key_select_frame,
                textvariable=self.key_select_var,
                values=key_names,
                font=("Segoe UI", 9),
                width=20,
            )
            key_combo.pack(side="left", padx=(5, 0))
            key_combo.bind("<<ComboboxSelected>>", on_key_select)
        
        # CD Key entry field
        self.key_entry = self.create_field(
            content, "", self.key_var, padding
        )
        # Small inline hint and tooltip for expected format
        try:
            hint = tk.Label(
                content,
                text="Format: XXXXX-XXXXX-XXXXX-XXXXX-XXXXX-XXXXX-XXXXX",
                bg=COLORS["bg_root"],
                fg=COLORS["fg_dim"],
                font=("Segoe UI", 8),
            )
            hint.pack(anchor="w", padx=padding, pady=(2, 6))
            ToolTip(self.key_entry, "CD Key should be 7 groups of 5 letters/numbers separated by hyphens. Example: YUJXF-TL4V7-...")
        except Exception:
            pass
        self.create_field(
            content,
            "Login Name (settings.tml):",
            self.player_var,
            padding,
        )
        self.create_field(
            content, "Launch Arguments:", self.args_var, padding
        )

        btn_frame = tk.Frame(self, bg=COLORS["bg_root"])
        btn_frame.pack(
            fill="x", padx=padding, pady=30, side="bottom"
        )

        ModernButton(
            btn_frame,
            COLORS["success"],
            COLORS["success_hover"],
            text="Save",
            font=("Segoe UI", 11, "bold"),
            command=self.save_and_close,
        ).pack(side="right", ipadx=15, ipady=5)

        ModernButton(
            btn_frame,
            COLORS["bg_panel"],
            COLORS["border"],
            text="Cancel",
            font=("Segoe UI", 11),
            fg=COLORS["fg_text"],
            command=self.destroy,
        ).pack(side="right", padx=10, ipadx=10, ipady=5)

        self.finalize_window(parent)

    def create_field(self, parent, label, var, padding):
        tk.Label(
            parent,
            text=label,
            bg=COLORS["bg_root"],
            fg=COLORS["fg_dim"],
            font=("Segoe UI", 10),
        ).pack(anchor="w", padx=padding, pady=(5, 2))

        entry = tk.Entry(
            parent,
            textvariable=var,
            bg=COLORS["bg_input"],
            fg=COLORS["fg_text"],
            relief="flat",
            insertbackground="white",
            font=("Segoe UI", 11),
        )
        entry.configure(
            highlightthickness=1,
            highlightbackground=COLORS["border"],
            highlightcolor=COLORS["accent"],
        )
        entry.pack(fill="x", padx=padding, ipady=6)
        return entry

    def save_and_close(self):
        cat = self.cat_var.get().strip()
        if not cat:
            cat = "General"

        new_data = {
            "name": self.name_var.get(),
            "category": cat,
            "cdKey": self.key_var.get(),
            "playerName": self.player_var.get(),
            "launchArgs": self.args_var.get(),
        }
        # Validate CD Key format: expect 7 groups of 5 alphanumeric characters separated by '-'
        try:
            raw = (self.key_var.get() or "").strip()
            key = raw.upper()
            import re

            pattern = re.compile(r'^[A-Z0-9]{5}(?:-[A-Z0-9]{5}){6}$')
            if raw and not pattern.match(key):
                messagebox.showerror(
                    "Invalid CD Key",
                    "CD Key must be in format: XXXXX-XXXXX-XXXXX-XXXXX-XXXXX-XXXXX-XXXXX\nPlease check the key and try again.",
                    parent=self,
                )
                return
            new_data["cdKey"] = key
        except Exception:
            # On any unexpected error, fall back to original value
            new_data["cdKey"] = self.key_var.get()

        self.on_save(new_data)
        self.destroy()


class CustomInputDialog(BaseDialog):
    def __init__(self, parent, title, prompt, initial_value=""):
        super().__init__(parent, title, 400, 200)
        self.result = None

        tk.Label(
            self,
            text=prompt,
            bg=COLORS["bg_root"],
            fg=COLORS["fg_text"],
            font=("Segoe UI", 11),
        ).pack(pady=(20, 10), padx=20, anchor="w")

        self.entry = tk.Entry(
            self,
            bg=COLORS["bg_input"],
            fg=COLORS["fg_text"],
            relief="flat",
            font=("Segoe UI", 11),
            insertbackground="white",
        )
        self.entry.configure(
            highlightthickness=1,
            highlightbackground=COLORS["border"],
            highlightcolor=COLORS["accent"],
        )
        self.entry.pack(fill="x", padx=20, ipady=6)
        self.entry.insert(0, initial_value)

        btn_frame = tk.Frame(self, bg=COLORS["bg_root"])
        btn_frame.pack(fill="x", pady=20, padx=20, side="bottom")

        ModernButton(
            btn_frame,
            COLORS["success"],
            COLORS["success_hover"],
            text="OK",
            width=10,
            command=self.on_ok,
        ).pack(side="right", padx=(10, 0))

        ModernButton(
            btn_frame,
            COLORS["bg_panel"],
            COLORS["border"],
            text="Cancel",
            width=10,
            command=self.destroy,
        ).pack(side="right")

        self.bind("<Return>", lambda e: self.on_ok())
        self.bind("<Escape>", lambda e: self.destroy())

        self.entry.focus_set()
        self.finalize_window(parent)

    def on_ok(self):
        val = self.entry.get().strip()
        if val:
            self.result = val
        self.destroy()


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


class RestoreBackupDialog(BaseDialog):
    def __init__(self, parent, backup_dir, doc_path, on_export=None, on_import=None):
        super().__init__(parent, "Restore Backup", 450, 400)
        self.backup_dir = backup_dir
        self.doc_path = doc_path

        content = tk.Frame(self, bg=COLORS["bg_root"])
        content.pack(fill="both", expand=True, padx=20, pady=10)

        tk.Label(
            content,
            text="Select a backup file to restore:",
            bg=COLORS["bg_root"],
            fg=COLORS["fg_dim"],
        ).pack(anchor="w")

        self.lb = tk.Listbox(
            content,
            bg=COLORS["bg_input"],
            fg=COLORS["fg_text"],
            bd=0,
            highlightthickness=1,
            highlightbackground=COLORS["border"],
        )
        self.lb.pack(fill="both", expand=True, pady=10)

        self.files: list[str] = []
        if os.path.exists(backup_dir):
            try:
                all_files = [
                    f
                    for f in os.listdir(backup_dir)
                    if f.endswith(".bak")
                ]
                all_files.sort(
                    key=lambda x: os.path.getmtime(
                        os.path.join(backup_dir, x)
                    ),
                    reverse=True,
                )
                self.files = all_files
                for f in self.files:
                    self.lb.insert(tk.END, f)
            except Exception as e:
                print(f"Error listing backups: {e}")

        # Import/Export integration row
        ie_frame = tk.LabelFrame(
            content,
            text=" Import / Export Profiles ",
            bg=COLORS["bg_root"],
            fg=COLORS["fg_dim"],
            bd=1,
            relief="solid",
        )
        ie_frame.pack(fill="x", pady=(0,10))
        ie_inner = tk.Frame(ie_frame, bg=COLORS["bg_root"])
        ie_inner.pack(fill="x", padx=8, pady=6)
        ModernButton(
            ie_inner,
            COLORS["bg_input"],
            COLORS["border"],
            text="Export",
            width=10,
            command=lambda: on_export(self) if on_export else None,
            tooltip="Экспортировать профили в JSON",
        ).pack(side="left", padx=(0,6))
        ModernButton(
            ie_inner,
            COLORS["bg_input"],
            COLORS["border"],
            text="Import",
            width=10,
            command=lambda: on_import(self) if on_import else None,
            tooltip="Импортировать профили из JSON",
        ).pack(side="left")

        btn_frame = tk.Frame(content, bg=COLORS["bg_root"])
        btn_frame.pack(fill="x", pady=4, side="bottom")
        ModernButton(
            btn_frame,
            COLORS["warning"],
            COLORS["warning_hover"],
            text="Restore",
            width=10,
            command=self.restore,
        ).pack(side="right", padx=(10, 0))
        ModernButton(
            btn_frame,
            COLORS["bg_panel"],
            COLORS["border"],
            text="Close",
            width=10,
            command=self.destroy,
        ).pack(side="right")

        self.finalize_window(parent)

    def restore(self):
        idx = self.lb.curselection()
        if not idx:
            return

        filename = self.files[idx[0]]
        src = os.path.join(self.backup_dir, filename)

        original_name = ""
        if filename.startswith("nwncdkey"):
            original_name = "nwncdkey.ini"
        elif filename.startswith("settings"):
            original_name = "settings.tml"

        if not original_name:
            messagebox.showerror(
                "Error", "Unknown backup file type.", parent=self
            )
            return

        dst = os.path.join(self.doc_path, original_name)
        if messagebox.askyesno(
            "Confirm Restore",
            f"Restore {original_name} from backup?\nCurrent settings will be overwritten.",
            parent=self,
        ):
            try:
                if os.path.exists(dst):
                    os.chmod(dst, stat.S_IWRITE)
                safe_replace(src, dst)
                messagebox.showinfo(
                    "Success",
                    "File restored successfully!",
                    parent=self,
                )
                self.destroy()
            except Exception as e:
                messagebox.showerror("Error", str(e), parent=self)


class LogMonitorDialog(BaseDialog):
    def __init__(self, parent, config: dict, on_save_config, on_start, on_stop, is_running: bool):
        super().__init__(parent, "Log Monitor", 600, 450)
        self.on_save_config = on_save_config
        self.on_start = on_start
        self.on_stop = on_stop

        # Keep the enabled state from the main app but do not duplicate
        # the 'Enable' control here — monitoring is controlled from
        # the main sidebar checkbox. Store initial enabled value so
        # saving preserves it when the dialog does not change it.
        self.initial_enabled = bool(config.get("enabled", False))
        self.log_path_var = tk.StringVar(value=config.get("log_path", ""))
        self.webhooks = list(config.get("webhooks", []))
        self.keywords = list(config.get("keywords", []))

        content = tk.Frame(self, bg=COLORS["bg_root"])
        content.pack(fill="both", expand=True, padx=20, pady=15)

        tk.Label(
            content,
            text="Log file path (nwclientLog1.txt):",
            bg=COLORS["bg_root"],
            fg=COLORS["fg_dim"],
        ).pack(anchor="w")

        path_row = tk.Frame(content, bg=COLORS["bg_root"])
        path_row.pack(fill="x", pady=(0, 8))

        tk.Entry(
            path_row,
            textvariable=self.log_path_var,
            bg=COLORS["bg_input"],
            fg=COLORS["fg_text"],
            relief="flat",
        ).pack(side="left", fill="x", expand=True, ipady=3)

        ModernButton(
            path_row,
            COLORS["bg_panel"],
            COLORS["border"],
            text="...",
            width=3,
            command=self.browse_log,
        ).pack(side="right", padx=(5, 0))

        # Note: the enable checkbox intentionally omitted here to avoid
        # duplication with the main UI control.

        lists_frame = tk.Frame(content, bg=COLORS["bg_root"])
        lists_frame.pack(fill="both", expand=True)

        self.webhook_list = self._create_list_section(
            lists_frame,
            "Discord Webhooks:",
            self.webhooks,
            side="left",
        )
        self.keyword_list = self._create_list_section(
            lists_frame,
            "Keywords (one per line):",
            self.keywords,
            side="right",
        )

        btn_frame = tk.Frame(self, bg=COLORS["bg_root"])
        btn_frame.pack(fill="x", padx=20, pady=10, side="bottom")

        # Start/Stop monitor controls removed — monitoring is controlled from the main app

        ModernButton(
            btn_frame,
            COLORS["bg_panel"],
            COLORS["border"],
            text="Cancel",
            width=10,
            command=self.destroy,
        ).pack(side="right")

        ModernButton(
            btn_frame,
            COLORS["success"],
            COLORS["success_hover"],
            text="Save",
            width=10,
            command=self.save_and_close,
        ).pack(side="right", padx=(10, 0))

        self.finalize_window(parent)

    def _create_list_section(self, parent, title, items, side):
        frame = tk.Frame(parent, bg=COLORS["bg_root"])
        frame.pack(side=side, fill="both", expand=True, padx=5)

        tk.Label(
            frame,
            text=title,
            bg=COLORS["bg_root"],
            fg=COLORS["fg_dim"],
        ).pack(anchor="w")

        listbox = tk.Listbox(
            frame,
            bg=COLORS["bg_input"],
            fg=COLORS["fg_text"],
            bd=0,
            highlightthickness=1,
            highlightbackground=COLORS["border"],
        )
        listbox.pack(fill="both", expand=True, pady=(0, 5))

        for item in items:
            listbox.insert(tk.END, item)

        entry_row = tk.Frame(frame, bg=COLORS["bg_root"])
        entry_row.pack(fill="x", pady=(0, 5))

        entry = tk.Entry(
            entry_row,
            bg=COLORS["bg_input"],
            fg=COLORS["fg_text"],
            relief="flat",
        )
        entry.pack(side="left", fill="x", expand=True, ipady=3)

        def add_item():
            val = entry.get().strip()
            if val:
                items.append(val)
                listbox.insert(tk.END, val)
                entry.delete(0, tk.END)

        def remove_selected():
            sel = listbox.curselection()
            if not sel:
                return
            idx = sel[0]
            listbox.delete(idx)
            del items[idx]

        def edit_selected():
            sel = listbox.curselection()
            if not sel:
                return
            idx = sel[0]
            current = items[idx]
            entry.delete(0, tk.END)
            entry.insert(0, current)
            listbox.delete(idx)
            del items[idx]

        ModernButton(
            entry_row,
            COLORS["bg_panel"],
            COLORS["border"],
            text="Add",
            width=6,
            command=add_item,
        ).pack(side="right", padx=(5, 0))

        # Delete / Edit buttons row
        btn_row = tk.Frame(frame, bg=COLORS["bg_root"])
        btn_row.pack(fill="x")

        ModernButton(
            btn_row,
            COLORS["danger"],
            COLORS["danger_hover"],
            text="Delete",
            width=8,
            command=remove_selected,
        ).pack(side="left", padx=(0, 3))

        ModernButton(
            btn_row,
            COLORS["bg_panel"],
            COLORS["border"],
            text="Edit",
            width=8,
            command=edit_selected,
        ).pack(side="left")

        # Right-click context menu for delete/edit
        def show_context_menu(event):
            menu = tk.Menu(listbox, tearoff=False, bg=COLORS["bg_panel"], fg=COLORS["fg_text"])
            menu.add_command(label="Delete", command=remove_selected)
            menu.add_command(label="Edit", command=edit_selected)
            try:
                menu.tk_popup(event.x_root, event.y_root)
            finally:
                menu.grab_release()

        listbox.bind("<Button-3>", show_context_menu)

        return listbox

    def browse_log(self):
        f = filedialog.askopenfilename(
            title="Select Neverwinter Nights log file",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if f:
            self.log_path_var.set(f)

    def _collect_config(self) -> dict:
        # Return config; preserve enabled state coming from main app
        # (dialog doesn't provide an enable switch to avoid duplication).
        return {
            "enabled": self.initial_enabled,
            "log_path": self.log_path_var.get().strip(),
            "webhooks": list(self.webhooks),
            "keywords": list(self.keywords),
        }

    def save_and_close(self):
        cfg = self._collect_config()
        self.on_save_config(cfg)
        self.destroy()

    def start_clicked(self):
        cfg = self._collect_config()
        self.on_save_config(cfg)
        self.on_start()

    def stop_clicked(self):
        self.on_stop()


# CraftDialog removed - functionality moved to integrated craft screen in app.py

class AddKeyDialog(BaseDialog):
    def __init__(self, parent, on_save):
        super().__init__(parent, "Add CD Key", 400, 250)
        self.on_save = on_save

        content = tk.Frame(self, bg=COLORS["bg_root"])
        content.pack(fill="both", expand=True, padx=20, pady=20)

        self.name_var = tk.StringVar()
        self.key_var = tk.StringVar()

        tk.Label(
            content,
            text="Key Name (e.g. My Key 1):",
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
            text="CD Key:",
            bg=COLORS["bg_root"],
            fg=COLORS["fg_dim"],
        ).pack(anchor="w")
        entry = tk.Entry(
            content,
            textvariable=self.key_var,
            bg=COLORS["bg_input"],
            fg=COLORS["fg_text"],
            relief="flat",
        )
        entry.pack(fill="x", pady=(0, 10), ipady=3)
        
        # Tooltip for format
        hint = tk.Label(
            content,
            text="Format: XXXXX-XXXXX-...",
            bg=COLORS["bg_root"],
            fg=COLORS["fg_dim"],
            font=("Segoe UI", 8),
        )
        hint.pack(anchor="w", pady=(0, 10))


        btn_frame = tk.Frame(content, bg=COLORS["bg_root"])
        btn_frame.pack(fill="x", pady=10, side="bottom")

        def save():
            name = self.name_var.get().strip()
            key = self.key_var.get().strip().upper()
            if name and key:
                self.on_save({"name": name, "key": key})
                self.destroy()
            else:
                messagebox.showwarning("Error", "All fields required", parent=self)

        ModernButton(
            btn_frame,
            COLORS["success"],
            COLORS["success_hover"],
            text="Add",
            width=10,
            command=save,
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


class KeyManagementDialog(BaseDialog):
    def __init__(self, parent, keys: list, on_save):
        super().__init__(parent, "Manage CD Keys", 500, 400)
        self.keys = [dict(k) for k in keys]  # Copy
        self.on_save = on_save
        
        content = tk.Frame(self, bg=COLORS["bg_root"])
        content.pack(fill="both", expand=True, padx=20, pady=20)
        
        tk.Label(
            content,
            text="Saved CD Keys:",
            bg=COLORS["bg_root"],
            fg=COLORS["fg_dim"],
            font=("Segoe UI", 10),
        ).pack(anchor="w")
        
        # Key listbox
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
            text="Add Key",
            width=10,
            command=self._add_key,
        ).pack(side="left", padx=(0, 5))
        
        ModernButton(
            btn_frame,
            COLORS["danger"],
            COLORS["danger_hover"],
            text="Delete",
            width=8,
            command=self._delete_key,
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
        for k in self.keys:
            self.lb.insert(tk.END, f"{k['name']} ({k['key'][:5]}...)")
    
    def _add_key(self):
        def on_add(data):
            self.keys.append(data)
            self._refresh_list()
        AddKeyDialog(self, on_add)
    
    def _delete_key(self):
        sel = self.lb.curselection()
        if not sel:
            return
        idx = sel[0]
        key = self.keys[idx]
        if messagebox.askyesno("Confirm", f"Delete key '{key['name']}'?", parent=self):
            del self.keys[idx]
            self._refresh_list()
    
    def _save_and_close(self):
        self.on_save(self.keys)
        self.destroy()