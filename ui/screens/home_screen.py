import tkinter as tk
from tkinter import ttk

from ui.ui_base import COLORS, ModernButton, ToggleSwitch, SectionFrame, Separator


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

    # Sidebar header with accent underline
    accounts_header = tk.Frame(sidebar, bg=COLORS["bg_panel"])
    accounts_header.pack(fill="x", padx=15, pady=(20, 5))
    
    header_left = tk.Frame(accounts_header, bg=COLORS["bg_panel"])
    header_left.pack(side="left", fill="x", expand=True)
    
    tk.Label(
        header_left,
        text="ACCOUNTS",
        bg=COLORS["bg_panel"],
        fg=COLORS["accent"],
        font=("Segoe UI", 11, "bold"),
    ).pack(side="left")
    
    # E710 = Add icon from Segoe Fluent Icons
    self.btn_add_profile_side = ModernButton(
        accounts_header,
        COLORS["accent"],
        COLORS["accent_hover"],
        text="\uE710",
        width=3,
        font=("Segoe Fluent Icons", 10),
        command=self.add_profile,
        tooltip="Добавить профиль",
    )
    self.btn_add_profile_side.pack(side="right")
    
    # Header underline
    tk.Frame(sidebar, bg=COLORS["accent"], height=2).pack(fill="x", padx=15, pady=(5, 15))

    # Vertical separator between sidebar and content
    Separator(game_split, orient="vertical", color=COLORS["border"], thickness=1, padding=0).pack(side="left", fill="y")

    accounts_wrap = tk.Frame(sidebar, bg=COLORS["bg_panel"])
    accounts_wrap.pack(fill="both", expand=True, padx=10, pady=(0, 10))
    self.lb = tk.Listbox(
        accounts_wrap,
        bg=COLORS["bg_panel"],
        fg=COLORS["fg_text"],
        selectbackground=COLORS["accent"],
        selectforeground=COLORS["bg_panel"],
        bd=0,
        highlightthickness=0,
        font=("Segoe UI", 11),
        activestyle="none",
        exportselection=False,
    )
    self.lb.pack(side="left", fill="both", expand=True)

    # Inline action buttons
    self.inline_action_frame = tk.Frame(self.lb, bg=COLORS["bg_panel"], bd=0)
    self.inline_action_frame.place_forget()

    # Edit icon - E70F (Edit)
    self.btn_edit_profile = ModernButton(
        self.inline_action_frame,
        COLORS["bg_panel"],
        COLORS["bg_input"],
        text="\uE70F",
        width=3,
        fg=COLORS["accent"],
        font=("Segoe Fluent Icons", 10),
        command=self._inline_edit_profile,
        tooltip="Редактировать выбранный профиль",
    )
    self.btn_edit_profile.pack(side="left", padx=(0, 6))

    # Delete icon - E74D (Delete)
    self.btn_delete_profile_top = ModernButton(
        self.inline_action_frame,
        COLORS["bg_panel"],
        COLORS["bg_input"],
        text="\uE74D",
        width=3,
        fg=COLORS["danger"],
        font=("Segoe Fluent Icons", 10),
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
    # Reduced padding to prevent clipping on small screens/high scaling
    content.pack(side="left", fill="both", expand=True, padx=30, pady=20)
    self.home_content = content

    # Header row with title and server group switcher
    header_row = tk.Frame(content, bg=COLORS["bg_root"])
    header_row.pack(fill="x", pady=(0, 5))
    
    self.header_lbl = tk.Label(
        header_row,
        text="Select Profile",
        bg=COLORS["bg_root"],
        fg=COLORS["fg_text"],
        font=("Segoe UI", 26, "bold"),
    )
    self.header_lbl.pack(side="left")
    
    # Server Group Switcher (right side of header)
    group_frame = tk.Frame(header_row, bg=COLORS["bg_root"])
    group_frame.pack(side="right")
    
    def _switch_server_group(group_name):
        """Switch to a different server group."""
        if self.server_group == group_name:
            return
        # Save current group's servers
        self.server_groups[self.server_group] = self.servers
        # Switch to new group
        self.server_group = group_name
        self.servers = self.server_groups.get(group_name, [])
        # Reset server selection
        if self.servers:
            self.server_var.set(self.servers[0]["name"])
        else:
            self.server_var.set("")
        # Save group to current profile
        if self.current_profile:
            self.current_profile["server_group"] = group_name
            self.current_profile["server"] = self.server_var.get()
        # Update UI
        _update_group_buttons()
        self._create_server_buttons()
        # Trigger ping for new servers
        self.root.after(100, self.server_manager.ping_all_servers)
        self.save_data()
    
    def _update_group_buttons():
        """Update visual state of group toggle buttons."""
        for grp, btn in self.server_group_buttons.items():
            if grp == self.server_group:
                btn.configure(bg=COLORS["accent"], fg=COLORS["text_dark"])
                btn.bg_color = COLORS["accent"]
                btn._color_key = "accent"  # Update semantic key for theme switching
            else:
                btn.configure(bg=COLORS["bg_panel"], fg=COLORS["fg_text"])
                btn.bg_color = COLORS["bg_panel"]
                btn._color_key = "bg_panel"  # Update semantic key for theme switching
    
    self.server_group_buttons = {}
    
    btn_siala = ModernButton(
        group_frame,
        COLORS["accent"] if getattr(self, 'server_group', 'siala') == 'siala' else COLORS["bg_panel"],
        COLORS["accent_hover"],
        text="Siala",
        font=("Segoe UI", 9),
        width=8,
        command=lambda: _switch_server_group("siala"),
        tooltip="Switch to Siala servers",
    )
    btn_siala.pack(side="left", padx=(0, 2))
    self.server_group_buttons["siala"] = btn_siala
    
    btn_cormyr = ModernButton(
        group_frame,
        COLORS["accent"] if getattr(self, 'server_group', 'siala') == 'cormyr' else COLORS["bg_panel"],
        COLORS["accent_hover"],
        text="Cormyr",
        font=("Segoe UI", 9),
        width=8,
        command=lambda: _switch_server_group("cormyr"),
        tooltip="Switch to Cormyr servers",
    )
    btn_cormyr.pack(side="left")
    self.server_group_buttons["cormyr"] = btn_cormyr
    
    self._update_group_buttons = _update_group_buttons
    
    # Update group button styles based on current group
    self.root.after(100, _update_group_buttons)
    
    self.cat_lbl = tk.Label(
        content,
        text="",
        bg=COLORS["bg_root"],
        fg=COLORS["accent"],
        font=("Segoe UI", 10),
    )
    self.cat_lbl.pack(anchor="w")

    self.info_frame = tk.Frame(content, bg=COLORS["bg_root"])
    self.info_frame.pack(fill="x", pady=10) # Reduced pady

    f_key = tk.Frame(self.info_frame, bg=COLORS["bg_root"])
    f_key.pack(fill="x", pady=4) # Reduced pady

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

    # E7B3 = View/Eye icon
    ModernButton(
        key_cont,
        COLORS["bg_root"],
        COLORS["bg_panel"],
        text="\uE7B3",
        width=3,
        fg=COLORS["accent"],
        font=("Segoe Fluent Icons", 10),
        command=self.toggle_key_visibility,
        tooltip="Show/Hide CD Key",
    ).pack(side="right", padx=5)

    def info_row(label: str):
        f = tk.Frame(self.info_frame, bg=COLORS["bg_root"])
        f.pack(fill="x", pady=4) # Reduced pady
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

    # Spacer removed, relies on top/bottom packing

    # Bottom action bar with Segoe Fluent Icons
    bottom_actions = tk.Frame(content, bg=COLORS["bg_root"])
    bottom_actions.pack(side="bottom", fill="x", pady=(5, 0)) # Reduced pady
    
    # E768 = Play icon
    self.btn_play = ModernButton(
        bottom_actions,
        COLORS["accent"],
        COLORS["accent_hover"],
        text="\uE768",
        width=4,
        font=("Segoe Fluent Icons", 14),
        command=self.launch_game,
        tooltip="Запустить игру",
    )
    self.btn_play.pack(side="left", padx=(0, 6))
    self.ctrl_frame = tk.Frame(bottom_actions, bg=COLORS["bg_root"])
    self.ctrl_frame.pack(side="left")
    
    # E72C = Sync/Restart icon
    self.btn_restart = ModernButton(
        self.ctrl_frame,
        COLORS["accent"],
        COLORS["accent_hover"],
        text="\uE72C",
        width=4,
        font=("Segoe Fluent Icons", 14),
        command=self.restart_game,
        tooltip="Перезапустить игру",
    )
    self.btn_restart.pack(side="left", padx=(0, 6))
    
    # E8BB = Close icon (same as titlebar)
    self.btn_close = ModernButton(
        self.ctrl_frame,
        COLORS["accent"],
        COLORS["accent_hover"],
        text="\uE8BB",
        width=4,
        font=("Segoe Fluent Icons", 14),
        command=self.close_game,
        tooltip="Безопасный выход из игры",
    )
    self.btn_close.pack(side="left")

    # Server controls - clickable buttons instead of dropdown
    srv_frame = tk.Frame(content, bg=COLORS["bg_root"])
    srv_frame.pack(side="bottom", fill="x", pady=(0, 10)) # Reduced pady

    # Header row with label, add/edit buttons, and status
    srv_header = tk.Frame(srv_frame, bg=COLORS["bg_root"])
    srv_header.pack(fill="x")
    
    tk.Label(
        srv_header,
        text="Servers",
        bg=COLORS["bg_root"],
        fg=COLORS["accent"],
        font=("Segoe UI", 11, "bold"),
    ).pack(side="left")
    
    # Add and Edit buttons next to label
    def _open_server_management():
        from ui.dialogs import ServerManagementDialog
        def on_save(new_servers):
            self.servers = new_servers
            self.save_data()
            _create_server_buttons()
        ServerManagementDialog(self.root, self.servers, on_save)
    
    # E710 = Add icon
    ModernButton(
        srv_header,
        COLORS["accent"],
        COLORS["accent_hover"],
        text="\uE710",
        width=3,
        font=("Segoe Fluent Icons", 10),
        command=lambda: (self.add_server(), _create_server_buttons()),
        tooltip="Add new server",
    ).pack(side="left", padx=(10, 0))
    
    # E70F = Edit icon
    ModernButton(
        srv_header,
        COLORS["bg_panel"],
        COLORS["border"],
        text="\uE70F",
        width=3,
        font=("Segoe Fluent Icons", 10),
        command=_open_server_management,
        tooltip="Manage servers (add/edit/delete)",
    ).pack(side="left", padx=(5, 0))
    
    # Auto-connect toggle
    auto_connect_frame = tk.Frame(srv_header, bg=COLORS["bg_root"])
    auto_connect_frame.pack(side="left", padx=(15, 0))
    
    tk.Label(
        auto_connect_frame,
        text="Direct:",
        bg=COLORS["bg_root"],
        fg=COLORS["fg_dim"],
        font=("Segoe UI", 9),
    ).pack(side="left")
    
    def _on_auto_connect_toggle():
        self.save_data()
    
    from ui.ui_base import ToggleSwitch
    auto_toggle = ToggleSwitch(auto_connect_frame, variable=self.use_server_var, command=_on_auto_connect_toggle)
    auto_toggle.pack(side="left", padx=(5, 0))

    
    self.status_lbl = tk.Label(
        srv_header,
        text="",
        bg=COLORS["bg_root"],
        fg=COLORS["fg_dim"],
        font=("Segoe UI", 9),
    )
    self.status_lbl.pack(side="right", padx=(5, 0))

    # Manual Ping Refresh Button
    ModernButton(
        srv_header,
        COLORS["bg_root"],
        COLORS["bg_panel"],
        text="\uE72C",  # Refresh icon
        width=3,
        fg=COLORS["accent"],
        font=("Segoe Fluent Icons", 9),
        command=self.server_manager.ping_all_servers,
        tooltip="Refresh Server Status",
    ).pack(side="right")

    # Server buttons container with scrolling if many servers
    srv_scroll_frame = tk.Frame(srv_frame, bg=COLORS["bg_root"])
    srv_scroll_frame.pack(fill="x", pady=(5, 5))
    
    # Create canvas for scrolling
    srv_canvas = tk.Canvas(srv_scroll_frame, bg=COLORS["bg_root"], highlightthickness=0, height=80)
    srv_canvas.pack(side="left", fill="both", expand=True)
    
    # Scrollbar (hidden by default, appears if needed)
    srv_scrollbar = ttk.Scrollbar(srv_scroll_frame, orient="vertical", command=srv_canvas.yview)
    srv_canvas.configure(yscrollcommand=srv_scrollbar.set)
    
    self.srv_buttons_frame = tk.Frame(srv_canvas, bg=COLORS["bg_root"])
    canvas_window = srv_canvas.create_window((0, 0), window=self.srv_buttons_frame, anchor="nw")
    
    def _on_srv_frame_configure(e):
        srv_canvas.configure(scrollregion=srv_canvas.bbox("all"))
        # Show scrollbar only if content is taller than canvas
        if self.srv_buttons_frame.winfo_reqheight() > srv_canvas.winfo_height():
            srv_scrollbar.pack(side="right", fill="y")
        else:
            srv_scrollbar.pack_forget()
    
    def _on_srv_canvas_configure(e):
        srv_canvas.itemconfig(canvas_window, width=e.width)
    
    self.srv_buttons_frame.bind("<Configure>", _on_srv_frame_configure)
    srv_canvas.bind("<Configure>", _on_srv_canvas_configure)
    
    # Mouse wheel scrolling
    def _srv_mousewheel(e):
        srv_canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
    srv_canvas.bind("<MouseWheel>", _srv_mousewheel)
    self.srv_buttons_frame.bind("<MouseWheel>", _srv_mousewheel)
    
    # Keep server_var for compatibility but set via buttons
    self.srv_ctrl = tk.Frame(srv_frame, bg=COLORS["bg_root"])  # Hidden, for toggle_server_ui
    
    self.server_buttons_map = {}
    self.server_latencies = {}  # Store latencies for best/worst calculation

    def _create_server_buttons():
        """Recreate server buttons when list changes."""
        self.server_buttons_map.clear()
        self.server_latencies.clear()
        
        for widget in self.srv_buttons_frame.winfo_children():
            widget.destroy()
        
        current_row_frame = None
        COLS = 2
        
        
        # Heuristic filtering: if group is siala/cormyr, filter by name to prevent cross-contamination
        # caused by bad imports
        display_servers = []
        group = getattr(self, 'server_group', '').lower()
        
        if group in ['siala', 'cormyr']:
            filtered = [s for s in self.servers if group in s["name"].lower()]
            # Only use filtered list if it's not empty, otherwise fallback to show all
            if filtered:
                display_servers = filtered
            else:
                display_servers = self.servers
        else:
            display_servers = self.servers

        for i, s in enumerate(display_servers):
            # Create new row frame every COLS buttons
            if i % COLS == 0:
                current_row_frame = tk.Frame(self.srv_buttons_frame, bg=COLORS["bg_root"])
                current_row_frame.pack(side="top", fill="x", pady=2)
            
            srv_name = s["name"]
            
            def make_cmd(name=srv_name):
                def cmd():
                    self.server_var.set(name)
                    self.use_server_var.set(True)
                    self._on_server_selected()
                    _update_server_button_styles()
                return cmd
            
            # Initial text is just name
            btn = ModernButton(
                current_row_frame,
                COLORS["bg_panel"],
                COLORS["accent"],
                text=srv_name,
                font=("Segoe UI", 9),
                pady=4,
                command=make_cmd(),
                tooltip=f"Connect to {srv_name}",
            )
            # Expand=True makes buttons share width equally in the row
            btn.pack(side="left", fill="x", expand=True, padx=2)
            btn._server_name = srv_name
            self.server_buttons_map[srv_name] = btn
        
        _update_server_button_styles()

    def update_server_latency(name: str, ms: int):
        """Update button text with ping time and best/worst indicators."""
        btn = self.server_buttons_map.get(name)
        if not btn:
            return
        
        # Store latency
        self.server_latencies[name] = ms
        
        # Calculate best and worst in current group
        valid_latencies = {n: l for n, l in self.server_latencies.items() if l > 0}
        best_name = min(valid_latencies, key=valid_latencies.get) if valid_latencies else None
        worst_name = max(valid_latencies, key=valid_latencies.get) if valid_latencies else None
        
        # Update all buttons with indicators
        for srv_name, srv_btn in self.server_buttons_map.items():
            lat = self.server_latencies.get(srv_name)
            if lat is None:
                continue
            
            if lat < 0:
                ping_text = f"{srv_name} (❌ Off)"
            elif srv_name == best_name and len(valid_latencies) > 1:
                ping_text = f"{srv_name} (⚡ {lat}ms)"
            elif srv_name == worst_name and len(valid_latencies) > 1:
                ping_text = f"{srv_name} (🐢 {lat}ms)"
            else:
                ping_text = f"{srv_name} (📡 {lat}ms)"
            
            if srv_btn.cget("text") != ping_text:
                srv_btn.config(text=ping_text)

    self.update_server_latency = update_server_latency

    def _update_server_button_styles():
        """Highlight currently selected server button."""
        current = self.server_var.get()
        for srv_name, btn in self.server_buttons_map.items():
            if srv_name == current:
                btn.configure(bg=COLORS["accent"], fg=COLORS["text_dark"])
                btn.bg_color = COLORS["accent"]
                btn._color_key = "accent"  # Update semantic key for theme switching
            else:
                btn.configure(bg=COLORS["bg_panel"], fg=COLORS["fg_text"])
                btn.bg_color = COLORS["bg_panel"]
                btn._color_key = "bg_panel"  # Update semantic key for theme switching
    
    self._create_server_buttons = _create_server_buttons
    self._update_server_button_styles = _update_server_button_styles
    
    _create_server_buttons()
    
    # Trigger initial ping and start auto-refresh every 60 seconds
    self.root.after(500, self.server_manager.ping_all_servers)
    self.root.after(1000, self.server_manager.start_auto_ping)

    # Keep use_server_var always True now (auto-connect when server selected)
    self.use_server_var.set(True)

    # Pack spacer REMOVED - relying on natural side=top vs side=bottom separation
    # This avoids conflict where spacer consumes space needed by auto-expanding bottom frames
    
    # Пакуем блок кнопок управления всегда (статусы меняются логикой)

    # Удалён старый блок запуска из панели профиля
    # --- Adaptive layout initialization ---
    try:
        self._layout_mode = None  # track current responsive state
        self.root.bind("<Configure>", self.on_root_resize)
    except Exception:
        pass

    return home_frame
