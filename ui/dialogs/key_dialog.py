import tkinter as tk
from tkinter import ttk, messagebox
from ui.ui_base import BaseDialog, ModernButton, COLORS

class AddKeyDialog(BaseDialog):
    def __init__(self, parent, on_save):
        super().__init__(parent, "Add CD Key", 400, 250)
        self.on_save = on_save

        content = tk.Frame(self, bg=COLORS["bg_root"])
        content.pack(fill="both", expand=True, padx=20, pady=20)

        self.name_var = tk.StringVar()
        self.key_var = tk.StringVar()

        tk.Label(
            content,
            text="Key Name (e.g. My Key 1):",
            bg=COLORS["bg_root"],
            fg=COLORS["fg_dim"],
        ).pack(anchor="w")
        tk.Entry(
            content,
            textvariable=self.name_var,
            bg=COLORS["bg_input"],
            fg=COLORS["fg_text"],
            relief="flat",
        ).pack(fill="x", pady=(0, 10), ipady=3)

        tk.Label(
            content,
            text="CD Key:",
            bg=COLORS["bg_root"],
            fg=COLORS["fg_dim"],
        ).pack(anchor="w")
        entry = tk.Entry(
            content,
            textvariable=self.key_var,
            bg=COLORS["bg_input"],
            fg=COLORS["fg_text"],
            relief="flat",
        )
        entry.pack(fill="x", pady=(0, 10), ipady=3)
        
        # Tooltip for format
        hint = tk.Label(
            content,
            text="Format: XXXXX-XXXXX-...",
            bg=COLORS["bg_root"],
            fg=COLORS["fg_dim"],
            font=("Segoe UI", 8),
        )
        hint.pack(anchor="w", pady=(0, 10))


        btn_frame = tk.Frame(content, bg=COLORS["bg_root"])
        btn_frame.pack(fill="x", pady=10, side="bottom")

        def save():
            name = self.name_var.get().strip()
            key = self.key_var.get().strip().upper()
            if name and key:
                self.on_save({"name": name, "key": key})
                self.destroy()
            else:
                messagebox.showwarning("Error", "All fields required", parent=self)

        ModernButton(
            btn_frame,
            COLORS["success"],
            COLORS["success_hover"],
            text="Add",
            width=10,
            command=save,
        ).pack(side="right", padx=(10, 0))

        ModernButton(
            btn_frame,
            COLORS["bg_panel"],
            COLORS["border"],
            text="Cancel",
            width=10,
            command=self.destroy,
        ).pack(side="right")

        self.finalize_window(parent)


class KeyManagementDialog(BaseDialog):
    def __init__(self, parent, keys: list, on_save):
        super().__init__(parent, "Manage CD Keys", 500, 400)
        self.keys = [dict(k) for k in keys]  # Copy
        self.on_save = on_save
        
        content = tk.Frame(self, bg=COLORS["bg_root"])
        content.pack(fill="both", expand=True, padx=20, pady=20)
        
        tk.Label(
            content,
            text="Saved CD Keys:",
            bg=COLORS["bg_root"],
            fg=COLORS["fg_dim"],
            font=("Segoe UI", 10),
        ).pack(anchor="w")
        
        # Key listbox
        list_frame = tk.Frame(content, bg=COLORS["bg_root"])
        list_frame.pack(fill="both", expand=True, pady=(5, 10))
        
        self.lb = tk.Listbox(
            list_frame,
            bg=COLORS["bg_input"],
            fg=COLORS["fg_text"],
            bd=0,
            highlightthickness=1,
            highlightbackground=COLORS["border"],
            font=("Segoe UI", 10),
        )
        self.lb.pack(fill="both", expand=True, side="left")
        
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.lb.yview)
        scrollbar.pack(side="right", fill="y")
        self.lb.config(yscrollcommand=scrollbar.set)
        
        self._refresh_list()
        
        # Action buttons
        btn_frame = tk.Frame(content, bg=COLORS["bg_root"])
        btn_frame.pack(fill="x", pady=(0, 10))
        
        ModernButton(
            btn_frame,
            COLORS["success"],
            COLORS["success_hover"],
            text="Add Key",
            width=10,
            command=self._add_key,
        ).pack(side="left", padx=(0, 5))
        
        ModernButton(
            btn_frame,
            COLORS["danger"],
            COLORS["danger_hover"],
            text="Delete",
            width=8,
            command=self._delete_key,
        ).pack(side="left")
        
        # Save/Cancel
        bottom_frame = tk.Frame(self, bg=COLORS["bg_root"])
        bottom_frame.pack(fill="x", padx=20, pady=10, side="bottom")
        
        ModernButton(
            bottom_frame,
            COLORS["success"],
            COLORS["success_hover"],
            text="Save",
            width=10,
            command=self._save_and_close,
        ).pack(side="right", padx=(10, 0))
        
        ModernButton(
            bottom_frame,
            COLORS["bg_panel"],
            COLORS["border"],
            text="Cancel",
            width=10,
            command=self.destroy,
        ).pack(side="right")
        
        self.finalize_window(parent)
    
    def _refresh_list(self):
        self.lb.delete(0, tk.END)
        for k in self.keys:
            self.lb.insert(tk.END, f"{k['name']} ({k['key'][:5]}...)")
    
    def _add_key(self):
        def on_add(data):
            self.keys.append(data)
            self._refresh_list()
        AddKeyDialog(self, on_add)
    
    def _delete_key(self):
        sel = self.lb.curselection()
        if not sel:
            return
        idx = sel[0]
        key = self.keys[idx]
        if messagebox.askyesno("Confirm", f"Delete key '{key['name']}'?", parent=self):
            del self.keys[idx]
            self._refresh_list()
    
    def _save_and_close(self):
        self.on_save(self.keys)
        self.destroy()
