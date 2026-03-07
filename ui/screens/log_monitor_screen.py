import tkinter as tk
from tkinter import ttk
from ui.ui_base import COLORS, ModernButton, ToggleSwitch, SectionFrame

def build_log_monitor_screen(app):
    """Screen for game automation features (Auto-Fog, Slayer)."""
    self = app

    log_frame = tk.Frame(self.content_frame, bg=COLORS["bg_root"])
    self.screens["log_monitor"] = log_frame

    # Scrollable container
    canvas = tk.Canvas(log_frame, bg=COLORS["bg_root"], highlightthickness=0, bd=0)
    scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=canvas.yview)
    scrollable_frame = tk.Frame(canvas, bg=COLORS["bg_root"])

    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )

    canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    def _on_canvas_configure(event):
        canvas.itemconfig(canvas_window, width=event.width)
    canvas.bind("<Configure>", _on_canvas_configure)

    canvas.pack(side="left", fill="both", expand=True)

    main = tk.Frame(scrollable_frame, bg=COLORS["bg_root"])
    main.pack(fill="both", expand=True, padx=40, pady=20)

    # Header
    header = tk.Frame(main, bg=COLORS["bg_root"])
    header.pack(fill="x", pady=(0, 20))

    tk.Label(
        header,
        text="Automation",
        font=("Segoe UI", 24, "bold"),
        bg=COLORS["bg_root"],
        fg=COLORS["fg_text"]
    ).pack(side="left")

    # Global Automation Enable
    enable_frame = tk.Frame(header, bg=COLORS["bg_root"])
    enable_frame.pack(side="right")
    
    tk.Label(enable_frame, text="Status:", bg=COLORS["bg_root"], fg=COLORS["fg_dim"]).pack(side="left", padx=(0, 10))
    toggle = ToggleSwitch(enable_frame, variable=self.log_monitor_state.enabled_var, command=self._on_log_monitor_toggle)
    toggle.pack(side="left")

    # --- Log File Path (Required for both Spy and Automation) ---
    path_frame = SectionFrame(main, text="Log File")
    path_frame.pack(fill="x", pady=(0, 15))
    path_inner = tk.Frame(path_frame, bg=COLORS["bg_root"])
    path_inner.pack(fill="x", padx=15, pady=10)

    # Use the shared log_path_var initialized in LogMonitorManager
    tk.Entry(path_inner, textvariable=self.log_monitor_state.log_path_var, width=60, bg=COLORS["bg_input"], fg=COLORS["fg_text"], relief="flat").pack(side="left", fill="x", expand=True, padx=(0, 10))
    ModernButton(path_inner, COLORS["bg_input"], COLORS["border"], text="Browse", width=10, command=self._browse_log_path).pack(side="left")

    # --- Slayer: Open Wounds Section ---
    self.ow_frame = SectionFrame(main, text="Slayer: Open Wounds")
    self.ow_frame.pack(fill="x", pady=(0, 15))
    ow_inner = tk.Frame(self.ow_frame, bg=COLORS["bg_root"])
    ow_inner.pack(fill="x", padx=15, pady=10)

    # Row with all controls: toggle, key selector, counter
    self.ow_ctrl = tk.Frame(ow_inner, bg=COLORS["bg_root"])
    self.ow_ctrl.pack(fill="x", pady=(0, 5))

    tk.Label(self.ow_ctrl, text="Auto-press F-key on 'Open Wounds Hit':", bg=COLORS["bg_root"], fg=COLORS["fg_text"]).pack(side="left", padx=(0, 10))
    ToggleSwitch(self.ow_ctrl, variable=self.log_monitor_state.open_wounds_enabled_var).pack(side="left", padx=(0, 15))

    tk.Label(self.ow_ctrl, text="Key:", bg=COLORS["bg_root"], fg=COLORS["fg_text"]).pack(side="left")
    keys = [f"F{i}" for i in range(1, 13)]
    ttk.Combobox(self.ow_ctrl, textvariable=self.log_monitor_state.open_wounds_key_var, values=keys, width=6, state="readonly").pack(side="left", padx=(6, 10))

    self.slayer_counter_label = tk.Label(self.ow_ctrl, text=f"Hits: {self.log_monitor_state.slayer_hit_count}", bg=COLORS["bg_root"], fg=COLORS["warning"], font=("Segoe UI", 10, "bold"))
    self.slayer_counter_label.pack(side="left", padx=(15, 5))

    def reset_slayer_counter():
        self.log_monitor_state.slayer_hit_count = 0
        if hasattr(self, '_update_slayer_hit_counter_ui'):
            self._update_slayer_hit_counter_ui()

    ModernButton(self.ow_ctrl, COLORS["bg_input"], COLORS["border"], text="↻", width=3, command=reset_slayer_counter).pack(side="left", padx=(0, 10))

    tk.Label(ow_inner, text="Slayer functions separately from the main automation switch.", bg=COLORS["bg_root"], fg=COLORS["fg_dim"], font=("Segoe UI", 9)).pack(anchor="w", pady=(5, 0))

    # --- Auto-Fog Section ---
    auto_fog_frame = SectionFrame(main, text="Auto-Fog (PvP)")
    auto_fog_frame.pack(fill="x", pady=(0, 15))
    af_inner = tk.Frame(auto_fog_frame, bg=COLORS["bg_root"])
    af_inner.pack(fill="x", padx=15, pady=10)

    tk.Label(af_inner, text="Auto-type '##mainscene.fog 0' in PvP Areas:", bg=COLORS["bg_root"], fg=COLORS["fg_text"]).pack(side="left", padx=(0, 10))
    ToggleSwitch(af_inner, variable=self.log_monitor_state.auto_fog_enabled_var).pack(side="left", padx=(0, 20))

    tk.Label(af_inner, text="⚠ Только при одной активной сессии",
             bg=COLORS["bg_root"], fg=COLORS["warning"],
             font=("Segoe UI", 9)).pack(side="left", padx=(5, 0))

    # --- Status Section ---
    status_frame = tk.Frame(main, bg=COLORS["bg_root"])
    status_frame.pack(fill="x", pady=(10, 0))

    is_running = hasattr(app, 'log_monitor_state') and app.log_monitor_state.enabled_var.get() and app.log_monitor_state.monitor and app.log_monitor_state.monitor.is_running()
    self.log_monitor_status = tk.Label(
        status_frame,
        text="Automation: Running" if is_running else "Automation: Stopped",
        bg=COLORS["bg_root"],
        fg=COLORS["success"] if is_running else COLORS["danger"],
        font=("Segoe UI", 10)
    )
    self.log_monitor_status.pack(side="left")

    tk.Label(status_frame, text="(Changes save automatically)", bg=COLORS["bg_root"], fg=COLORS["fg_dim"], font=("Segoe UI", 8)).pack(side="right")

    # Initial state update
    if hasattr(self, 'log_monitor_manager'):
        self.log_monitor_manager.update_slayer_ui_state()

    return log_frame
