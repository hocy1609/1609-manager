import tkinter as tk
from tkinter import ttk

from ui.ui_base import COLORS, ModernButton


def build_craft_screen(app):
    """Craft screen with integrated craft UI - no dialog needed."""
    self = app

    craft_frame = tk.Frame(self.content_frame, bg=COLORS["bg_root"])
    self.screens["craft"] = craft_frame

    # Initialize craft state via manager
    if hasattr(self, "craft_manager"):
        self.craft_manager.initialize_state()

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
    timing_frame = tk.LabelFrame(left_col, text=" Timing ", bg=COLORS["bg_root"], fg=COLORS["fg_dim"], bd=1, relief="solid")
    timing_frame.pack(fill="x", pady=(0, 15))
    timing_inner = tk.Frame(timing_frame, bg=COLORS["bg_root"])
    timing_inner.pack(fill="x", padx=15, pady=10)

    self._craft_row(timing_inner, 0, "Задержка после F10:", self.craft_state.vars["delay_action"])
    self._craft_row(timing_inner, 1, "Задержка первого крафта:", self.craft_state.vars["delay_first"])
    self._craft_row(timing_inner, 2, "Задержка после крафта:", self.craft_state.vars["delay_seq"])
    self._craft_row(timing_inner, 3, "Задержка после R:", self.craft_state.vars["delay_r"])
    self._craft_row(timing_inner, 4, "Повторов до R:", self.craft_state.vars["repeat_before_r"])

    # Potion recipes: (display_name, sequence)
    # Sequence: category + item + "1" for confirmation (Да)
    self.potion_recipes = [
        # Уровень 1
        ("Зелье Самогон", "111"),
        ("Зелье Пиво", "121"),
        ("Зелье Вино", "131"),
        ("Зелье Эль", "141"),
        ("Зелье Исцеления Легких Ран", "151"),
        # Уровень 2
        ("Зелье Исцеления Средних Ран", "211"),
        ("Зелье Противоядия", "221"),
        ("Зелье Благословения", "231"),
        ("Зелье Деревянной Кожи", "241"),
        ("Зелье Малого Восстановления", "251"),
        # Уровень 3
        ("Зелье Знаний", "311"),
        ("Зелье Исцеления Серьезных Ран", "321"),
        ("Зелье Ясности", "331"),
        ("Зелье Невидимости", "341"),
        # Уровень 4
        ("Зелье Выносливости (большое)", "411"),
        ("Зелье Ловкости (большое)", "421"),
        ("Зелье Харизмы (большое)", "431"),
        ("Зелье Интеллекта (большое)", "441"),
        ("Зелье Мудрости (большое)", "451"),
        ("Зелье Силы (большое)", "461"),
        ("Зелье Исцеления Смертельных Ран", "471"),
        ("Зелье Всевидения", "481"),
        ("Зелье Скорости", "491"),
        # Секретные (уровень 5)
        ("Зелье Ауры Славы", "511"),
        ("Зелье Божественной Силы", "521"),
        ("Зелье Великого Восстановления", "531"),
        ("Зелье Защиты от Заклинаний", "541"),
        ("Зелье Защиты от Негативной Энергии", "551"),
        ("Зелье Камнекожи", "561"),
        ("Зелье Массового Камуфляжа", "571"),
        ("Зелье Призрачного Вида", "581"),
        ("Зелье Превращения", "591"),
        ("Зелье Щита Смерти", "5101"),
        ("Зелье Элементального Щита", "5111"),
    ]

    # Build list for combobox
    self.potion_list = [name for name, seq in self.potion_recipes]
    self.potion_sequences = {name: seq for name, seq in self.potion_recipes}

    # Load favorites from saved data
    self.favorite_potions = set(getattr(self, "_loaded_favorite_potions", []))

    # Craft settings - Potion selector with favorites
    craft_settings = tk.LabelFrame(left_col, text=" Выбор зелья ", bg=COLORS["bg_root"], fg=COLORS["fg_dim"], bd=1, relief="solid")
    craft_settings.pack(fill="both", expand=True, pady=(0, 15))
    craft_inner = tk.Frame(craft_settings, bg=COLORS["bg_root"])
    craft_inner.pack(fill="both", expand=True, padx=10, pady=10)

    # Selected potion display
    selected_frame = tk.Frame(craft_inner, bg=COLORS["bg_root"])
    selected_frame.pack(fill="x", pady=(0, 10))
    tk.Label(selected_frame, text="Выбрано:", bg=COLORS["bg_root"], fg=COLORS["fg_dim"]).pack(side="left")
    self.selected_potion_lbl = tk.Label(selected_frame, text="—", bg=COLORS["bg_root"], fg=COLORS["accent"], font=("Segoe UI", 10, "bold"))
    self.selected_potion_lbl.pack(side="left", padx=(10, 0))

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

    # Populate potion list
    self._populate_potion_list()

    # Settings row below
    settings_row = tk.Frame(craft_inner, bg=COLORS["bg_root"])
    settings_row.pack(fill="x", pady=(10, 0))

    tk.Label(settings_row, text="Menu Key:", bg=COLORS["bg_root"], fg=COLORS["fg_dim"]).pack(side="left")
    tk.Entry(settings_row, textvariable=self.craft_state.vars["action_key"], width=6, bg=COLORS["bg_input"], fg=COLORS["fg_text"], relief="flat").pack(side="left", padx=(5, 20))

    tk.Label(settings_row, text="Лимит:", bg=COLORS["bg_root"], fg=COLORS["fg_dim"]).pack(side="left")
    tk.Entry(settings_row, textvariable=self.craft_state.vars["potion_limit"], width=6, bg=COLORS["bg_input"], fg=COLORS["fg_text"], relief="flat").pack(side="left", padx=(5, 0))

    # Right column - Drag settings & Controls
    right_col = tk.Frame(columns, bg=COLORS["bg_root"])
    right_col.pack(side="left", fill="both", expand=True)

    # Drag Macro settings
    drag_frame = tk.LabelFrame(right_col, text=" Drag Macro ", bg=COLORS["bg_root"], fg=COLORS["fg_dim"], bd=1, relief="solid")
    drag_frame.pack(fill="x", pady=(0, 15))
    drag_inner = tk.Frame(drag_frame, bg=COLORS["bg_root"])
    drag_inner.pack(fill="x", padx=15, pady=10)

    # Macro status
    self.macro_status_lbl = tk.Label(
        drag_inner,
        text="No macro recorded",
        bg=COLORS["bg_root"],
        fg=COLORS["fg_dim"],
        font=("Segoe UI", 10)
    )
    self.macro_status_lbl.pack(anchor="w", pady=(0, 10))

    # Record button
    macro_btn_row = tk.Frame(drag_inner, bg=COLORS["bg_root"])
    macro_btn_row.pack(fill="x")

    self.craft_btn_record = ModernButton(
        macro_btn_row,
        COLORS["danger"],
        COLORS["danger_hover"],
        text="🔴 RECORD",
        command=self.craft_start_recording,
        width=10
    )
    self.craft_btn_record.pack(side="left", padx=(0, 5))

    self.craft_btn_save_macro = ModernButton(
        macro_btn_row,
        COLORS["success"],
        COLORS["success_hover"],
        text="💾 Save",
        command=self.craft_save_macro,
        width=8
    )
    self.craft_btn_save_macro.pack(side="left", padx=(0, 5))

    self.craft_btn_clear_macro = ModernButton(
        macro_btn_row,
        COLORS["bg_input"],
        COLORS["border"],
        text="✕",
        command=self.craft_clear_macro,
        width=3
    )
    self.craft_btn_clear_macro.pack(side="left")

    # Saved macros dropdown
    saved_row = tk.Frame(drag_inner, bg=COLORS["bg_root"])
    saved_row.pack(fill="x", pady=(10, 0))

    tk.Label(saved_row, text="Saved:", bg=COLORS["bg_root"], fg=COLORS["fg_dim"]).pack(side="left")
    self.macro_combo = ttk.Combobox(saved_row, textvariable=self.craft_state.vars["selected_macro"], width=20, state="readonly")
    self.macro_combo.pack(side="left", padx=(5, 5))
    self.macro_combo.bind("<<ComboboxSelected>>", self.craft_load_selected_macro)

    self.craft_btn_delete_macro = ModernButton(
        saved_row,
        COLORS["danger"],
        COLORS["danger_hover"],
        text="🗑",
        command=self.craft_delete_macro,
        width=3
    )
    self.craft_btn_delete_macro.pack(side="left")

    # Load saved macros list
    self._refresh_macro_list()

    # Instructions
    tk.Label(
        drag_inner,
        text="RECORD → switch to NWN → drag → Alt+Tab\nAlt+Tab also stops playback",
        bg=COLORS["bg_root"],
        fg=COLORS["fg_dim"],
        font=("Segoe UI", 9),
        justify="left"
    ).pack(anchor="w", pady=(10, 0))

    # Speed slider
    speed_frame = tk.Frame(drag_inner, bg=COLORS["bg_root"])
    speed_frame.pack(fill="x", pady=(10, 0))

    tk.Label(speed_frame, text="Speed:", bg=COLORS["bg_root"], fg=COLORS["fg_dim"]).pack(side="left")
    self.speed_slider = tk.Scale(
        speed_frame,
        from_=0.1,
        to=5.0,
        resolution=0.1,
        orient="horizontal",
        variable=self.craft_state.vars["macro_speed"],
        bg=COLORS["bg_root"],
        fg=COLORS["fg_text"],
        troughcolor=COLORS["bg_input"],
        highlightthickness=0,
        length=150,
        showvalue=True
    )
    self.speed_slider.pack(side="left", padx=(5, 10))
    tk.Label(speed_frame, text="x", bg=COLORS["bg_root"], fg=COLORS["fg_dim"]).pack(side="left")

    # Repeat count
    tk.Label(speed_frame, text="Repeat:", bg=COLORS["bg_root"], fg=COLORS["fg_dim"]).pack(side="left", padx=(20, 0))
    tk.Entry(speed_frame, textvariable=self.craft_state.vars["macro_repeats"], width=4, bg=COLORS["bg_input"], fg=COLORS["fg_text"], relief="flat").pack(side="left", padx=(5, 0))
    # Controls
    ctrl_frame = tk.LabelFrame(right_col, text=" Controls ", bg=COLORS["bg_root"], fg=COLORS["fg_dim"], bd=1, relief="solid")
    ctrl_frame.pack(fill="x")
    ctrl_inner = tk.Frame(ctrl_frame, bg=COLORS["bg_root"])
    ctrl_inner.pack(fill="x", padx=15, pady=15)

    # Status
    self.craft_status_lbl = tk.Label(
        ctrl_inner,
        text="Остановлено (0 зелий)",
        fg=COLORS["danger"],
        bg=COLORS["bg_root"],
        font=("Segoe UI", 12, "bold")
    )
    self.craft_status_lbl.pack(pady=(0, 15))

    # Buttons row
    btn_row = tk.Frame(ctrl_inner, bg=COLORS["bg_root"])
    btn_row.pack(fill="x")

    self.craft_btn_start = ModernButton(
        btn_row,
        COLORS["success"],
        COLORS["success_hover"],
        text="▶ START",
        command=self.craft_start,
        width=12
    )
    self.craft_btn_start.pack(side="left", padx=(0, 5))

    self.craft_btn_stop = ModernButton(
        btn_row,
        COLORS["danger"],
        COLORS["danger_hover"],
        text="■ STOP",
        command=self.craft_stop,
        width=12
    )
    self.craft_btn_stop.pack(side="left", padx=(0, 5))
    self.craft_btn_stop.configure(state="disabled")

    btn_row2 = tk.Frame(ctrl_inner, bg=COLORS["bg_root"])
    btn_row2.pack(fill="x", pady=(10, 0))

    self.craft_btn_drag = ModernButton(
        btn_row2,
        COLORS["accent"],
        COLORS["accent_hover"],
        text="⇄ DRAG POTIONS",
        command=self.craft_drag_potions,
        width=18
    )
    self.craft_btn_drag.pack(side="left")

    # Settings button (gear icon)
    self.craft_btn_settings = ModernButton(
        btn_row2,
        COLORS["bg_panel"],
        COLORS["border"],
        text="⚙",
        command=self._open_craft_settings,
        width=3
    )
    self.craft_btn_settings.pack(side="right")

    return craft_frame
