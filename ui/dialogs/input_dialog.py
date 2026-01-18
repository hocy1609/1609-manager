import tkinter as tk
from ui.ui_base import BaseDialog, ModernButton, COLORS

class CustomInputDialog(BaseDialog):
    def __init__(self, parent, title, prompt, initial_value=""):
        super().__init__(parent, title, 400, 200)
        self.result = None

        tk.Label(
            self,
            text=prompt,
            bg=COLORS["bg_root"],
            fg=COLORS["fg_text"],
            font=("Segoe UI", 11),
        ).pack(pady=(20, 10), padx=20, anchor="w")

        self.entry = tk.Entry(
            self,
            bg=COLORS["bg_input"],
            fg=COLORS["fg_text"],
            relief="flat",
            font=("Segoe UI", 11),
            insertbackground="white",
        )
        self.entry.configure(
            highlightthickness=1,
            highlightbackground=COLORS["border"],
            highlightcolor=COLORS["accent"],
        )
        self.entry.pack(fill="x", padx=20, ipady=6)
        self.entry.insert(0, initial_value)

        btn_frame = tk.Frame(self, bg=COLORS["bg_root"])
        btn_frame.pack(fill="x", pady=20, padx=20, side="bottom")

        ModernButton(
            btn_frame,
            COLORS["success"],
            COLORS["success_hover"],
            text="OK",
            width=10,
            command=self.on_ok,
        ).pack(side="right", padx=(10, 0))

        ModernButton(
            btn_frame,
            COLORS["bg_panel"],
            COLORS["border"],
            text="Cancel",
            width=10,
            command=self.destroy,
        ).pack(side="right")

        self.bind("<Return>", lambda e: self.on_ok())
        self.bind("<Escape>", lambda e: self.destroy())

        self.entry.focus_set()
        self.finalize_window(parent)

    def on_ok(self):
        val = self.entry.get().strip()
        if val:
            self.result = val
        self.destroy()
