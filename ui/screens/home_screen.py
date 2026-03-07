import tkinter as tk
from tkinter import ttk

from ui.ui_base import COLORS, ModernButton, ToggleSwitch, SectionFrame, Separator


def build_home_screen(app):
    """Original main UI assembled as the Home screen."""
    self = app
    
    # Track server group buttons for highlighting
    self.server_group_buttons = {}

    home_frame = tk.Frame(self.content_frame, bg=COLORS["bg_root"])
    self.screens["home"] = home_frame

    # Main split container: Sidebar (Profiles) | Content (Settings/Launch)
    game_split = tk.Frame(home_frame, bg=COLORS["bg_root"])
    game_split.pack(fill="both", expand=True)

    # --- Sidebar (Left) ---
    sidebar = tk.Frame(game_split, bg=COLORS["bg_panel"], width=300)
    sidebar.pack(side="left", fill="y")
    sidebar.pack_propagate(False)

    # Sidebar Header
    sidebar_header = tk.Frame(sidebar, bg=COLORS["bg_panel"])
    sidebar_header.pack(fill="x", padx=15, pady=(20, 15))

    tk.Label(
        sidebar_header,
        text="Profiles",
        font=("Segoe UI", 18, "bold"),
        bg=COLORS["bg_panel"],
        fg=COLORS["fg_text"]
    ).pack(side="left")

    # E710 = Add icon
    ModernButton(
        sidebar_header,
        COLORS["accent"],
        COLORS["accent_hover"],
        text="\uE710",
        width=3,
        font=("Segoe Fluent Icons", 10),
        command=self.add_profile,
        tooltip="Создать новый профиль",
    ).pack(side="right")

    # Group Switcher (Top of Sidebar)
    switcher_frame = tk.Frame(sidebar, bg=COLORS["bg_panel"])
    switcher_frame.pack(fill="x", padx=10, pady=(0, 10))

    def _switch_server_group(group_name):
        if self.server_group == group_name:
            return
        
        # Switch to new group
        self.server_group = group_name
        self.servers = self.server_groups.get(group_name, [])
        
        # Reset server selection
        if self.servers:
            self.server_var.set(self.servers[0].name)
        else:
            self.server_var.set("")

        self.save_data()
        self.refresh_list()
        self.refresh_server_list()
        
        # Update group buttons highlighting
        _update_group_buttons_sidebar()
        
        # Update Slayer visibility in footer (Cormyr only)
        if hasattr(self, 'status_bar_comp'):
             self.status_bar_comp.set_slayer_visibility(group_name != 'siala')

    def _update_group_buttons_sidebar():
        """Update visual state of sidebar group toggle buttons."""
        for grp, btn in self.server_group_buttons.items():
            if grp == self.server_group:
                btn.configure(bg=COLORS["accent"], fg=COLORS["text_dark"])
                btn.bg_color = COLORS["accent"]
                btn._color_key = "accent"
            else:
                btn.configure(bg=COLORS["bg_panel"], fg=COLORS["fg_text"])
                btn.bg_color = COLORS["bg_panel"]
                btn._color_key = "bg_panel"

    self._switch_server_group = _switch_server_group
    self._update_group_buttons = _update_group_buttons_sidebar

    btn_siala = ModernButton(
        switcher_frame,
        COLORS["accent"] if getattr(self, 'server_group', 'siala') == 'siala' else COLORS["bg_panel"],
        COLORS["accent_hover"],
        text="Siala",
        font=("Segoe UI", 9),
        width=12,
        command=lambda: _switch_server_group("siala"),
        tooltip="Switch to Siala servers",
    )
    btn_siala.pack(side="left", padx=(0, 5), expand=True, fill="x")
    self.server_group_buttons["siala"] = btn_siala
    
    btn_cormyr = ModernButton(
        switcher_frame,
        COLORS["accent"] if getattr(self, 'server_group', 'siala') == 'cormyr' else COLORS["bg_panel"],
        COLORS["accent_hover"],
        text="Cormyr",
        font=("Segoe UI", 9),
        width=12,
        command=lambda: _switch_server_group("cormyr"),
        tooltip="Switch to Cormyr servers",
    )
    btn_cormyr.pack(side="left", expand=True, fill="x")
    self.server_group_buttons["cormyr"] = btn_cormyr
    
    # Vertical separator between sidebar and content
    Separator(game_split, orient="vertical", color=COLORS["border"], thickness=1, padding=0).pack(side="left", fill="y")

    accounts_wrap = tk.Frame(sidebar, bg=COLORS["bg_panel"])
    accounts_wrap.pack(fill="both", expand=True, padx=(10, 1), pady=(0, 10))
    
    self.lb = ttk.Treeview(
        accounts_wrap,
        selectmode="extended",
        show="tree",
        style="ProfileList.Treeview"
    )
    self.lb.column("#0", width=250, stretch=True, anchor="w")
    self.lb.heading("#0", text="Profile", anchor="w")

    scrollbar = ttk.Scrollbar(accounts_wrap, orient="vertical", command=self.lb.yview)
    self.lb.configure(yscrollcommand=scrollbar.set)
    self.lb.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    # Inline action buttons
    self.inline_action_frame = tk.Frame(self.lb, bg=COLORS["bg_panel"], bd=0)
    self.inline_action_frame.place_forget()

    self.btn_edit_profile = ModernButton(
        self.inline_action_frame, COLORS["bg_panel"], COLORS["bg_input"],
        text="\uE70F", width=3, fg=COLORS["accent"], font=("Segoe Fluent Icons", 10),
        command=self._inline_edit_profile, tooltip="Редактировать выбранный профиль",
    )
    self.btn_edit_profile.pack(side="left", padx=(0, 6))

    self.btn_delete_profile_top = ModernButton(
        self.inline_action_frame, COLORS["bg_panel"], COLORS["bg_input"],
        text="\uE74D", width=3, fg=COLORS["danger"], font=("Segoe Fluent Icons", 10),
        command=self._inline_delete_profile, tooltip="Удалить выбранный профиль",
    )
    self.btn_delete_profile_top.pack(side="left")

    self.lb.bind("<<TreeviewSelect>>", self.on_select)
    self.lb.bind("<Button-1>", self.on_drag_start)
    self.lb.bind("<ButtonRelease-1>", self.on_drag_drop)
    self.lb.bind("<Button-2>", self.on_middle_click)
    self.lb.bind("<Button-3>", self.on_right_click)
    self.lb.bind("<Motion>", self.on_profile_list_motion)
    self.lb.bind("<Leave>", self.on_profile_list_leave)
    self.lb.bind("<FocusOut>", lambda e: self.hide_inline_actions())
    self.lb.bind("<MouseWheel>", self.on_profile_list_scroll)

    # --- Content Area ---
    content = tk.Frame(game_split, bg=COLORS["bg_root"])
    content.pack(side="left", fill="both", expand=True, padx=30, pady=20)
    self.home_content = content

    header_row = tk.Frame(content, bg=COLORS["bg_root"])
    header_row.pack(fill="x", pady=(0, 5))
    
    self.header_lbl = tk.Label(
        header_row, text="Select Profile", bg=COLORS["bg_root"],
        fg=COLORS["fg_text"], font=("Segoe UI", 26, "bold"),
    )
    self.header_lbl.pack(side="left")
    
    self.cat_lbl = tk.Label(
        content, text="", bg=COLORS["bg_root"], fg=COLORS["accent"], font=("Segoe UI", 10),
    )
    self.cat_lbl.pack(anchor="w")

    self.info_frame = tk.Frame(content, bg=COLORS["bg_root"])
    self.info_frame.pack(fill="x", pady=10)

    f_key = tk.Frame(self.info_frame, bg=COLORS["bg_root"])
    f_key.pack(fill="x", pady=4)

    tk.Label(f_key, text="CD Key:", bg=COLORS["bg_root"], fg=COLORS["fg_dim"], font=("Segoe UI", 9)).pack(anchor="w")
    key_cont = tk.Frame(f_key, bg=COLORS["bg_root"])
    key_cont.pack(fill="x", pady=(2, 0))

    self.info_cdkey = tk.Entry(
        key_cont, bg=COLORS["bg_root"], fg=COLORS["fg_text"], relief="flat",
        readonlybackground=COLORS["bg_root"], font=("Segoe UI Mono", 10),
    )
    self.info_cdkey.pack(side="left", fill="x", expand=True)
    self.info_cdkey.config(state="readonly")

    ModernButton(
        key_cont, COLORS["bg_root"], COLORS["bg_panel"], text="\uE7B3", width=3,
        fg=COLORS["accent"], font=("Segoe Fluent Icons", 10), command=self.toggle_key_visibility,
        tooltip="Show/Hide CD Key",
    ).pack(side="right", padx=5)

    def info_row(label: str):
        f = tk.Frame(self.info_frame, bg=COLORS["bg_root"])
        f.pack(fill="x", pady=4)
        tk.Label(f, text=label, bg=COLORS["bg_root"], fg=COLORS["fg_dim"], font=("Segoe UI", 9)).pack(anchor="w")
        e = tk.Entry(
            f, bg=COLORS["bg_root"], fg=COLORS["fg_text"], relief="flat",
            readonlybackground=COLORS["bg_root"], font=("Segoe UI Mono", 10),
        )
        e.pack(fill="x", pady=(2, 0))
        e.config(state="readonly")
        return e

    self.info_login = info_row("Login:")

    bottom_actions = tk.Frame(content, bg=COLORS["bg_root"])
    bottom_actions.pack(side="bottom", fill="x", pady=(5, 0))
    
    self.btn_play = ModernButton(
        bottom_actions, COLORS["accent"], COLORS["accent_hover"], text="\uE768", width=4,
        font=("Segoe Fluent Icons", 14), command=self.launch_selected, tooltip="Запустить выбранные профили",
    )
    self.btn_play.pack(side="left", padx=(0, 6))
    
    self.lbl_selected_count = tk.Label(
        bottom_actions, text="", bg=COLORS["bg_root"], fg=COLORS["accent"], font=("Segoe UI", 10, "bold")
    )
    self.lbl_selected_count.pack(side="left", padx=(0, 10))

    self.ctrl_frame = tk.Frame(bottom_actions, bg=COLORS["bg_root"])
    self.ctrl_frame.pack(side="left")
    
    self.btn_restart = ModernButton(
        self.ctrl_frame, COLORS["accent"], COLORS["accent_hover"], text="\uE72C", width=4,
        font=("Segoe Fluent Icons", 14), command=self.restart_game, tooltip="Перезапустить игру",
    )
    self.btn_restart.pack(side="left", padx=(0, 6))
    
    self.btn_close = ModernButton(
        self.ctrl_frame, COLORS["accent"], COLORS["accent_hover"], text="\uE8BB", width=4,
        font=("Segoe Fluent Icons", 14), command=self.close_game, tooltip="Безопасный выход из игры",
    )
    self.btn_close.pack(side="left")

    srv_frame = tk.Frame(content, bg=COLORS["bg_root"])
    srv_frame.pack(side="bottom", fill="x", pady=(0, 10))

    srv_header = tk.Frame(srv_frame, bg=COLORS["bg_root"])
    srv_header.pack(fill="x")
    
    tk.Label(srv_header, text="Servers", bg=COLORS["bg_root"], fg=COLORS["accent"], font=("Segoe UI", 11, "bold")).pack(side="left")
    
    def _open_server_management():
        from ui.dialogs import ServerManagementDialog
        def on_save(new_servers):
            self.servers = new_servers
            self.save_data()
            _create_server_buttons()
        ServerManagementDialog(self.root, self.servers, on_save)
    
    ModernButton(
        srv_header, COLORS["accent"], COLORS["accent_hover"], text="\uE710", width=3,
        font=("Segoe Fluent Icons", 10), command=lambda: (self.add_server(), _create_server_buttons()), tooltip="Add new server",
    ).pack(side="left", padx=(10, 0))
    
    ModernButton(
        srv_header, COLORS["bg_panel"], COLORS["border"], text="\uE70F", width=3,
        font=("Segoe Fluent Icons", 10), command=_open_server_management, tooltip="Manage servers (add/edit/delete)",
    ).pack(side="left", padx=(5, 0))
    
    auto_connect_frame = tk.Frame(srv_header, bg=COLORS["bg_root"])
    auto_connect_frame.pack(side="left", padx=(15, 0))
    
    tk.Label(auto_connect_frame, text="Direct:", bg=COLORS["bg_root"], fg=COLORS["fg_dim"], font=("Segoe UI", 9)).pack(side="left")
    
    auto_toggle = ToggleSwitch(auto_connect_frame, variable=self.use_server_var, command=self.save_data)
    auto_toggle.pack(side="left", padx=(5, 0))

    self.status_lbl = tk.Label(srv_header, text="", bg=COLORS["bg_root"], fg=COLORS["fg_dim"], font=("Segoe UI", 9))
    self.status_lbl.pack(side="right", padx=(5, 0))

    srv_scroll_frame = tk.Frame(srv_frame, bg=COLORS["bg_root"])
    srv_scroll_frame.pack(fill="x", pady=(5, 5))
    
    srv_canvas = tk.Canvas(srv_scroll_frame, bg=COLORS["bg_root"], highlightthickness=0, height=80)
    srv_canvas.pack(side="left", fill="both", expand=True)
    
    srv_scrollbar = ttk.Scrollbar(srv_scroll_frame, orient="vertical", command=srv_canvas.yview)
    srv_canvas.configure(yscrollcommand=srv_scrollbar.set)
    
    self.srv_buttons_frame = tk.Frame(srv_canvas, bg=COLORS["bg_root"])
    canvas_window = srv_canvas.create_window((0, 0), window=self.srv_buttons_frame, anchor="nw")
    
    def _on_srv_frame_configure(e):
        srv_canvas.configure(scrollregion=srv_canvas.bbox("all"))
        if self.srv_buttons_frame.winfo_reqheight() > srv_canvas.winfo_height():
            srv_scrollbar.pack(side="right", fill="y")
        else:
            srv_scrollbar.pack_forget()
    
    def _on_srv_canvas_configure(e):
        srv_canvas.itemconfig(canvas_window, width=e.width)
    
    self.srv_buttons_frame.bind("<Configure>", _on_srv_frame_configure)
    srv_canvas.bind("<Configure>", _on_srv_canvas_configure)
    
    def _srv_mousewheel(e):
        srv_canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
    srv_canvas.bind("<MouseWheel>", _srv_mousewheel)
    self.srv_buttons_frame.bind("<MouseWheel>", _srv_mousewheel)
    
    self.server_buttons_map = {}

    def _create_server_buttons():
        """Recreate server buttons when list changes."""
        self.server_buttons_map.clear()
        for widget in self.srv_buttons_frame.winfo_children():
            widget.destroy()
        
        COLS = 2
        group = getattr(self, 'server_group', '').lower()
        display_servers = [s for s in self.servers if group in s.name.lower()] or self.servers

        for i, s in enumerate(display_servers):
            if i % COLS == 0:
                row_f = tk.Frame(self.srv_buttons_frame, bg=COLORS["bg_root"])
                row_f.pack(side="top", fill="x", pady=2)
            
            srv_name = s.name
            def make_cmd(name=srv_name):
                def cmd():
                    self.server_var.set(name)
                    self.use_server_var.set(True)
                    self._on_server_selected()
                    _update_server_button_styles()
                return cmd
            
            btn = ModernButton(
                row_f, COLORS["bg_panel"], COLORS["accent"], text=srv_name, font=("Segoe UI", 9),
                pady=4, command=make_cmd(), tooltip=f"Connect to {srv_name}",
            )
            btn.pack(side="left", fill="x", expand=True, padx=2)
            self.server_buttons_map[srv_name] = btn
        _update_server_button_styles()

    def _update_server_button_styles():
        """Highlight currently selected server button."""
        current = self.server_var.get()
        for srv_name, btn in self.server_buttons_map.items():
            if srv_name == current:
                btn.configure(bg=COLORS["accent"], fg=COLORS["text_dark"])
                btn.bg_color = COLORS["accent"]
                btn._color_key = "accent"
            else:
                btn.configure(bg=COLORS["bg_panel"], fg=COLORS["fg_text"])
                btn.bg_color = COLORS["bg_panel"]
                btn._color_key = "bg_panel"
    
    self._create_server_buttons = _create_server_buttons
    self._update_server_button_styles = _update_server_button_styles
    
    _create_server_buttons()
    self.use_server_var.set(True)

    try:
        self._layout_mode = None
        self.root.bind("<Configure>", self.on_root_resize)
    except Exception:
        pass

    return home_frame
