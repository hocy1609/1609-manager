import tkinter as tk
from tkinter import ttk

from ui.ui_base import COLORS, ModernButton, SectionFrame


def build_craft_screen(app):
    """Craft screen with integrated craft UI - no dialog needed."""
    self = app

    craft_frame = tk.Frame(self.content_frame, bg=COLORS["bg_root"])
    self.screens["craft"] = craft_frame

    # Initialize craft state via manager
    if hasattr(self, "craft_manager"):
        self.craft_manager.initialize_state()
        # Initialize queue state if not present
        if not hasattr(self.craft_manager, "craft_queue"):
            self.craft_manager.craft_queue = {}

    # Main container with scroll
    main = tk.Frame(craft_frame, bg=COLORS["bg_root"])
    main.pack(fill="both", expand=True, padx=40, pady=20)

    # Header
    tk.Label(
        main,
        text="Auto Crafter",
        font=("Segoe UI", 24, "bold"),
        bg=COLORS["bg_root"],
        fg=COLORS["fg_text"]
    ).pack(anchor="w", pady=(0, 20))

    # Two columns layout
    columns = tk.Frame(main, bg=COLORS["bg_root"])
    columns.pack(fill="both", expand=True)

    # Left column - Settings
    left_col = tk.Frame(columns, bg=COLORS["bg_root"])
    left_col.pack(side="left", fill="both", expand=True, padx=(0, 20))

    # Timing settings
    timing_frame = SectionFrame(left_col, text="Timing")
    timing_frame.pack(fill="x", pady=(0, 15))
    timing_inner = tk.Frame(timing_frame, bg=COLORS["bg_root"])
    timing_inner.pack(fill="x", padx=15, pady=10)

    self._craft_row(timing_inner, 0, "Задержка открытия меню:", self.craft_state.vars["delay_open"])
    self._craft_row(timing_inner, 1, "Задержка между клавишами:", self.craft_state.vars["delay_key"])
    self._craft_row(timing_inner, 2, "Пауза между крафтами:", self.craft_state.vars["delay_craft"])
    
    # ... (rest of UI building) ...

    def update_queue_calls(restore_data):
        """
        restore_data: list of (name, seq, count, active)
        """
        # Reset all to 0
        for name_lbl, count_var, toggle_var, scale, seq_key in self.row_widgets:
             count_var.set(0)
             toggle_var.set(False)
        
        # Map restore data
        # restore_data is list of (name, seq, count, active)
        # We match by seq key
        
        restore_map = {item[1]: item[2] for item in restore_data} # seq -> count
        
        for name_lbl, count_var, toggle_var, scale, seq_key in self.row_widgets:
            if seq_key in restore_map:
                count = restore_map[seq_key]
                count_var.set(count)
                if count > 0:
                    toggle_var.set(True)
    
    # Attach helper to app so CraftManager can use it
    self.update_craft_queue_ui = update_queue_calls
    
    # Open Sequence moved here
    tk.Label(timing_inner, text="Brew Potion Location:", bg=COLORS["bg_root"], fg=COLORS["fg_dim"], anchor="w").grid(
        row=4, column=0, sticky="w", pady=2
    )
    seq_entry = tk.Entry(
        timing_inner, textvariable=self.craft_state.vars["open_sequence"], width=35, bg=COLORS["bg_input"], 
        fg=COLORS["fg_text"], relief="flat", insertbackground=COLORS["fg_text"]
    )
    seq_entry.grid(row=4, column=1, sticky="w", padx=(10, 0), pady=2)
    # Hint label below the entry
    tk.Label(timing_inner, text="F1-12, Ctrl, Shift", bg=COLORS["bg_root"], fg=COLORS["fg_dim"],
             font=("Segoe UI", 7), anchor="w").grid(row=5, column=1, sticky="w", padx=(10, 0))



    # Potion recipes: (display_name, sequence)
    # Sequence: category + item (confirmation "1" is added automatically)
    # Menu opened with NUMPAD0,NUMPAD4,NUMPAD2
    self.potion_recipes = [
        # Категория 2: Простые зелья
        ("Зелье Исцеления Средних Ран", "21"),
        ("Зелье Противоядия", "22"),
        ("Зелье Деревянной Кожи", "23"),
        ("Зелье Малого Восстановления", "24"),
        ("Зелье Помощи", "25"),
        ("Зелье Знаний", "26"),
        # Категория 3: Улучшенные зелья
        ("Зелье Благословения", "31"),
        ("Зелье Исцеления Серьезных Ран", "32"),
        ("Зелье Ясности", "33"),
        ("Зелье Невидимости", "34"),
        ("Зелье Улучшенного Зрения", "35"),
        ("Зелье Быстрого Бега", "36"),
        # Категория 4: Продвинутые зелья
        ("Большое Зелье Выносливости", "41"),
        ("Большое Зелье Ловкости", "42"),
        ("Большое Зелье Харизмы", "43"),
        ("Большое Зелье Интеллекта", "44"),
        ("Большое Зелье Мудрости", "45"),
        ("Большое Зелье Силы", "46"),
        ("Зелье Исцеления Смертельных Ран", "47"),
        ("Зелье Всевидения", "48"),
        ("Зелье Скорости", "49"),
    ]

    # Build list for combobox
    self.potion_list = [name for name, seq in self.potion_recipes]
    self.potion_sequences = {name: seq for name, seq in self.potion_recipes}

    self.potion_sequences = {name: seq for name, seq in self.potion_recipes}

    # Craft settings - Queue selector
    craft_settings = SectionFrame(left_col, text="Очередь крафта")
    craft_settings.pack(fill="both", expand=True, pady=(0, 15))
    craft_inner = tk.Frame(craft_settings, bg=COLORS["bg_root"])
    craft_inner.pack(fill="both", expand=True, padx=10, pady=10)
    
    # Header for columns
    header_frame = tk.Frame(craft_inner, bg=COLORS["bg_root"])
    header_frame.pack(fill="x", pady=(0, 5))
    tk.Label(header_frame, text="Зелье", bg=COLORS["bg_root"], fg=COLORS["fg_dim"], font=("Segoe UI", 9, "bold")).pack(side="left", padx=5)
    tk.Label(header_frame, text="Кол-во", bg=COLORS["bg_root"], fg=COLORS["fg_dim"], font=("Segoe UI", 9, "bold")).pack(side="right", padx=25)

    # Scrollable potion list
    list_frame = tk.Frame(craft_inner, bg=COLORS["bg_input"], bd=1, relief="solid")
    list_frame.pack(fill="both", expand=True)

    # Canvas with scrollbar
    canvas = tk.Canvas(list_frame, bg=COLORS["bg_input"], highlightthickness=0, height=200)
    scrollbar = tk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
    self.potions_frame = tk.Frame(canvas, bg=COLORS["bg_input"])

    self.potions_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=self.potions_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    # Mouse wheel scroll
    def _on_mousewheel(event):
        canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    canvas.bind_all("<MouseWheel>", _on_mousewheel)

    # Populate potion list with checkboxes
    if hasattr(self, "craft_manager"):
        self.craft_manager._populate_craft_list(self.potions_frame)

    # Reset Queue Button
    reset_btn_row = tk.Frame(craft_inner, bg=COLORS["bg_root"])
    reset_btn_row.pack(fill="x", pady=(10, 0))
    
    ModernButton(
        reset_btn_row,
        COLORS["bg_panel"],
        COLORS["border"],
        text="Сбросить очередь",
        command=lambda: self.craft_manager._reset_queue() if hasattr(self, "craft_manager") else None,
        width=15
    ).pack(side="right")

    # Right column - Controls
    right_col = tk.Frame(columns, bg=COLORS["bg_root"])
    right_col.pack(side="left", fill="both", expand=False, padx=(10, 0))

    # Controls Frame
    controls_frame = SectionFrame(right_col, text="Controls")
    controls_frame.pack(fill="both", expand=True) # expand to fill space
    controls_inner = tk.Frame(controls_frame, bg=COLORS["bg_root"])
    controls_inner.pack(fill="both", expand=True, padx=15, pady=15)
    
    # Status Label (Large)
    self.craft_status_lbl = tk.Label(
        controls_inner, 
        text="Остановлено (0 нажатий, 0 зелий)", 
        bg=COLORS["bg_root"], 
        fg=COLORS["danger"],
        font=("Segoe UI", 11, "bold"),
        wraplength=250
    )
    self.craft_status_lbl.pack(pady=(0, 10))
    
    # Progress Bar
    style = ttk.Style()
    style.theme_use('default')
    style.configure("green.Horizontal.TProgressbar", background=COLORS["success"], troughcolor=COLORS["bg_input"], borderwidth=0)
    
    self.craft_progress = ttk.Progressbar(
        controls_inner, 
        orient="horizontal", 
        length=200, 
        mode="determinate",
        style="green.Horizontal.TProgressbar"
    )
    self.craft_progress.pack(fill="x", pady=(0, 10))
    
    # Detailed Status Log
    self.craft_details_log = tk.Text(
        controls_inner,
        height=10,
        bg=COLORS["bg_input"],
        fg=COLORS["fg_text"],
        font=("Consolas", 9),
        relief="flat",
        state="disabled"
    )
    self.craft_details_log.pack(fill="both", expand=True, pady=(0, 10))
    
    # Start/Stop Buttons
    btn_frame = tk.Frame(controls_inner, bg=COLORS["bg_root"])
    btn_frame.pack(fill="x", pady=5)
    
    self.craft_btn_start = ModernButton(
        btn_frame, 
        COLORS["success"], 
        COLORS["success_hover"], 
        text="▷ START", 
        command=self.craft_start,
        width=12
    )
    self.craft_btn_start.pack(side="left", padx=(0, 10))
    
    self.craft_btn_stop = ModernButton(
        btn_frame, 
        COLORS["danger"], 
        COLORS["danger_hover"], 
        text="■ STOP", 
        command=self.craft_stop,
        width=12
    )
    self.craft_btn_stop.pack(side="left")
    
    self.craft_btn_resume = ModernButton(
        btn_frame,
        COLORS["accent"],
        COLORS["accent_hover"],
        text="▷ RESUME",
        command=lambda: self.craft_manager.craft_resume() if hasattr(self, "craft_manager") else None,
        width=12
    )
    self.craft_btn_resume.pack(side="left", padx=(10, 0))
    self.craft_btn_resume.configure(state="disabled") # Initially disabled

    # RESTORE MISSING Button
    self.craft_btn_restore = ModernButton(
        btn_frame,
        COLORS["warning"],
        COLORS["warning_hover"],
        text="↻ RESTORE",
        command=lambda: self.craft_manager.restore_missing_items() if hasattr(self, "craft_manager") else None,
        width=12
    )
    self.craft_btn_restore.pack(side="left", padx=(10, 0))
    # enabled always or only after stop? Let's leave enabled.
    
    # ...

    def set_queue(self, new_queue_data):
        """
        Updates the UI queue with new data.
        new_queue_data: list of tuples (name, seq, count, active_bool)
        """
        # Clear current
        for widget in self.queue_list_frame.winfo_children():
            widget.destroy()
        self.row_widgets = []
        
        # Re-populate
        # We need to map (name, seq, count, active) to the UI creation logic
        # populating self.row_widgets
        
        for name, seq, count, active in new_queue_data:
            self.add_queue_item(name, seq, count, active)

    def add_queue_item(self, name, seq, count, active=False):
        """Helper to add a row to queue list (refactored helper or inline)."""
        # We need to replicate the logic from `populate_queue_list` or `_create_row`.
        # `populate_queue_list` iterates `self.app.potions_data`.
        # Here we adding specific items which might NOT be in the static list 
        # (though they should be).
        # Actually, `populate_queue_list` builds the list from ALL available potions.
        # The user wants to "restore missing", implying we sets the counts for specific items.
        
        # Strategy:
        # The current UI (`populate_queue_list`) lists ALL potions with 0 count.
        # It's a static list where user changes numbers.
        # If we "restore missing", we probably want to Set the counts on existing rows?
        # OR does the user want a "Queue" view like in the screenshot? 
        # The screenshot shows a list of ALL potions with toggle/count.
        
        # So "Restoring" means: Find the row for "Potion X", set its count to Y, set Checkbox to ON.
        # Set all others to 0 / OFF.
        
        # We need to iterate self.row_widgets and update them.
        pass

    def update_queue_calls(self, restore_data):
        """
        restore_data: list of (name, seq, count, active)
        """
        # Reset all to 0
        for name_lbl, count_var, toggle_var, scale, seq_key in self.row_widgets:
             count_var.set(0)
             toggle_var.set(False)
        
        # Map restore data
        # restore_data is list of (name, seq, count, active)
        # We match by seq key
        
        restore_map = {item[1]: item[2] for item in restore_data} # seq -> count
        
        for name_lbl, count_var, toggle_var, scale, seq_key in self.row_widgets:
            if seq_key in restore_map:
                count = restore_map[seq_key]
                count_var.set(count)
                if count > 0:
                    toggle_var.set(True)


    # Presets Section
    presets_frame = SectionFrame(right_col, text="Presets")
    presets_frame.pack(fill="x", pady=(15, 0))
    presets_inner = tk.Frame(presets_frame, bg=COLORS["bg_root"])
    presets_inner.pack(fill="x", padx=10, pady=10)
    
    # Save Mode Toggle
    self.preset_save_mode = tk.BooleanVar(value=False)
    
    def toggle_save_mode():
        mode = self.preset_save_mode.get()
        if mode:
            btn_save.configure(bg=COLORS["danger"], text="SAVE MODE: ON")
        else:
            btn_save.configure(bg=COLORS["bg_panel"], text="Save Preset")
    
    btn_save = tk.Checkbutton(
        presets_inner, 
        text="Save Preset", 
        variable=self.preset_save_mode,
        indicatoron=False,
        bg=COLORS["bg_panel"],
        fg=COLORS["fg_text"],
        selectcolor=COLORS["danger"],
        activebackground=COLORS["bg_panel"],
        activeforeground=COLORS["fg_text"],
        command=toggle_save_mode,
        font=("Segoe UI", 9),
        width=12,
        bd=0
    )
    btn_save.pack(side="top", pady=(0, 10))
    
    # 1-5 Buttons
    slots_frame = tk.Frame(presets_inner, bg=COLORS["bg_root"])
    slots_frame.pack(fill="x")
    
    def on_preset_click(idx):
        if self.preset_save_mode.get():
            # Save
            if hasattr(self, "craft_manager"):
                self.craft_manager.save_current_to_preset(idx)
                # Auto turn off save mode
                self.preset_save_mode.set(False)
                toggle_save_mode()
        else:
            # Load
            if hasattr(self, "craft_manager"):
                self.craft_manager.apply_preset(idx)
    
    for i in range(1, 6):
        ModernButton(
            slots_frame,
            COLORS["bg_panel"],
            COLORS["border"],
            text=str(i),
            command=lambda x=i: on_preset_click(x),
            width=3
        ).pack(side="left", padx=2)
    


    return craft_frame
