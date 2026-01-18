import tkinter as tk
from ui.ui_base import BaseDialog, COLORS

class HelpDialog(BaseDialog):
    """Simple help dialog with concise explanations for toggles and Clip Margin."""

    def __init__(self, parent):
        super().__init__(parent, "Settings Help", 520, 280)
        content = tk.Frame(self, bg=COLORS["bg_root"])
        content.pack(fill="both", expand=True, padx=16, pady=16)

        lines = [
            ("Show tooltips:", "Toggle on to show small helper text when hovering action buttons; toggle off to reduce visual noise. Recommended: On for new users, Off for power users."),
            ("Clip Margin (px):", "When mouse-clipping fallback is used during automated Safe Exit, `clip_margin` expands the rectangle kept under control around the target coordinates. Larger margins tolerate small cursor movement; smaller margins are more precise. Recommended: 32–64 px (48 default)."),
            ("Exit Speed / ESC Count:", "Adjust how quickly the automated Safe Exit sequence sends ESCs and confirms; increase ESC Count if logout dialog is slow to appear.")
        ]

        for title, text in lines:
            tk.Label(content, text=title, bg=COLORS["bg_root"], fg=COLORS["fg_dim"], font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(8, 0))
            tk.Label(content, text=text, bg=COLORS["bg_root"], fg=COLORS["fg_text"], wraplength=480, justify="left").pack(anchor="w")

        btn = tk.Button(content, text="Close", command=self.destroy, bg=COLORS["bg_panel"], fg=COLORS["fg_text"], relief="flat", cursor="hand2")
        btn.pack(side="bottom", pady=12)
        
        # Center window without grab_set to avoid freezing parent
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = (sw - 520) // 2
        y = (sh - 280) // 2
        self.geometry(f"520x280+{x}+{y}")
        self.lift()
        self.focus_force()
