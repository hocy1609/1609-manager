import tkinter as tk

from ui.ui_base import COLORS


def build_help_screen(app):
    """Static help screen content."""
    self = app

    help_frame = tk.Frame(self.content_frame, bg=COLORS["bg_root"])
    self.screens["help"] = help_frame

    help_text = """
16:09 Launcher - Neverwinter Nights Enhanced Edition Manager

NAVIGATION:
• 🏠 Home - Manage accounts and launch game
• 🔨 Craft - Auto-crafting and potion management
• ⚙️ Settings - Application settings
• 📊 Log Monitor - Monitor game logs with webhooks
• ❓ Help - This help screen

WORKFLOW:
1. Add profiles in Home screen
2. Configure craft settings in Craft screen
3. Use START button to begin crafting
5. Alt+Tab stops recording and playback

Press ESC to return to Home screen from dialogs.
"""

    tk.Label(
        help_frame,
        text="Help & Documentation",
        font=("Segoe UI", 24, "bold"),
        bg=COLORS["bg_root"],
        fg=COLORS["fg_text"]
    ).pack(pady=20)

    text_widget = tk.Text(
        help_frame,
        wrap="word",
        bg=COLORS["bg_panel"],
        fg=COLORS["fg_text"],
        font=("Segoe UI", 11),
        bd=0,
        padx=20,
        pady=20
    )
    text_widget.pack(fill="both", expand=True, padx=40, pady=20)
    text_widget.insert("1.0", help_text)
    text_widget.config(state="disabled")

    return help_frame
