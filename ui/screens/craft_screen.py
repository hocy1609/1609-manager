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
    self._craft_row(timing_inner, 2, "Пауза между крафтами:", self.craft_state.vars["delay_between"])
    
    # Open Sequence moved here
    tk.Label(timing_inner, text="Seq Открытия:", bg=COLORS["bg_root"], fg=COLORS["fg_dim"], anchor="w").grid(
        row=3, column=0, sticky="w", pady=2
    )
    tk.Entry(
        timing_inner, textvariable=self.craft_state.vars["open_sequence"], width=25, bg=COLORS["bg_input"], 
        fg=COLORS["fg_text"], relief="flat", insertbackground=COLORS["fg_text"]
    ).grid(row=3, column=1, sticky="w", padx=(10, 0), pady=2)

    # Potion recipes: (display_name, sequence)
    # Sequence: category + item (confirmation "1" is added automatically)
    # Menu opened with NUMPAD0,NUMPAD4,NUMPAD2
    self.potion_recipes = [
        # Категория 1: Алкоголь
        ("Самогон", "11"),
        ("Пиво", "12"),
        ("Вино", "13"),
        ("Эль", "14"),
        ("Зелье Исцеления Легких Ран", "15"),
        # Категория 2: Простые зелья
        ("Зелье Исцеления Средних Ран", "21"),
        ("Зелье Противоядия", "22"),
        ("Зелье Деревянной Кожи", "23"),
        ("Зелье Малого Восстановления", "24"),
        ("Зелье Помощи", "25"),
        ("Зелье Знаний", "26"),
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
    right_col.pack(side="left", fill="both", expand=True, padx=(10, 0))

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
    self.craft_status_lbl.pack(pady=(0, 20))
    
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
    


    return craft_frame
