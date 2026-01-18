import tkinter as tk
from tkinter import ttk

from ui.ui_base import COLORS, ModernButton, ToggleSwitch


def build_settings_screen(app):
    """Embedded settings screen with auto-save."""
    self = app

    settings_frame = tk.Frame(self.content_frame, bg=COLORS["bg_root"])
    self.screens["settings"] = settings_frame

    # Create scrollable canvas (no visible scrollbar, just mouse wheel)
    canvas = tk.Canvas(settings_frame, bg=COLORS["bg_root"], highlightthickness=0)
    
    main = tk.Frame(canvas, bg=COLORS["bg_root"])
    
    # Configure scrolling
    def on_frame_configure(event):
        canvas.configure(scrollregion=canvas.bbox("all"))
    
    main.bind("<Configure>", on_frame_configure)
    
    # Create window in canvas
    canvas_window = canvas.create_window((0, 0), window=main, anchor="nw")
    
    def on_canvas_configure(event):
        canvas.itemconfig(canvas_window, width=event.width)
    
    canvas.bind("<Configure>", on_canvas_configure)
    
    # Mouse wheel scrolling
    def on_mousewheel(event):
        canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    
    def bind_mousewheel(widget):
        widget.bind("<MouseWheel>", on_mousewheel)
        for child in widget.winfo_children():
            bind_mousewheel(child)
    
    canvas.bind("<MouseWheel>", on_mousewheel)
    main.bind("<MouseWheel>", on_mousewheel)
    
    # Pack canvas only (no scrollbar)
    canvas.pack(fill="both", expand=True)
    
    # Main content padding
    content = tk.Frame(main, bg=COLORS["bg_root"])
    content.pack(fill="both", expand=True, padx=30, pady=15)

    # Header
    tk.Label(
        content,
        text="Settings",
        font=("Segoe UI", 22, "bold"),
        bg=COLORS["bg_root"],
        fg=COLORS["fg_text"]
    ).pack(anchor="w", pady=(0, 15))

    # Auto-save function with debounce
    _save_job = [None]
    
    def auto_save(*args):
        """Save settings with debounce."""
        if _save_job[0]:
            self.root.after_cancel(_save_job[0])
        _save_job[0] = self.root.after(500, _do_save)
    
    def _do_save():
        """Actually save the settings."""
        try:
            self.exit_x = int(self.settings_exit_x.get())
            self.exit_y = int(self.settings_exit_y.get())
            self.confirm_x = int(self.settings_confirm_x.get())
            self.confirm_y = int(self.settings_confirm_y.get())
            self.exit_speed = float(self.settings_exit_speed.get())
            self.esc_count = int(self.settings_esc_count.get())
            self.clip_margin = int(self.settings_clip_margin.get())
            
            # UI Settings
            new_theme = self.settings_theme.get()
            theme_changed = (new_theme != self.theme)
            self.theme = new_theme
            
            # Apply theme if changed
            if theme_changed:
                try:
                    import ui.ui_base as _uib
                    _uib.set_theme(self.theme, root=self.root)
                except Exception as e:
                    self.log_error("SettingsScreen._do_save.set_theme", e)
            
            self.save_data()
            
            # Rebuild UI if theme changed
            if theme_changed:
                try:
                    self._rebuild_current_screen()
                except Exception as e:
                    self.log_error("SettingsScreen._do_save.rebuild_ui", e)
        except (ValueError, AttributeError):
            pass  # Invalid input, don't save

    # Paths section
    paths_frame = tk.LabelFrame(content, text=" Paths ", bg=COLORS["bg_root"], fg=COLORS["fg_dim"], bd=1, relief="solid")
    paths_frame.pack(fill="x", pady=(0, 10))
    paths_inner = tk.Frame(paths_frame, bg=COLORS["bg_root"])
    paths_inner.pack(fill="x", padx=12, pady=8)

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
    
    # Auto-save paths
    self.doc_path_var.trace_add("write", auto_save)
    self.exe_path_var.trace_add("write", auto_save)

    # Two columns for Coordinates and Automation
    cols = tk.Frame(content, bg=COLORS["bg_root"])
    cols.pack(fill="x", pady=(0, 10))

    # Left - Coordinates
    left = tk.Frame(cols, bg=COLORS["bg_root"])
    left.pack(side="left", fill="both", expand=True, padx=(0, 8))

    coords_frame = tk.LabelFrame(left, text=" Exit Coordinates ", bg=COLORS["bg_root"], fg=COLORS["fg_dim"], bd=1, relief="solid")
    coords_frame.pack(fill="x")
    coords_inner = tk.Frame(coords_frame, bg=COLORS["bg_root"])
    coords_inner.pack(fill="x", padx=12, pady=8)

    self.settings_exit_x = tk.StringVar(value=str(self.exit_x))
    self.settings_exit_y = tk.StringVar(value=str(self.exit_y))
    self.settings_confirm_x = tk.StringVar(value=str(self.confirm_x))
    self.settings_confirm_y = tk.StringVar(value=str(self.confirm_y))

    tk.Label(coords_inner, text="Exit X:", bg=COLORS["bg_root"], fg=COLORS["fg_dim"]).grid(row=0, column=0, sticky="w")
    tk.Entry(coords_inner, textvariable=self.settings_exit_x, width=8, bg=COLORS["bg_input"], fg=COLORS["fg_text"], relief="flat").grid(row=0, column=1, padx=5)
    tk.Label(coords_inner, text="Y:", bg=COLORS["bg_root"], fg=COLORS["fg_dim"]).grid(row=0, column=2)
    tk.Entry(coords_inner, textvariable=self.settings_exit_y, width=8, bg=COLORS["bg_input"], fg=COLORS["fg_text"], relief="flat").grid(row=0, column=3, padx=5)

    tk.Label(coords_inner, text="Confirm X:", bg=COLORS["bg_root"], fg=COLORS["fg_dim"]).grid(row=1, column=0, sticky="w", pady=(4, 0))
    tk.Entry(coords_inner, textvariable=self.settings_confirm_x, width=8, bg=COLORS["bg_input"], fg=COLORS["fg_text"], relief="flat").grid(row=1, column=1, padx=5, pady=(4, 0))
    tk.Label(coords_inner, text="Y:", bg=COLORS["bg_root"], fg=COLORS["fg_dim"]).grid(row=1, column=2, pady=(4, 0))
    tk.Entry(coords_inner, textvariable=self.settings_confirm_y, width=8, bg=COLORS["bg_input"], fg=COLORS["fg_text"], relief="flat").grid(row=1, column=3, padx=5, pady=(4, 0))

    # Auto-save coordinates
    self.settings_exit_x.trace_add("write", auto_save)
    self.settings_exit_y.trace_add("write", auto_save)
    self.settings_confirm_x.trace_add("write", auto_save)
    self.settings_confirm_y.trace_add("write", auto_save)

    # Right - Automation
    right = tk.Frame(cols, bg=COLORS["bg_root"])
    right.pack(side="left", fill="both", expand=True)

    auto_frame = tk.LabelFrame(right, text=" Automation ", bg=COLORS["bg_root"], fg=COLORS["fg_dim"], bd=1, relief="solid")
    auto_frame.pack(fill="x")
    auto_inner = tk.Frame(auto_frame, bg=COLORS["bg_root"])
    auto_inner.pack(fill="x", padx=12, pady=8)

    self.settings_exit_speed = tk.StringVar(value=str(getattr(self, "exit_speed", 0.1)))
    self.settings_esc_count = tk.StringVar(value=str(getattr(self, "esc_count", 1)))
    self.settings_clip_margin = tk.StringVar(value=str(getattr(self, "clip_margin", 48)))

    tk.Label(auto_inner, text="Exit Speed:", bg=COLORS["bg_root"], fg=COLORS["fg_dim"]).grid(row=0, column=0, sticky="w")
    tk.Entry(auto_inner, textvariable=self.settings_exit_speed, width=8, bg=COLORS["bg_input"], fg=COLORS["fg_text"], relief="flat").grid(row=0, column=1, padx=5)

    tk.Label(auto_inner, text="ESC Count:", bg=COLORS["bg_root"], fg=COLORS["fg_dim"]).grid(row=1, column=0, sticky="w", pady=(4, 0))
    tk.Entry(auto_inner, textvariable=self.settings_esc_count, width=8, bg=COLORS["bg_input"], fg=COLORS["fg_text"], relief="flat").grid(row=1, column=1, padx=5, pady=(4, 0))

    tk.Label(auto_inner, text="Clip Margin:", bg=COLORS["bg_root"], fg=COLORS["fg_dim"]).grid(row=2, column=0, sticky="w", pady=(4, 0))
    tk.Entry(auto_inner, textvariable=self.settings_clip_margin, width=8, bg=COLORS["bg_input"], fg=COLORS["fg_text"], relief="flat").grid(row=2, column=1, padx=5, pady=(4, 0))

    # Auto-save automation
    self.settings_exit_speed.trace_add("write", auto_save)
    self.settings_esc_count.trace_add("write", auto_save)
    self.settings_clip_margin.trace_add("write", auto_save)

    # UI Settings section (Tooltips + Theme)
    ui_frame = tk.LabelFrame(content, text=" UI Settings ", bg=COLORS["bg_root"], fg=COLORS["fg_dim"], bd=1, relief="solid")
    ui_frame.pack(fill="x", pady=(0, 10))
    ui_inner = tk.Frame(ui_frame, bg=COLORS["bg_root"])
    ui_inner.pack(fill="x", padx=12, pady=8)

    # Theme selector
    self.settings_theme = tk.StringVar(value=getattr(self, "theme", "dark"))
    tk.Label(ui_inner, text="Theme:", bg=COLORS["bg_root"], fg=COLORS["fg_dim"]).grid(row=0, column=0, sticky="w")
    theme_combo = ttk.Combobox(ui_inner, textvariable=self.settings_theme, values=["dark", "purple", "blue", "light", "mint", "rose"], width=12, state="readonly")
    theme_combo.grid(row=0, column=1, sticky="w", padx=10)

    # Auto-save UI settings
    self.settings_theme.trace_add("write", auto_save)

    # Data management
    data_frame = tk.LabelFrame(content, text=" Data Management ", bg=COLORS["bg_root"], fg=COLORS["fg_dim"], bd=1, relief="solid")
    data_frame.pack(fill="x", pady=(0, 10))
    data_inner = tk.Frame(data_frame, bg=COLORS["bg_root"])
    data_inner.pack(fill="x", padx=12, pady=8)

    ModernButton(data_inner, COLORS["bg_input"], COLORS["border"], text="Export Profiles", width=14, command=self.export_data).pack(side="left", padx=(0, 8))
    ModernButton(data_inner, COLORS["bg_input"], COLORS["border"], text="Import Profiles", width=14, command=self.import_data).pack(side="left", padx=(0, 8))
    ModernButton(data_inner, COLORS["success"], COLORS["success_hover"], text="Import xNwN.ini", width=14, command=self.import_xnwn_ini).pack(side="left", padx=(0, 8))
    ModernButton(data_inner, COLORS["accent"], COLORS["accent_hover"], text="Open Backups", width=14, command=self.open_restore_dialog).pack(side="left", padx=(0, 8))
    
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

    # Bind mousewheel to all children
    self.root.after(100, lambda: bind_mousewheel(content))

    return settings_frame
