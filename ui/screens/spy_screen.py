import tkinter as tk
from tkinter import ttk, messagebox
from ui.ui_base import COLORS, ModernButton, ToggleSwitch, SectionFrame

def build_spy_screen(app):
    """Screen for keyword tracking and Discord notifications."""
    self = app

    spy_frame = tk.Frame(self.content_frame, bg=COLORS["bg_root"])
    self.screens["spy"] = spy_frame

    # Scrollable container
    canvas = tk.Canvas(spy_frame, bg=COLORS["bg_root"], highlightthickness=0, bd=0)
    scrollbar = ttk.Scrollbar(spy_frame, orient="vertical", command=canvas.yview)
    scrollable_frame = tk.Frame(canvas, bg=COLORS["bg_root"])

    # Scroll region update
    def _update_scroll_region(e=None):
        canvas.configure(scrollregion=canvas.bbox("all"))

    scrollable_frame.bind("<Configure>", _update_scroll_region)

    canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    def _on_canvas_configure(event):
        canvas.itemconfig(canvas_window, width=event.width)
    canvas.bind("<Configure>", _on_canvas_configure)

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    # Mousewheel support
    def _on_mousewheel(event):
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def bind_mousewheel(widget):
        widget.bind("<MouseWheel>", _on_mousewheel)
        for child in widget.winfo_children():
            bind_mousewheel(child)

    main = tk.Frame(scrollable_frame, bg=COLORS["bg_root"])
    main.pack(fill="both", expand=True, padx=40, pady=20)

    # Header
    header = tk.Frame(main, bg=COLORS["bg_root"])
    header.pack(fill="x", pady=(0, 20))

    tk.Label(
        header,
        text="Spy Mode",
        font=("Segoe UI", 24, "bold"),
        bg=COLORS["bg_root"],
        fg=COLORS["fg_text"]
    ).pack(side="left")

    # Spy Toggle
    enable_frame = tk.Frame(header, bg=COLORS["bg_root"])
    enable_frame.pack(side="right")
    
    tk.Label(enable_frame, text="Enable/Disable:", bg=COLORS["bg_root"], fg=COLORS["fg_dim"]).pack(side="left", padx=(0, 10))
    
    def _on_spy_toggle():
        spy_on = self.log_monitor_state.spy_enabled_var.get()
        if hasattr(self, 'log_monitor_manager'):
            self.log_monitor_manager.toggle_spy_enabled(force_state=spy_on)
    
    spy_toggle = ToggleSwitch(enable_frame, variable=self.log_monitor_state.spy_enabled_var, command=_on_spy_toggle)
    spy_toggle.pack(side="left")

    # --- Log File Path ---
    path_frame = SectionFrame(main, text="Log File")
    path_frame.pack(fill="x", pady=(0, 15))
    path_inner = tk.Frame(path_frame, bg=COLORS["bg_root"])
    path_inner.pack(fill="x", padx=15, pady=10)

    tk.Entry(path_inner, textvariable=self.log_monitor_state.log_path_var, width=60, bg=COLORS["bg_input"], fg=COLORS["fg_text"], relief="flat").pack(side="left", fill="x", expand=True, padx=(0, 10))
    ModernButton(path_inner, COLORS["bg_input"], COLORS["border"], text="Browse", width=10, command=self._browse_log_path).pack(side="left")

    # --- Webhooks Section ---
    webhooks_section = SectionFrame(main, text="Discord Webhooks")
    webhooks_section.pack(fill="x", pady=(0, 15))
    wh_container = tk.Frame(webhooks_section, bg=COLORS["bg_root"])
    wh_container.pack(fill="x", padx=15, pady=8)

    self.wh_list_frame = tk.Frame(wh_container, bg=COLORS["bg_root"])
    self.wh_list_frame.pack(fill="x")

    def _test_webhook(url, name="Webhook"):
        if not url or not (isinstance(url, str) and url.startswith("http")):
            messagebox.showerror("Error", "Invalid Webhook URL")
            return
        try:
            import json
            from urllib import request
            payload = json.dumps({
                "username": "Spy Bot [TEST]",
                "content": f"✅ Webhook **{name}** is working correctly!",
            }).encode("utf-8")
            headers = {"Content-Type": "application/json", "User-Agent": "1609Manager/1.0"}
            req = request.Request(url, data=payload, headers=headers, method="POST")
            with request.urlopen(req, timeout=5):
                messagebox.showinfo("Success", f"Test message sent to {name}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to send test message: {e}")

    def _render_webhooks():
        for widget in self.wh_list_frame.winfo_children():
            widget.destroy()
        
        webhooks = self.log_monitor_state.config.get("webhooks", [])
        cleaned_whs = []
        for i, wh in enumerate(webhooks):
            if isinstance(wh, str):
                wh = {"url": wh, "enabled": True, "name": f"Webhook {i+1}"}
            if isinstance(wh, dict):
                cleaned_whs.append(wh)
        
        self.log_monitor_state.config["webhooks"] = cleaned_whs
        if not cleaned_whs:
            tk.Label(self.wh_list_frame, text="No webhooks added yet.", bg=COLORS["bg_root"], fg=COLORS["fg_dim"]).pack(pady=10)
        else:
            for i, wh in enumerate(cleaned_whs):
                row = tk.Frame(self.wh_list_frame, bg=COLORS["bg_panel"], padx=10, pady=5)
                row.pack(fill="x", pady=2)

                wh_var = tk.BooleanVar(value=wh.get("enabled", True))
                def _make_toggle_cmd(idx=i, var=wh_var):
                    def cmd():
                        current_whs = self.log_monitor_state.config.get("webhooks", [])
                        if idx < len(current_whs):
                            current_whs[idx]["enabled"] = var.get()
                            self.log_monitor_manager._save_config()
                    return cmd
                
                ToggleSwitch(row, variable=wh_var, command=_make_toggle_cmd()).pack(side="left", padx=(0, 10))

                info_f = tk.Frame(row, bg=COLORS["bg_panel"])
                info_f.pack(side="left", fill="x", expand=True)
                w_name = wh.get("name", f"Webhook {i+1}")
                w_url = wh.get("url", "")
                tk.Label(info_f, text=w_name, bg=COLORS["bg_panel"], fg=COLORS["fg_text"], font=("Segoe UI", 10, "bold")).pack(anchor="w")
                url_snippet = w_url[:50] + "..." if len(w_url) > 50 else w_url
                tk.Label(info_f, text=url_snippet, bg=COLORS["bg_panel"], fg=COLORS["fg_dim"], font=("Segoe UI", 8)).pack(anchor="w")

                ModernButton(row, COLORS["bg_input"], COLORS["border"], text="Edit", width=6, command=lambda idx=i: _add_webhook_dialog(edit_idx=idx)).pack(side="left", padx=5)
                ModernButton(row, COLORS["bg_input"], COLORS["border"], text="Test", width=6, command=lambda u=w_url, n=w_name: _test_webhook(u, n)).pack(side="left", padx=5)
                
                def _make_del_cmd(idx=i):
                    def cmd():
                        if messagebox.askyesno("Confirm", "Delete this webhook?"):
                            current_whs = self.log_monitor_state.config.get("webhooks", [])
                            if idx < len(current_whs):
                                current_whs.pop(idx)
                                self.log_monitor_manager._save_config()
                                _render_webhooks()
                    return cmd
                ModernButton(row, COLORS["bg_input"], COLORS["danger"], text="Delete", width=6, command=_make_del_cmd()).pack(side="left")
        
        # Recalculate scroll region after rendering content
        self.root.after(10, _update_scroll_region)

    def _add_webhook_dialog(edit_idx=None):
        is_edit = edit_idx is not None
        current_webhooks = self.log_monitor_state.config.get("webhooks", [])
        if is_edit and edit_idx < len(current_webhooks):
            wh_data = current_webhooks[edit_idx]
            initial_name = wh_data.get("name", "")
            initial_url = wh_data.get("url", "")
        else:
            initial_name = f"Webhook {len(current_webhooks)+1}"
            initial_url = ""

        diag = tk.Toplevel(self.root)
        diag.title("Edit Webhook" if is_edit else "Add Webhook")
        diag.geometry("450x250")
        diag.configure(bg=COLORS["bg_root"])
        diag.transient(self.root)
        diag.grab_set()

        f = tk.Frame(diag, bg=COLORS["bg_root"], padx=20, pady=20)
        f.pack(fill="both", expand=True)
        tk.Label(f, text="Webhook Name:", bg=COLORS["bg_root"], fg=COLORS["fg_dim"]).pack(anchor="w")
        name_e = tk.Entry(f, bg=COLORS["bg_input"], fg=COLORS["fg_text"], relief="flat")
        name_e.pack(fill="x", pady=(2, 10), ipady=3)
        name_e.insert(0, initial_name)
        tk.Label(f, text="Webhook URL:", bg=COLORS["bg_root"], fg=COLORS["fg_dim"]).pack(anchor="w")
        url_e = tk.Entry(f, bg=COLORS["bg_input"], fg=COLORS["fg_text"], relief="flat")
        url_e.pack(fill="x", pady=(2, 15), ipady=3)
        url_e.insert(0, initial_url)

        def _save():
            name = name_e.get().strip()
            url = url_e.get().strip()
            if not url or not ("discord.com" in url):
                messagebox.showerror("Error", "Invalid Discord Webhook URL")
                return
            whs = self.log_monitor_state.config.get("webhooks", [])
            if is_edit and edit_idx < len(whs):
                whs[edit_idx] = {"name": name, "url": url, "enabled": whs[edit_idx].get("enabled", True)}
            else:
                whs.append({"name": name, "url": url, "enabled": True})
            self.log_monitor_state.config["webhooks"] = whs
            self.log_monitor_manager._save_config()
            _render_webhooks()
            diag.destroy()

        btn_f = tk.Frame(f, bg=COLORS["bg_root"])
        btn_f.pack(fill="x")
        ModernButton(btn_f, COLORS["success"], COLORS["success_hover"], text="Save" if is_edit else "Add Webhook", command=_save).pack(side="right", padx=5)
        ModernButton(btn_f, COLORS["bg_panel"], COLORS["border"], text="Cancel", command=diag.destroy).pack(side="right")

    wh_controls = tk.Frame(wh_container, bg=COLORS["bg_root"])
    wh_controls.pack(fill="x", pady=(10, 0))
    ModernButton(wh_controls, COLORS["accent"], COLORS["accent_hover"], text="+ Add Webhook", width=15, command=lambda: _add_webhook_dialog()).pack(side="left")

    mentions_frame = tk.Frame(wh_controls, bg=COLORS["bg_root"])
    mentions_frame.pack(side="right")
    tk.Label(mentions_frame, text="Ping:", bg=COLORS["bg_root"], fg=COLORS["fg_dim"], font=("Segoe UI", 9)).pack(side="left", padx=(0, 5))
    
    def _toggle_ping():
        self.log_monitor_manager._save_config()

    tk.Checkbutton(mentions_frame, text="@here", variable=self.log_monitor_state.mention_here_var, bg=COLORS["bg_root"], fg=COLORS["fg_text"], activebackground=COLORS["bg_root"], selectcolor=COLORS["bg_input"], command=_toggle_ping).pack(side="left", padx=(0, 5))
    tk.Checkbutton(mentions_frame, text="@everyone", variable=self.log_monitor_state.mention_everyone_var, bg=COLORS["bg_root"], fg=COLORS["fg_text"], activebackground=COLORS["bg_root"], selectcolor=COLORS["bg_input"], command=_toggle_ping).pack(side="left")

    # --- Keywords Section ---
    keywords_frame = SectionFrame(main, text="Keywords to Monitor")
    keywords_frame.pack(fill="x", pady=(0, 15))
    keywords_inner = tk.Frame(keywords_frame, bg=COLORS["bg_root"])
    keywords_inner.pack(fill="x", padx=15, pady=8)
    self.log_monitor_state.keywords_text = tk.Text(keywords_inner, height=4, bg=COLORS["bg_input"], fg=COLORS["fg_text"], relief="flat", font=("Consolas", 10))
    self.log_monitor_state.keywords_text.pack(fill="x")
    existing_keywords = self.log_monitor_state.config.get("keywords", [])
    if existing_keywords:
        self.log_monitor_state.keywords_text.insert("1.0", "\n".join(existing_keywords))
    tk.Label(keywords_inner, text="One keyword per line (case-insensitive)", bg=COLORS["bg_root"], fg=COLORS["fg_dim"], font=("Segoe UI", 9)).pack(anchor="w", pady=(5, 0))

    # --- History Section ---
    history_frame = SectionFrame(main, text="Match History")
    history_frame.pack(fill="x", pady=(0, 15))
    history_inner = tk.Frame(history_frame, bg=COLORS["bg_root"])
    history_inner.pack(fill="x", padx=15, pady=10)
    self.log_history_text = tk.Text(history_inner, height=6, bg=COLORS["bg_input"], fg=COLORS["accent"], relief="flat", font=("Consolas", 9), state="disabled")
    self.log_history_text.pack(fill="x", expand=True)
    
    def _clear_history():
        self.log_history_text.config(state="normal")
        self.log_history_text.delete("1.0", tk.END)
        self.log_history_text.config(state="disabled")
            
    btn_frame = tk.Frame(history_inner, bg=COLORS["bg_root"])
    btn_frame.pack(fill="x", pady=(5, 0))
    ModernButton(btn_frame, COLORS["bg_input"], COLORS["border"], text="Clear History", width=12, command=_clear_history).pack(side="left")

    def _manual_save():
        if hasattr(self, 'log_monitor_manager'):
            self.log_monitor_manager.save_log_monitor_settings(silent=False)
            
    ModernButton(btn_frame, COLORS["bg_input"], COLORS["border"], text="Save Configuration", width=20, command=_manual_save, fg=COLORS.get("success", "#95D5B2")).pack(side="right")

    _render_webhooks()
    # Recursive bind for mousewheel
    self.root.after(100, lambda: bind_mousewheel(spy_frame))

    return spy_frame
