import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from ui.ui_base import BaseDialog, ModernButton, COLORS, ToggleSwitch
from .help_dialog import HelpDialog

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
