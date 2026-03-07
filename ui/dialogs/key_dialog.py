import tkinter as tk
from tkinter import ttk, messagebox
from ui.ui_base import BaseDialog, ModernButton, COLORS

class KeyManagerDialog(BaseDialog):
    """Dialog for managing saved CD keys."""
    
    def __init__(self, parent, settings):
        super().__init__(parent, "Manage CD Keys", 700, 500)
        self.settings = settings
        self.registry = self.settings.get_key_registry()
        
        self.selected_key_data = None
        self.create_widgets()
        self.refresh_list()
        self.finalize_window(parent)

    def create_widgets(self):
        padding = 20
        main_frame = tk.Frame(self, bg=COLORS["bg_root"])
        main_frame.pack(fill="both", expand=True, padx=padding, pady=padding)
        
        # Left side: List of keys
        list_frame = tk.Frame(main_frame, bg=COLORS["bg_root"])
        list_frame.pack(side="left", fill="both", expand=True)
        
        tk.Label(
            list_frame, text="Known CD Keys:", 
            bg=COLORS["bg_root"], fg=COLORS["fg_dim"],
            font=("Segoe UI", 10)
        ).pack(anchor="w", pady=(0, 5))
        
        lb_container = tk.Frame(list_frame, bg=COLORS["border"])
        lb_container.pack(fill="both", expand=True)
        
        self.lb = tk.Listbox(
            lb_container,
            bg=COLORS["bg_input"],
            fg=COLORS["fg_text"],
            font=("Segoe UI", 10),
            borderwidth=0,
            highlightthickness=0,
            selectbackground=COLORS["accent"],
            selectforeground="white",
            activestyle="none"
        )
        self.lb.pack(side="left", fill="both", expand=True, padx=1, pady=1)
        self.lb.bind("<<ListboxSelect>>", self.on_select)
        
        sb = ttk.Scrollbar(lb_container, orient="vertical", command=self.lb.yview)
        sb.pack(side="right", fill="y")
        self.lb.config(yscrollcommand=sb.set)
        
        # Right side: Details
        self.details_frame = tk.Frame(main_frame, bg=COLORS["bg_root"], width=300)
        self.details_frame.pack(side="right", fill="both", padx=(padding, 0))
        self.details_frame.pack_propagate(False)
        
        self.name_var = tk.StringVar()
        self.key_val_var = tk.StringVar()
        
        self.edit_container = tk.Frame(self.details_frame, bg=COLORS["bg_root"])
        
        tk.Label(self.edit_container, text="Name / Label:", bg=COLORS["bg_root"], fg=COLORS["fg_dim"], font=("Segoe UI", 9)).pack(anchor="w")
        self.name_entry = tk.Entry(self.edit_container, textvariable=self.name_var, bg=COLORS["bg_input"], fg=COLORS["fg_text"], relief="flat", font=("Segoe UI", 10))
        self.name_entry.pack(fill="x", pady=(2, 10))
        
        tk.Label(self.edit_container, text="CD Key Value:", bg=COLORS["bg_root"], fg=COLORS["fg_dim"], font=("Segoe UI", 9)).pack(anchor="w")
        self.key_entry = tk.Entry(self.edit_container, textvariable=self.key_val_var, bg=COLORS["bg_input"], fg=COLORS["fg_text"], relief="flat", font=("Consolas", 10))
        self.key_entry.pack(fill="x", pady=(2, 5))
        
        self.usage_lbl = tk.Label(self.edit_container, text="Used in: None", bg=COLORS["bg_root"], fg=COLORS["accent"], font=("Segoe UI", 9), wraplength=280, justify="left")
        self.usage_lbl.pack(anchor="w", pady=(5, 15))
        
        ModernButton(self.edit_container, COLORS["success"], COLORS["success_hover"], text="Save Changes", command=self.save_selected).pack(fill="x", pady=5)
        ModernButton(self.edit_container, COLORS["danger"], COLORS["danger_hover"], text="Delete from Saved", command=self.delete_selected).pack(fill="x", pady=5)
        
        bottom_frame = tk.Frame(self, bg=COLORS["bg_panel"])
        bottom_frame.pack(fill="x", side="bottom", ipady=5)
        
        ModernButton(bottom_frame, COLORS["accent"], COLORS["accent_hover"], text="+ Add New Key", command=self.add_new).pack(side="left", padx=padding, ipadx=10)
        ModernButton(bottom_frame, COLORS["bg_root"], COLORS["border"], text="Close", fg=COLORS["fg_text"], command=self.destroy).pack(side="right", padx=padding, ipadx=10)

    def refresh_list(self):
        self.registry = self.settings.get_key_registry()
        self.lb.delete(0, tk.END)
        for k in self.registry:
            key_val = k['key']
            profiles = k['profiles']
            usage = f" ({', '.join(profiles)})" if profiles else " (Unused)"
            self.lb.insert(tk.END, f"{key_val[:17]}...{usage}")
        self.edit_container.pack_forget()
        self.selected_key_data = None

    def on_select(self, event=None):
        selection = self.lb.curselection()
        if not selection: return
        idx = selection[0]
        self.selected_key_data = self.registry[idx]
        self.name_var.set(self.selected_key_data["name"])
        self.key_val_var.set(self.selected_key_data["key"])
        profiles = self.selected_key_data["profiles"]
        self.usage_lbl.config(text="Used in: " + (", ".join(profiles) if profiles else "No profiles"))
        self.edit_container.pack(fill="both", expand=True)

    def save_selected(self):
        if not self.selected_key_data: return
        new_name = self.name_var.get().strip()
        new_key = self.key_val_var.get().strip().upper()
        if not new_name or not new_key: return

        old_key = self.selected_key_data["key"]
        updated_saved = []
        found = False
        for k in self.settings.saved_keys:
            if k.get("key", "").upper() == old_key:
                updated_saved.append({"name": new_name, "key": new_key})
                found = True
            else:
                updated_saved.append(k)
        if not found: updated_saved.append({"name": new_name, "key": new_key})
        self.settings.saved_keys = updated_saved
        self.settings.save() # Ensure save to disk
        messagebox.showinfo("Success", "Key saved.")
        self.refresh_list()

    def delete_selected(self):
        if not self.selected_key_data: return
        key_to_del = self.selected_key_data["key"]
        if messagebox.askyesno("Confirm", f"Remove key '{key_to_del[:10]}...' from saved?"):
            self.settings.saved_keys = [k for k in self.settings.saved_keys if k.get("key", "").upper() != key_to_del]
            self.settings.save()
            self.refresh_list()

    def add_new(self):
        self.lb.selection_clear(0, tk.END)
        self.selected_key_data = {"key": "", "name": "New Key", "profiles": []}
        self.name_var.set("New Key")
        self.key_val_var.set("")
        self.usage_lbl.config(text="New entry")
        self.edit_container.pack(fill="both", expand=True)
