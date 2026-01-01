import tkinter as tk
from tkinter import ttk

from ui.ui_base import COLORS, ModernButton, ToggleSwitch


def build_log_monitor_screen(app):
    """Embedded log monitor screen with scrollable content."""
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

    # Make canvas window expand with canvas width
    def _on_canvas_configure(event):
        canvas.itemconfig(canvas_window, width=event.width)
    canvas.bind("<Configure>", _on_canvas_configure)

    # Mouse wheel scrolling
    def _on_mousewheel(event):
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
    canvas.bind_all("<MouseWheel>", _on_mousewheel, add="+")

    # Pack - scrollbar hidden by default (minimal), only show if needed
    canvas.pack(side="left", fill="both", expand=True)
    # Uncomment next line to show minimal scrollbar: scrollbar.pack(side="right", fill="y")

    # Main container with padding
    main = tk.Frame(scrollable_frame, bg=COLORS["bg_root"])
    main.pack(fill="both", expand=True, padx=40, pady=20)

    # Header
    header = tk.Frame(main, bg=COLORS["bg_root"])
    header.pack(fill="x", pady=(0, 20))

    tk.Label(
        header,
        text="Log Monitor",
        font=("Segoe UI", 24, "bold"),
        bg=COLORS["bg_root"],
        fg=COLORS["fg_text"]
    ).pack(side="left")

    # Enable toggle
    self.log_monitor_state.enabled_var = tk.BooleanVar(value=self.log_monitor_state.config.get("enabled", False))
    enable_frame = tk.Frame(header, bg=COLORS["bg_root"])
    enable_frame.pack(side="right")
    tk.Label(enable_frame, text="Enabled:", bg=COLORS["bg_root"], fg=COLORS["fg_dim"]).pack(side="left", padx=(0, 10))
    from ui.ui_base import ToggleSwitch
    toggle = ToggleSwitch(enable_frame, variable=self.log_monitor_state.enabled_var, command=self._on_log_monitor_toggle)
    toggle.pack(side="left")

    # Log path
    path_frame = tk.LabelFrame(main, text=" Log File ", bg=COLORS["bg_root"], fg=COLORS["fg_dim"], bd=1, relief="solid")
    path_frame.pack(fill="x", pady=(0, 15))
    path_inner = tk.Frame(path_frame, bg=COLORS["bg_root"])
    path_inner.pack(fill="x", padx=15, pady=10)

    self.log_monitor_state.log_path_var = tk.StringVar(value=self.log_monitor_state.config.get("log_path", ""))
    tk.Entry(path_inner, textvariable=self.log_monitor_state.log_path_var, width=60, bg=COLORS["bg_input"], fg=COLORS["fg_text"], relief="flat").pack(side="left", fill="x", expand=True, padx=(0, 10))
    ModernButton(path_inner, COLORS["bg_input"], COLORS["border"], text="Browse", width=10, command=self._browse_log_path).pack(side="left")

    # Webhooks
    webhooks_frame = tk.LabelFrame(main, text=" Discord Webhooks ", bg=COLORS["bg_root"], fg=COLORS["fg_dim"], bd=1, relief="solid")
    webhooks_frame.pack(fill="x", pady=(0, 15))
    webhooks_inner = tk.Frame(webhooks_frame, bg=COLORS["bg_root"])
    webhooks_inner.pack(fill="x", padx=15, pady=8)

    self.log_monitor_state.webhooks_text = tk.Text(webhooks_inner, height=3, bg=COLORS["bg_input"], fg=COLORS["fg_text"], relief="flat", font=("Consolas", 10))
    self.log_monitor_state.webhooks_text.pack(fill="x")
    self.log_monitor_state.webhooks_text.insert("1.0", "\n".join(self.log_monitor_state.config.get("webhooks", [])))
    tk.Label(webhooks_inner, text="One webhook URL per line", bg=COLORS["bg_root"], fg=COLORS["fg_dim"], font=("Segoe UI", 9)).pack(anchor="w", pady=(5, 0))

    # Keywords
    keywords_frame = tk.LabelFrame(main, text=" Keywords to Monitor ", bg=COLORS["bg_root"], fg=COLORS["fg_dim"], bd=1, relief="solid")
    keywords_frame.pack(fill="x", pady=(0, 15))
    keywords_inner = tk.Frame(keywords_frame, bg=COLORS["bg_root"])
    keywords_inner.pack(fill="x", padx=15, pady=8)

    self.log_monitor_state.keywords_text = tk.Text(keywords_inner, height=3, bg=COLORS["bg_input"], fg=COLORS["fg_text"], relief="flat", font=("Consolas", 10))
    self.log_monitor_state.keywords_text.pack(fill="x")
    self.log_monitor_state.keywords_text.insert("1.0", "\n".join(self.log_monitor_state.config.get("keywords", [])))
    tk.Label(keywords_inner, text="One keyword per line (case-insensitive)", bg=COLORS["bg_root"], fg=COLORS["fg_dim"], font=("Segoe UI", 9)).pack(anchor="w", pady=(5, 0))

    # --- Slayer: Open Wounds auto-press ---
    self.ow_frame = tk.LabelFrame(main, text=" Slayer: Open Wounds ", bg=COLORS["bg_root"], fg=COLORS["fg_dim"], bd=1, relief="solid")
    self.ow_frame.pack(fill="x", pady=(0, 15))
    ow_inner = tk.Frame(self.ow_frame, bg=COLORS["bg_root"])
    ow_inner.pack(fill="x", padx=15, pady=10)

    # Vars - slayer works independently from log monitor now
    ow_cfg = self.log_monitor_state.config.get("open_wounds", {"enabled": False, "key": "F1"})
    slayer_enabled = bool(ow_cfg.get("enabled", False))
    self.log_monitor_state.open_wounds_enabled_var = tk.BooleanVar(value=slayer_enabled)
    self.log_monitor_state.open_wounds_key_var = tk.StringVar(value=str(ow_cfg.get("key", "F1")))

    # Auto-save function for Open Wounds
    def _auto_save_open_wounds(*args):
        try:
            enabled = bool(self.log_monitor_state.open_wounds_enabled_var.get())
            # Slayer works independently - no need to check log monitor
            self.log_monitor_state.config["open_wounds"] = {
                "enabled": enabled,
                "key": str(self.log_monitor_state.open_wounds_key_var.get() or "F1"),
            }
            self.save_data()
            # Update slayer mode in running LogMonitor for instant response
            if self.log_monitor_state.monitor and self.log_monitor_state.monitor.is_running():
                self.log_monitor_state.monitor.set_slayer_mode(enabled)
            # Start/stop independent slayer monitor
            self._ensure_slayer_if_enabled()
            # Update slayer UI visual state
            self._update_slayer_ui_state()
        except Exception:
            pass

    # Trace changes
    self.log_monitor_state.open_wounds_enabled_var.trace_add("write", _auto_save_open_wounds)
    self.log_monitor_state.open_wounds_key_var.trace_add("write", _auto_save_open_wounds)

    # Row with all controls: toggle, key selector, test button
    self.ow_ctrl = tk.Frame(ow_inner, bg=COLORS["bg_root"])
    self.ow_ctrl.pack(fill="x", pady=(0, 5))

    self.ow_label = tk.Label(self.ow_ctrl, text="Auto-press F-key on 'Open Wounds Hit':", bg=COLORS["bg_root"], fg=COLORS["fg_text"])
    self.ow_label.pack(side="left", padx=(0, 10))
    from ui.ui_base import ToggleSwitch, ToolTip
    self.ow_toggle = ToggleSwitch(self.ow_ctrl, variable=self.log_monitor_state.open_wounds_enabled_var)
    self.ow_toggle.pack(side="left", padx=(0, 15))

    self.ow_key_label = tk.Label(self.ow_ctrl, text="Key:", bg=COLORS["bg_root"], fg=COLORS["fg_text"])
    self.ow_key_label.pack(side="left")
    keys = [f"F{i}" for i in range(1, 13)]
    self.ow_key_cb = ttk.Combobox(self.ow_ctrl, textvariable=self.log_monitor_state.open_wounds_key_var, values=keys, width=6, state="readonly")
    self.ow_key_cb.pack(side="left", padx=(6, 10))

    # Slayer hit counter display
    self.slayer_counter_label = tk.Label(self.ow_ctrl, text=f"Hits: {self.log_monitor_state.slayer_hit_count}", bg=COLORS["bg_root"], fg=COLORS["warning"], font=("Segoe UI", 10, "bold"))
    self.slayer_counter_label.pack(side="left", padx=(15, 5))
    ToolTip(self.slayer_counter_label, "Number of Open Wounds auto-presses this session")

    # Reset counter button
    def reset_slayer_counter():
        self.log_monitor_state.slayer_hit_count = 0
        self._update_slayer_hit_counter_ui()

    reset_btn = ModernButton(self.ow_ctrl, COLORS["bg_input"], COLORS["border"], text="↻", width=3, command=reset_slayer_counter, tooltip="Reset hit counter")
    reset_btn.pack(side="left", padx=(0, 10))

    # Note about requirement
    self.ow_note = tk.Label(ow_inner, text="(Requires Log Monitor to be enabled)", bg=COLORS["bg_root"], fg=COLORS["fg_dim"], font=("Segoe UI", 9))
    self.ow_note.pack(anchor="w", pady=(5, 0))

    # Initial state update
    self._update_slayer_ui_state()

    # Buttons
    btn_frame = tk.Frame(main, bg=COLORS["bg_root"])
    btn_frame.pack(fill="x", pady=(10, 0))

    ModernButton(
        btn_frame,
        COLORS["success"],
        COLORS["success_hover"],
        text="💾 Save & Apply",
        width=15,
        command=self._save_log_monitor_settings
    ).pack(side="left", padx=(0, 10))

    # Show actual status based on log_monitor state
    is_running = hasattr(self, 'log_monitor_state') and self.log_monitor_state.monitor and self.log_monitor_state.monitor.running
    self.log_monitor_status = tk.Label(
        btn_frame,
        text="Status: Running" if is_running else "Status: Stopped",
        bg=COLORS["bg_root"],
        fg=COLORS["success"] if is_running else COLORS["danger"],
        font=("Segoe UI", 10)
    )
    self.log_monitor_status.pack(side="left", padx=20)

    return log_frame
