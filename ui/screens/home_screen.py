import tkinter as tk
from tkinter import ttk

from ui.ui_base import COLORS, ModernButton


def build_home_screen(app):
    """Original main UI assembled as the Home screen."""
    self = app

    home_frame = tk.Frame(self.content_frame, bg=COLORS["bg_root"])
    self.screens["home"] = home_frame

    container = tk.Frame(home_frame, bg=COLORS["bg_root"])
    container.pack(fill="both", expand=True)

    # Main layout: Sidebar (left) + Content (right)
    game_split = tk.Frame(container, bg=COLORS["bg_root"])
    game_split.pack(fill="both", expand=True)

    # --- Sidebar ---
    sidebar = tk.Frame(game_split, bg=COLORS["bg_panel"], width=260)
    sidebar.pack(side="left", fill="y")
    sidebar.pack_propagate(False)

    accounts_header = tk.Frame(sidebar, bg=COLORS["bg_panel"])
    accounts_header.pack(fill="x", padx=10, pady=(25, 10))
    tk.Label(
        accounts_header,
        text="ACCOUNTS",
        bg=COLORS["bg_panel"],
        fg=COLORS["fg_dim"],
        font=("Segoe UI", 10, "bold"),
    ).pack(side="left")
    self.btn_add_profile_side = ModernButton(
        accounts_header,
        COLORS["accent"],
        COLORS["accent_hover"],
        text="+",
        width=3,
        command=self.add_profile,
        tooltip="Добавить профиль",
    )
    self.btn_add_profile_side.pack(side="right")

    accounts_wrap = tk.Frame(sidebar, bg=COLORS["bg_panel"])
    accounts_wrap.pack(fill="both", expand=True, padx=10, pady=(0, 10))
    self.lb = tk.Listbox(
        accounts_wrap,
        bg=COLORS["bg_panel"],
        fg=COLORS["fg_text"],
        selectbackground=COLORS["bg_input"],
        selectforeground=COLORS["accent"],
        bd=0,
        highlightthickness=0,
        font=("Segoe UI", 11),
        activestyle="none",
    )
    self.lb.pack(side="left", fill="both", expand=True)

    # Inline action buttons
    self.inline_action_frame = tk.Frame(self.lb, bg=COLORS["bg_panel"], bd=0)
    self.inline_action_frame.place_forget()

    self.btn_edit_profile = ModernButton(
        self.inline_action_frame,
        COLORS["bg_panel"],
        COLORS["bg_input"],
        text="🖉",
        width=3,
        fg=COLORS["accent"],
        font=("Segoe UI", 10, "bold"),
        command=self._inline_edit_profile,
        tooltip="Редактировать выбранный профиль",
    )
    self.btn_edit_profile.pack(side="left", padx=(0, 6))

    self.btn_delete_profile_top = ModernButton(
        self.inline_action_frame,
        COLORS["bg_panel"],
        COLORS["bg_input"],
        text="✕",
        width=3,
        fg=COLORS["danger"],
        font=("Segoe UI", 10, "bold"),
        command=self._inline_delete_profile,
        tooltip="Удалить выбранный профиль",
    )
    self.btn_delete_profile_top.pack(side="left")

    self.btn_edit_profile.configure(state="disabled")
    self.btn_delete_profile_top.configure(state="disabled")
    self.inline_action_frame_visible = False
    self._inline_action_index = None
    self._inline_hide_job = None

    self.lb.bind("<<ListboxSelect>>", self.on_select)
    self.lb.bind("<Button-1>", self.on_drag_start)
    self.lb.bind("<ButtonRelease-1>", self.on_drag_drop)
    self.lb.bind("<Button-3>", self.on_right_click)
    self.lb.bind("<Motion>", self.on_profile_list_motion)
    self.lb.bind("<Leave>", self.on_profile_list_leave)
    self.lb.bind("<FocusOut>", lambda e: self.hide_inline_actions())
    self.lb.bind("<MouseWheel>", self.on_profile_list_scroll)

    self.inline_action_frame.bind("<Enter>", lambda e: self._cancel_inline_hide())
    self.inline_action_frame.bind("<Leave>", lambda e: self.on_profile_list_leave(e))
    for child in self.inline_action_frame.winfo_children():
        child.bind("<Enter>", lambda e: self._cancel_inline_hide())
        child.bind("<Leave>", lambda e: self.on_profile_list_leave(e))

    # --- Content Area ---
    content = tk.Frame(game_split, bg=COLORS["bg_root"])
    content.pack(side="left", fill="both", expand=True, padx=40, pady=40)
    self.home_content = content

    self.header_lbl = tk.Label(
        content,
        text="Select Profile",
        bg=COLORS["bg_root"],
        fg=COLORS["fg_text"],
        font=("Segoe UI", 26, "bold"),
    )
    self.header_lbl.pack(anchor="w", pady=(0, 5))

    self.cat_lbl = tk.Label(
        content,
        text="",
        bg=COLORS["bg_root"],
        fg=COLORS["accent"],
        font=("Segoe UI", 10),
    )
    self.cat_lbl.pack(anchor="w")

    self.info_frame = tk.Frame(content, bg=COLORS["bg_root"])
    self.info_frame.pack(fill="x", pady=20)

    f_key = tk.Frame(self.info_frame, bg=COLORS["bg_root"])
    f_key.pack(fill="x", pady=8)

    tk.Label(
        f_key,
        text="CD Key:",
        bg=COLORS["bg_root"],
        fg=COLORS["fg_dim"],
        font=("Segoe UI", 9),
    ).pack(anchor="w")

    key_cont = tk.Frame(f_key, bg=COLORS["bg_root"])
    key_cont.pack(fill="x", pady=(2, 0))

    self.info_cdkey = tk.Entry(
        key_cont,
        bg=COLORS["bg_root"],
        fg=COLORS["fg_text"],
        relief="flat",
        readonlybackground=COLORS["bg_root"],
        font=("Segoe UI Mono", 10),
    )
    self.info_cdkey.pack(side="left", fill="x", expand=True)
    self.info_cdkey.config(state="readonly")

    ModernButton(
        key_cont,
        COLORS["bg_root"],
        COLORS["bg_panel"],
        text="👁",
        width=3,
        fg=COLORS["accent"],
        command=self.toggle_key_visibility,
        tooltip="Show/Hide CD Key",
    ).pack(side="right", padx=5)

    def info_row(label: str):
        f = tk.Frame(self.info_frame, bg=COLORS["bg_root"])
        f.pack(fill="x", pady=8)
        tk.Label(
            f,
            text=label,
            bg=COLORS["bg_root"],
            fg=COLORS["fg_dim"],
            font=("Segoe UI", 9),
        ).pack(anchor="w")
        e = tk.Entry(
            f,
            bg=COLORS["bg_root"],
            fg=COLORS["fg_text"],
            relief="flat",
            readonlybackground=COLORS["bg_root"],
            font=("Segoe UI Mono", 10),
        )
        e.pack(fill="x", pady=(2, 0))
        e.config(state="readonly")
        return e

    # self.info_name removed as requested
    self.info_login = info_row("Login:")

    # Spacer to push bottom elements down (occupies remaining space)
    tk.Frame(content, bg=COLORS["bg_root"]).pack(fill="both", expand=True)

    # Bottom action bar (Packed FIRST with side=bottom to be at the very bottom)
    bottom_actions = tk.Frame(content, bg=COLORS["bg_root"])
    bottom_actions.pack(side="bottom", fill="x", pady=(10, 0))
    self.btn_play = ModernButton(
        bottom_actions,
        COLORS["accent"],
        COLORS["accent_hover"],
        text="▶",
        width=4,
        font=("Segoe UI", 12, "bold"),
        command=self.launch_game,
        tooltip="Запустить игру",
    )
    self.btn_play.pack(side="left", padx=(0, 6))
    self.ctrl_frame = tk.Frame(bottom_actions, bg=COLORS["bg_root"])
    self.ctrl_frame.pack(side="left")
    self.btn_restart = ModernButton(
        self.ctrl_frame,
        COLORS["accent"],
        COLORS["accent_hover"],
        text="↻",
        width=4,
        font=("Segoe UI", 12, "bold"),
        command=self.restart_game,
        tooltip="Перезапустить игру",
    )
    self.btn_restart.pack(side="left", padx=(0, 6))
    self.btn_close = ModernButton(
        self.ctrl_frame,
        COLORS["accent"],
        COLORS["accent_hover"],
        text="✕",
        width=4,
        font=("Segoe UI", 12, "bold"),
        command=self.close_game,
        tooltip="Безопасный выход из игры",
    )
    self.btn_close.pack(side="left")

    # Server controls (Packed NEXT with side=bottom to be above buttons)
    srv_frame = tk.Frame(content, bg=COLORS["bg_root"])
    srv_frame.pack(side="bottom", fill="x", pady=(0, 20))

    check_row = tk.Frame(srv_frame, bg=COLORS["bg_root"])
    check_row.pack(fill="x")

    ttk.Checkbutton(
        check_row,
        text="Auto-connect to server",
        variable=self.use_server_var,
        command=self.toggle_server_ui,
    ).pack(side="left")

    self.status_lbl = tk.Label(
        check_row,
        text="",
        bg=COLORS["bg_root"],
        fg=COLORS["fg_dim"],
        font=("Segoe UI", 9),
    )
    self.status_lbl.pack(side="right")

    self.srv_ctrl = tk.Frame(srv_frame, bg=COLORS["bg_root"])
    self.srv_ctrl.pack(fill="x", pady=(5, 0))

    srv_names = [s["name"] for s in self.servers]
    self.cb_server = ttk.Combobox(
        self.srv_ctrl,
        textvariable=self.server_var,
        values=srv_names,
        font=("Segoe UI", 10),
    )
    self.cb_server.pack(
        side="left",
        fill="x",
        expand=True,
        ipady=4,
    )

    self.cb_server.bind("<<ComboboxSelected>>", lambda e: self._on_server_selected())

    ModernButton(
        self.srv_ctrl,
        COLORS["bg_panel"],
        COLORS["border"],
        text="+",
        width=3,
        command=self.add_server,
        tooltip="Add new server",
    ).pack(side="left", padx=(5, 0))

    ModernButton(
        self.srv_ctrl,
        COLORS["bg_panel"],
        COLORS["border"],
        text="-",
        width=3,
        command=self.remove_server,
        tooltip="Remove selected server",
    ).pack(side="left", padx=(5, 0))

    self.toggle_server_ui()

    # Пакуем блок кнопок управления всегда (статусы меняются логикой)

    # Удалён старый блок запуска из панели профиля
    # --- Adaptive layout initialization ---
    try:
        self._layout_mode = None  # track current responsive state
        self.root.bind("<Configure>", self.on_root_resize)
    except Exception:
        pass

    return home_frame
