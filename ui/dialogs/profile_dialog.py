import tkinter as tk
from tkinter import ttk, messagebox
from ui.ui_base import BaseDialog, ModernButton, COLORS

class EditDialog(BaseDialog):
    def __init__(self, parent, profile_data=None, existing_categories=None, on_save=None, *, title=None, categories=None, server_list=None, is_new=False, saved_keys=None):
        # Support both calling conventions
        cats = categories or existing_categories or ["General"]
        profile = profile_data if profile_data else {}
        dialog_title = title or ("Add Profile" if is_new else "Edit Profile")
        super().__init__(parent, dialog_title, 550, 700)
        self.on_save = on_save
        self.saved_keys = saved_keys or []

        self.name_var = tk.StringVar(value=getattr(profile, "name", ""))
        self.category_var = tk.StringVar(
            value=getattr(profile, "category", "General")
        )
        self.key_var = tk.StringVar(value=getattr(profile, "cdKey", ""))
        self.player_name_var = tk.StringVar(
            value=getattr(profile, "playerName", "")
        )
        self.server_var = tk.StringVar(
            value=getattr(profile, "server", "")
        )

        self.server_list = server_list or []

        padding = 30
        content = tk.Frame(self, bg=COLORS["bg_root"])
        content.pack(fill="both", expand=True, padx=5, pady=5)

        self.create_field(content, "Profile Name:", self.name_var, padding)

        tk.Label(
            content,
            text="Category:",
            bg=COLORS["bg_root"],
            fg=COLORS["fg_dim"],
            font=("Segoe UI", 10),
        ).pack(anchor="w", padx=padding, pady=(5, 2))

        cat_cb = ttk.Combobox(
            content,
            textvariable=self.category_var,
            values=cats,
            font=("Segoe UI", 11),
        )
        cat_cb.pack(fill="x", padx=padding, ipady=4)

        if self.server_list:
            tk.Label(
                content,
                text="Default Server:",
                bg=COLORS["bg_root"],
                fg=COLORS["fg_dim"],
                font=("Segoe UI", 10),
            ).pack(anchor="w", padx=padding, pady=(10, 2))

            srv_cb = ttk.Combobox(
                content,
                textvariable=self.server_var,
                values=self.server_list,
                font=("Segoe UI", 11),
                state="readonly"
            )
            srv_cb.pack(fill="x", padx=padding, ipady=4)

        # CD Key section with saved keys dropdown
        key_frame = tk.Frame(content, bg=COLORS["bg_root"])
        key_frame.pack(fill="x", padx=padding, pady=(10, 0))
        
        tk.Label(
            key_frame,
            text="CD Key:",
            bg=COLORS["bg_root"],
            fg=COLORS["fg_dim"],
            font=("Segoe UI", 10),
        ).pack(anchor="w")
        
        # Saved keys dropdown (Registry-aware)
        if self.saved_keys:
            key_select_frame = tk.Frame(content, bg=COLORS["bg_root"])
            key_select_frame.pack(fill="x", padx=padding, pady=(2, 5))
            
            tk.Label(
                key_select_frame,
                text="Quick Select:",
                bg=COLORS["bg_root"],
                fg=COLORS["fg_dim"],
                font=("Segoe UI", 9),
            ).pack(side="left")
            
            # Format: "KEY_VALUE (Used in: Player1, Player2)"
            def format_label(k):
                key_val = k.get("key", "")
                profiles = k.get("profiles", [])
                usage = f" (Used in: {', '.join(profiles)})" if profiles else " (Unused)"
                return f"{key_val}{usage}"

            labels = [""] + [format_label(k) for k in self.saved_keys]
            self.key_select_var = tk.StringVar(value="")
            
            def on_key_select(event=None):
                selected_label = self.key_select_var.get()
                if not selected_label: return
                
                # Find by matching the label
                for k in self.saved_keys:
                    if format_label(k) == selected_label:
                        self.key_var.set(k.get("key", ""))
                        break
            
            key_combo = ttk.Combobox(
                key_select_frame,
                textvariable=self.key_select_var,
                values=labels,
                font=("Segoe UI", 9),
                width=40,
                state="readonly"
            )
            key_combo.pack(side="left", padx=(5, 0), fill="x", expand=True)
            key_combo.bind("<<ComboboxSelected>>", on_key_select)
        
        # CD Key entry field
        self.create_field(content, "", self.key_var, padding)
        
        # Small inline hint for expected format
        hint = tk.Label(
            content,
            text="Format: XXXXX-XXXXX-XXXXX-XXXXX-XXXXX-XXXXX-XXXXX",
            bg=COLORS["bg_root"],
            fg=COLORS["fg_dim"],
            font=("Segoe UI", 8),
        )
        hint.pack(anchor="w", padx=padding, pady=(2, 6))

        self.create_field(
            content,
            "Login Name (settings.tml):",
            self.player_name_var,
            padding,
        )

        btn_frame = tk.Frame(self, bg=COLORS["bg_root"])
        btn_frame.pack(
            fill="x", padx=padding, pady=30, side="bottom"
        )

        ModernButton(
            btn_frame,
            COLORS["success"],
            COLORS["success_hover"],
            text="Save",
            font=("Segoe UI", 11, "bold"),
            command=self.save_and_close,
        ).pack(side="right", ipadx=15, ipady=5)

        ModernButton(
            btn_frame,
            COLORS["bg_panel"],
            COLORS["border"],
            text="Cancel",
            font=("Segoe UI", 11),
            fg=COLORS["fg_text"],
            command=self.destroy,
        ).pack(side="right", padx=10, ipadx=10, ipady=5)

        self.finalize_window(parent)

    def create_field(self, parent, label, var, padding):
        if label:
            tk.Label(
                parent,
                text=label,
                bg=COLORS["bg_root"],
                fg=COLORS["fg_dim"],
                font=("Segoe UI", 10),
            ).pack(anchor="w", padx=padding, pady=(5, 2))

        entry = tk.Entry(
            parent,
            textvariable=var,
            bg=COLORS["bg_input"],
            fg=COLORS["fg_text"],
            relief="flat",
            insertbackground="white",
            font=("Segoe UI", 11),
        )
        entry.configure(
            highlightthickness=1,
            highlightbackground=COLORS["border"],
            highlightcolor=COLORS["accent"],
        )
        entry.pack(fill="x", padx=padding, ipady=6)
        return entry

    def save_and_close(self):
        name = self.name_var.get().strip()
        if not name:
            messagebox.showwarning("Validation Error", "Profile Name is required.", parent=self)
            return

        cat = self.category_var.get().strip()
        if not cat:
            cat = "General"
            
        raw_key = (self.key_var.get() or "").strip()
        if not raw_key:
            messagebox.showwarning("Validation Error", "CD Key is required.", parent=self)
            return

        new_data = {
            "name": name,
            "category": cat,
            "cdKey": raw_key,
            "playerName": self.player_name_var.get(),
            "launchArgs": "",
            "server": self.server_var.get(),
        }
        # Validate CD Key format: expect 7 groups of 5 alphanumeric characters separated by '-'
        try:
            raw = (self.key_var.get() or "").strip()
            key = raw.upper()
            import re

            pattern = re.compile(r'^[A-Z0-9]{5}(?:-[A-Z0-9]{5}){6}$')
            if raw and not pattern.match(key):
                messagebox.showerror(
                    "Invalid CD Key",
                    "CD Key must be in format: XXXXX-XXXXX-XXXXX-XXXXX-XXXXX-XXXXX-XXXXX\nPlease check the key and try again.",
                    parent=self,
                )
                return
            new_data["cdKey"] = key
        except Exception:
            # On any unexpected error, fall back to original value
            new_data["cdKey"] = self.key_var.get()

        self.on_save(new_data)
        self.destroy()
