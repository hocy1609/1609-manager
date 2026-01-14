import tkinter as tk

from ui.ui_base import COLORS, ModernButton


def build_settings_screen(app):
    """Embedded settings screen."""
    self = app

    settings_frame = tk.Frame(self.content_frame, bg=COLORS["bg_root"])
    self.screens["settings"] = settings_frame

    main = tk.Frame(settings_frame, bg=COLORS["bg_root"])
    main.pack(fill="both", expand=True, padx=40, pady=20)

    # Header
    tk.Label(
        main,
        text="Settings",
        font=("Segoe UI", 24, "bold"),
        bg=COLORS["bg_root"],
        fg=COLORS["fg_text"]
    ).pack(anchor="w", pady=(0, 20))

    # Settings vars (linked to main app vars)
    # Paths section
    paths_frame = tk.LabelFrame(main, text=" Paths ", bg=COLORS["bg_root"], fg=COLORS["fg_dim"], bd=1, relief="solid")
    paths_frame.pack(fill="x", pady=(0, 15))
    paths_inner = tk.Frame(paths_frame, bg=COLORS["bg_root"])
    paths_inner.pack(fill="x", padx=15, pady=10)

    # Documents path
    tk.Label(paths_inner, text="Documents Path:", bg=COLORS["bg_root"], fg=COLORS["fg_dim"]).grid(row=0, column=0, sticky="w", pady=2)
    doc_entry = tk.Entry(paths_inner, textvariable=self.doc_path_var, width=50, bg=COLORS["bg_input"], fg=COLORS["fg_text"], relief="flat")
    doc_entry.grid(row=0, column=1, sticky="w", padx=(10, 5), pady=2)
    ModernButton(paths_inner, COLORS["bg_input"], COLORS["border"], text="...", width=3, command=self._browse_doc_path).grid(row=0, column=2, pady=2)

    # Exe path
    tk.Label(paths_inner, text="Game Exe Path:", bg=COLORS["bg_root"], fg=COLORS["fg_dim"]).grid(row=1, column=0, sticky="w", pady=2)
    exe_entry = tk.Entry(paths_inner, textvariable=self.exe_path_var, width=50, bg=COLORS["bg_input"], fg=COLORS["fg_text"], relief="flat")
    exe_entry.grid(row=1, column=1, sticky="w", padx=(10, 5), pady=2)
    ModernButton(paths_inner, COLORS["bg_input"], COLORS["border"], text="...", width=3, command=self._browse_exe_path).grid(row=1, column=2, pady=2)

    # Two columns
    cols = tk.Frame(main, bg=COLORS["bg_root"])
    cols.pack(fill="x", pady=(0, 15))

    # Left - Coordinates
    left = tk.Frame(cols, bg=COLORS["bg_root"])
    left.pack(side="left", fill="both", expand=True, padx=(0, 10))

    coords_frame = tk.LabelFrame(left, text=" Exit Coordinates ", bg=COLORS["bg_root"], fg=COLORS["fg_dim"], bd=1, relief="solid")
    coords_frame.pack(fill="x")
    coords_inner = tk.Frame(coords_frame, bg=COLORS["bg_root"])
    coords_inner.pack(fill="x", padx=15, pady=10)

    self.settings_exit_x = tk.StringVar(value=str(self.exit_x))
    self.settings_exit_y = tk.StringVar(value=str(self.exit_y))
    self.settings_confirm_x = tk.StringVar(value=str(self.confirm_x))
    self.settings_confirm_y = tk.StringVar(value=str(self.confirm_y))

    tk.Label(coords_inner, text="Exit X:", bg=COLORS["bg_root"], fg=COLORS["fg_dim"]).grid(row=0, column=0, sticky="w")
    tk.Entry(coords_inner, textvariable=self.settings_exit_x, width=8, bg=COLORS["bg_input"], fg=COLORS["fg_text"], relief="flat").grid(row=0, column=1, padx=5)
    tk.Label(coords_inner, text="Y:", bg=COLORS["bg_root"], fg=COLORS["fg_dim"]).grid(row=0, column=2)
    tk.Entry(coords_inner, textvariable=self.settings_exit_y, width=8, bg=COLORS["bg_input"], fg=COLORS["fg_text"], relief="flat").grid(row=0, column=3, padx=5)

    tk.Label(coords_inner, text="Confirm X:", bg=COLORS["bg_root"], fg=COLORS["fg_dim"]).grid(row=1, column=0, sticky="w", pady=(5, 0))
    tk.Entry(coords_inner, textvariable=self.settings_confirm_x, width=8, bg=COLORS["bg_input"], fg=COLORS["fg_text"], relief="flat").grid(row=1, column=1, padx=5, pady=(5, 0))
    tk.Label(coords_inner, text="Y:", bg=COLORS["bg_root"], fg=COLORS["fg_dim"]).grid(row=1, column=2, pady=(5, 0))
    tk.Entry(coords_inner, textvariable=self.settings_confirm_y, width=8, bg=COLORS["bg_input"], fg=COLORS["fg_text"], relief="flat").grid(row=1, column=3, padx=5, pady=(5, 0))

    # Right - Automation
    right = tk.Frame(cols, bg=COLORS["bg_root"])
    right.pack(side="left", fill="both", expand=True)

    auto_frame = tk.LabelFrame(right, text=" Automation ", bg=COLORS["bg_root"], fg=COLORS["fg_dim"], bd=1, relief="solid")
    auto_frame.pack(fill="x")
    auto_inner = tk.Frame(auto_frame, bg=COLORS["bg_root"])
    auto_inner.pack(fill="x", padx=15, pady=10)

    self.settings_exit_speed = tk.StringVar(value=str(getattr(self, "exit_speed", 0.1)))
    self.settings_esc_count = tk.StringVar(value=str(getattr(self, "esc_count", 1)))

    tk.Label(auto_inner, text="Exit Speed:", bg=COLORS["bg_root"], fg=COLORS["fg_dim"]).grid(row=0, column=0, sticky="w")
    tk.Entry(auto_inner, textvariable=self.settings_exit_speed, width=8, bg=COLORS["bg_input"], fg=COLORS["fg_text"], relief="flat").grid(row=0, column=1, padx=5)

    tk.Label(auto_inner, text="ESC Count:", bg=COLORS["bg_root"], fg=COLORS["fg_dim"]).grid(row=1, column=0, sticky="w", pady=(5, 0))
    tk.Entry(auto_inner, textvariable=self.settings_esc_count, width=8, bg=COLORS["bg_input"], fg=COLORS["fg_text"], relief="flat").grid(row=1, column=1, padx=5, pady=(5, 0))

    # Data management
    data_frame = tk.LabelFrame(main, text=" Data Management ", bg=COLORS["bg_root"], fg=COLORS["fg_dim"], bd=1, relief="solid")
    data_frame.pack(fill="x", pady=(0, 15))
    data_inner = tk.Frame(data_frame, bg=COLORS["bg_root"])
    data_inner.pack(fill="x", padx=15, pady=10)

    ModernButton(data_inner, COLORS["bg_input"], COLORS["border"], text="Export Profiles", width=14, command=self.export_data).pack(side="left", padx=(0, 10))
    ModernButton(data_inner, COLORS["bg_input"], COLORS["border"], text="Import Profiles", width=14, command=self.import_data).pack(side="left", padx=(0, 10))
    ModernButton(data_inner, COLORS["success"], COLORS["success_hover"], text="Import xNwN.ini", width=14, command=self.import_xnwn_ini).pack(side="left", padx=(0, 10))
    ModernButton(data_inner, COLORS["accent"], COLORS["accent_hover"], text="Open Backups", width=14, command=self.open_restore_dialog).pack(side="left", padx=(0, 10))
    
    def _open_key_mgr():
        from ui.dialogs import KeyManagementDialog
        def on_save(keys):
            self.saved_keys[:] = keys
            self.save_data()
        try:
            keys = getattr(self, "saved_keys", [])
        except AttributeError:
            self.saved_keys = []
            keys = self.saved_keys
        KeyManagementDialog(self.root, keys, on_save)
        
    ModernButton(data_inner, COLORS["bg_panel"], COLORS["border"], text="Manage CD Keys", width=14, command=_open_key_mgr).pack(side="left")

    # Save button
    btn_frame = tk.Frame(main, bg=COLORS["bg_root"])
    btn_frame.pack(fill="x", pady=(10, 0))

    ModernButton(
        btn_frame,
        COLORS["success"],
        COLORS["success_hover"],
        text="💾 Save Settings",
        width=15,
        command=self._save_settings_from_screen
    ).pack(side="left")

    return settings_frame
