import tkinter as tk
from tkinter import filedialog
from ui.ui_base import BaseDialog, ModernButton, COLORS

class LogMonitorDialog(BaseDialog):
    def __init__(self, parent, config: dict, on_save_config, on_start, on_stop, is_running: bool):
        super().__init__(parent, "Log Monitor", 600, 450)
        self.on_save_config = on_save_config
        self.on_start = on_start
        self.on_stop = on_stop

        # Keep the enabled state from the main app but do not duplicate
        # the 'Enable' control here — monitoring is controlled from
        # the main sidebar checkbox. Store initial enabled value so
        # saving preserves it when the dialog does not change it.
        self.initial_enabled = bool(config.get("enabled", False))
        self.log_path_var = tk.StringVar(value=config.get("log_path", ""))
        self.webhooks = list(config.get("webhooks", []))
        self.keywords = list(config.get("keywords", []))

        content = tk.Frame(self, bg=COLORS["bg_root"])
        content.pack(fill="both", expand=True, padx=20, pady=15)

        tk.Label(
            content,
            text="Log file path (nwclientLog1.txt):",
            bg=COLORS["bg_root"],
            fg=COLORS["fg_dim"],
        ).pack(anchor="w")

        path_row = tk.Frame(content, bg=COLORS["bg_root"])
        path_row.pack(fill="x", pady=(0, 8))

        tk.Entry(
            path_row,
            textvariable=self.log_path_var,
            bg=COLORS["bg_input"],
            fg=COLORS["fg_text"],
            relief="flat",
        ).pack(side="left", fill="x", expand=True, ipady=3)

        ModernButton(
            path_row,
            COLORS["bg_panel"],
            COLORS["border"],
            text="...",
            width=3,
            command=self.browse_log,
        ).pack(side="right", padx=(5, 0))

        # Note: the enable checkbox intentionally omitted here to avoid
        # duplication with the main UI control.

        lists_frame = tk.Frame(content, bg=COLORS["bg_root"])
        lists_frame.pack(fill="both", expand=True)

        self.webhook_list = self._create_list_section(
            lists_frame,
            "Discord Webhooks:",
            self.webhooks,
            side="left",
        )
        self.keyword_list = self._create_list_section(
            lists_frame,
            "Keywords (one per line):",
            self.keywords,
            side="right",
        )

        btn_frame = tk.Frame(self, bg=COLORS["bg_root"])
        btn_frame.pack(fill="x", padx=20, pady=10, side="bottom")

        # Start/Stop monitor controls removed — monitoring is controlled from the main app

        ModernButton(
            btn_frame,
            COLORS["bg_panel"],
            COLORS["border"],
            text="Cancel",
            width=10,
            command=self.destroy,
        ).pack(side="right")

        ModernButton(
            btn_frame,
            COLORS["success"],
            COLORS["success_hover"],
            text="Save",
            width=10,
            command=self.save_and_close,
        ).pack(side="right", padx=(10, 0))

        self.finalize_window(parent)

    def _create_list_section(self, parent, title, items, side):
        frame = tk.Frame(parent, bg=COLORS["bg_root"])
        frame.pack(side=side, fill="both", expand=True, padx=5)

        tk.Label(
            frame,
            text=title,
            bg=COLORS["bg_root"],
            fg=COLORS["fg_dim"],
        ).pack(anchor="w")

        listbox = tk.Listbox(
            frame,
            bg=COLORS["bg_input"],
            fg=COLORS["fg_text"],
            bd=0,
            highlightthickness=1,
            highlightbackground=COLORS["border"],
        )
        listbox.pack(fill="both", expand=True, pady=(0, 5))

        for item in items:
            listbox.insert(tk.END, item)

        entry_row = tk.Frame(frame, bg=COLORS["bg_root"])
        entry_row.pack(fill="x", pady=(0, 5))

        entry = tk.Entry(
            entry_row,
            bg=COLORS["bg_input"],
            fg=COLORS["fg_text"],
            relief="flat",
        )
        entry.pack(side="left", fill="x", expand=True, ipady=3)

        def add_item():
            val = entry.get().strip()
            if val:
                items.append(val)
                listbox.insert(tk.END, val)
                entry.delete(0, tk.END)

        def remove_selected():
            sel = listbox.curselection()
            if not sel:
                return
            idx = sel[0]
            listbox.delete(idx)
            del items[idx]

        def edit_selected():
            sel = listbox.curselection()
            if not sel:
                return
            idx = sel[0]
            current = items[idx]
            entry.delete(0, tk.END)
            entry.insert(0, current)
            listbox.delete(idx)
            del items[idx]

        ModernButton(
            entry_row,
            COLORS["bg_panel"],
            COLORS["border"],
            text="Add",
            width=6,
            command=add_item,
        ).pack(side="right", padx=(5, 0))

        # Delete / Edit buttons row
        btn_row = tk.Frame(frame, bg=COLORS["bg_root"])
        btn_row.pack(fill="x")

        ModernButton(
            btn_row,
            COLORS["danger"],
            COLORS["danger_hover"],
            text="Delete",
            width=8,
            command=remove_selected,
        ).pack(side="left", padx=(0, 3))

        ModernButton(
            btn_row,
            COLORS["bg_panel"],
            COLORS["border"],
            text="Edit",
            width=8,
            command=edit_selected,
        ).pack(side="left")

        # Right-click context menu for delete/edit
        def show_context_menu(event):
            menu = tk.Menu(listbox, tearoff=False, bg=COLORS["bg_panel"], fg=COLORS["fg_text"])
            menu.add_command(label="Delete", command=remove_selected)
            menu.add_command(label="Edit", command=edit_selected)
            try:
                menu.tk_popup(event.x_root, event.y_root)
            finally:
                menu.grab_release()

        listbox.bind("<Button-3>", show_context_menu)

        return listbox

    def browse_log(self):
        f = filedialog.askopenfilename(
            title="Select Neverwinter Nights log file",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if f:
            self.log_path_var.set(f)

    def _collect_config(self) -> dict:
        # Return config; preserve enabled state coming from main app
        # (dialog doesn't provide an enable switch to avoid duplication).
        return {
            "enabled": self.initial_enabled,
            "log_path": self.log_path_var.get().strip(),
            "webhooks": list(self.webhooks),
            "keywords": list(self.keywords),
        }

    def save_and_close(self):
        cfg = self._collect_config()
        self.on_save_config(cfg)
        self.destroy()

    def start_clicked(self):
        cfg = self._collect_config()
        self.on_save_config(cfg)
        self.on_start()

    def stop_clicked(self):
        self.on_stop()
