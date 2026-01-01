"""
Craft Manager for NWN Manager.

This module handles all crafting-related operations including:
- Potion crafting automation
- Macro recording and playback
- Craft UI helpers
"""

import os
import time
import json
import threading
from tkinter import messagebox, filedialog

from ui.ui_base import COLORS


class CraftManager:
    """
    Manages crafting operations for NWN Manager.
    
    Takes a reference to the main app to access its state and UI elements.
    """
    
    def __init__(self, app):
        """
        Initialize the CraftManager.
        
        Args:
            app: Reference to the NWNManagerApp instance
        """
        self.app = app
    
    def _craft_row(self, parent, row, label, var):
        """Create a settings row in grid."""
        import tkinter as tk
        tk.Label(parent, text=label, bg=COLORS["bg_root"], fg=COLORS["fg_dim"], anchor="w").grid(
            row=row, column=0, sticky="w", pady=2
        )
        tk.Entry(
            parent, textvariable=var, width=12, bg=COLORS["bg_input"], 
            fg=COLORS["fg_text"], relief="flat", insertbackground=COLORS["fg_text"]
        ).grid(row=row, column=1, sticky="w", padx=(10, 0), pady=2)
    
    def _populate_potion_list(self):
        """Populate the potion list with favorites first."""
        import tkinter as tk
        
        # Clear existing
        for widget in self.app.potions_frame.winfo_children():
            widget.destroy()
        
        # Sort: favorites first, then rest
        favorites = [p for p in self.app.potion_list if p in self.app.favorite_potions]
        others = [p for p in self.app.potion_list if p not in self.app.favorite_potions]
        sorted_potions = favorites + others
        
        for idx, potion_name in enumerate(sorted_potions):
            is_fav = potion_name in self.app.favorite_potions
            row = tk.Frame(self.app.potions_frame, bg=COLORS["bg_input"])
            row.pack(fill="x", padx=5, pady=2)
            
            # Heart button
            heart = "❤️" if is_fav else "🤍"
            heart_btn = tk.Label(
                row, text=heart, bg=COLORS["bg_input"], 
                fg=COLORS["danger"] if is_fav else COLORS["fg_dim"],
                font=("Segoe UI", 12), cursor="hand2"
            )
            heart_btn.pack(side="left", padx=(0, 10))
            heart_btn.bind("<Button-1>", lambda e, p=potion_name: self._toggle_favorite(p))
            
            # Potion name (clickable)
            name_lbl = tk.Label(
                row, text=potion_name, bg=COLORS["bg_input"],
                fg=COLORS["accent"] if is_fav else COLORS["fg_text"],
                font=("Segoe UI", 10), cursor="hand2", anchor="w"
            )
            name_lbl.pack(side="left", fill="x", expand=True)
            name_lbl.bind("<Button-1>", lambda e, p=potion_name: self._select_potion(p))
            
            # Hover effect
            def on_enter(e, r=row):
                r.configure(bg=COLORS["border"])
                for w in r.winfo_children():
                    w.configure(bg=COLORS["border"])
            def on_leave(e, r=row):
                r.configure(bg=COLORS["bg_input"])
                for w in r.winfo_children():
                    w.configure(bg=COLORS["bg_input"])
            row.bind("<Enter>", on_enter)
            row.bind("<Leave>", on_leave)
    
    def _toggle_favorite(self, potion_name):
        """Toggle favorite status for a potion."""
        if potion_name in self.app.favorite_potions:
            self.app.favorite_potions.discard(potion_name)
        else:
            self.app.favorite_potions.add(potion_name)
        
        # Save to file
        # Save to file
        if hasattr(self.app, 'schedule_save'):
            self.app.schedule_save()
        else:
            self.app.save_data()
        
        # Refresh list (favorites will be at top)
        self._populate_potion_list()
    
    def _select_potion(self, potion_name):
        """Select a potion for crafting."""
        self.app.craft_vars["selected_potion"].set(potion_name)
        self.app.selected_potion_lbl.config(text=potion_name)
        if potion_name in self.app.potion_sequences:
            self.app.craft_vars["sequence"].set(self.app.potion_sequences[potion_name])
    
    def _on_potion_selected(self, event=None):
        """When potion is selected from dropdown, set the sequence."""
        selected = self.app.craft_vars["selected_potion"].get()
        if selected in self.app.potion_sequences:
            seq = self.app.potion_sequences[selected]
            self.app.craft_vars["sequence"].set(seq)
    
    def craft_start(self):
        """Start crafting process."""
        if self.app.craft_running:
            return
        
        self.app.craft_running = True
        self.app.craft_potions_count = 0
        self.app.craft_btn_start.configure(state="disabled")
        self.app.craft_btn_stop.configure(state="normal")
        self.app.craft_status_lbl.config(text="Status: Running... (0 potions)", fg=COLORS["success"])
        
        self.app.craft_thread = threading.Thread(target=self._craft_loop, daemon=True)
        self.app.craft_thread.start()
    
    def craft_stop(self):
        """Stop crafting process."""
        self.app.craft_running = False
        self.app.craft_status_lbl.config(
            text=f"Status: Stopped ({self.app.craft_potions_count} potions)", 
            fg=COLORS["warning"]
        )
    
    def _craft_loop(self):
        """Main craft loop - runs in thread."""
        from utils.win_automation import press_key_by_name
        try:
            delay_action = self.app.craft_vars["delay_action"].get()
            delay_first = self.app.craft_vars["delay_first"].get()
            delay_seq = self.app.craft_vars["delay_seq"].get()
            delay_r = self.app.craft_vars["delay_r"].get()
            repeat_before_r = self.app.craft_vars["repeat_before_r"].get()
            seq_str = self.app.craft_vars["sequence"].get()
            action_key = self.app.craft_vars["action_key"].get()
            potion_limit = self.app.craft_vars["potion_limit"].get()
            
            print(f"[Craft] Settings: action_key={action_key}, sequence={seq_str}, repeats={repeat_before_r}, limit={potion_limit}")
            print(f"[Craft] Delays: action={delay_action}, first={delay_first}, seq={delay_seq}, r={delay_r}")
            
            # Countdown with hint to switch to NWN
            for i in range(3, 0, -1):
                if not self.app.craft_running:
                    return
                self.app.root.after(0, lambda n=i: self.app.craft_status_lbl.config(
                    text=f"Переключись на NWN! {n}...", fg=COLORS["warning"]))
                time.sleep(1)
            
            self.app.root.after(0, lambda: self.app.craft_status_lbl.config(
                text="Крафтим...", fg=COLORS["success"]))

            # Initialize log monitoring
            log_path = self.app.craft_log_path.get()
            if log_path and os.path.exists(log_path):
                try:
                    with open(log_path, 'r', encoding='cp1251', errors='ignore') as f:
                        f.seek(0, 2)  # To end of file
                        self.app.craft_log_position = f.tell()
                    self.app.craft_real_count = 0
                    print(f"[Craft] Log monitoring enabled: {log_path}, position: {self.app.craft_log_position}")
                except Exception as e:
                    print(f"[Craft] Log monitoring failed: {e}")
                    log_path = None
            else:
                log_path = None
                print(f"[Craft] Log monitoring disabled")

            while self.app.craft_running:
                # Craft repeat_before_r potions
                for craft_idx in range(repeat_before_r):
                    if not self.app.craft_running:
                        break
                    if potion_limit > 0 and self.app.craft_potions_count >= potion_limit:
                        self.app.craft_running = False
                        break
                    
                    is_first = (craft_idx == 0)  # First craft after R
                    
                    # Open craft menu
                    print(f"[Craft] Pressing {action_key} to open menu{' (first after R)' if is_first else ''}")
                    press_key_by_name(action_key)
                    
                    # For first craft use increased delay
                    current_delay = delay_action + delay_first if is_first else delay_action
                    if not self._craft_sleep(current_delay):
                        break

                    # Press sequence to select potion
                    print(f"[Craft] Pressing sequence: {seq_str}")
                    for char in seq_str:
                        if not self.app.craft_running:
                            break
                        print(f"[Craft] Pressing key: {char}")
                        press_key_by_name(char)
                        time.sleep(0.5)
                    
                    if not self.app.craft_running:
                        break
                    
                    # Wait for craft completion
                    if not self._craft_sleep(delay_seq):
                        break
                    
                    self.app.craft_potions_count += 1
                    
                    # Check log for real potion count
                    real_count = self._check_craft_log(log_path) if log_path else self.app.craft_potions_count
                    
                    print(f"[Craft] Potion #{self.app.craft_potions_count} crafted ({craft_idx + 1}/{repeat_before_r}), real from log: {real_count}")
                    self.app.root.after(0, lambda c=self.app.craft_potions_count, r=real_count: self.app.craft_status_lbl.config(
                        text=f"Крафтим... ({c} нажатий, {r} зелий)"))
                
                if not self.app.craft_running:
                    break
                if potion_limit > 0 and self.app.craft_potions_count >= potion_limit:
                    break
                
                # Rest (R)
                print(f"[Craft] Pressing R (rest)")
                press_key_by_name("R")
                if not self._craft_sleep(delay_r):
                    break

        except Exception as e:
            self.app.log_error("craft_loop", e)
        finally:
            self.app.craft_running = False
            self.app.root.after(0, self._craft_reset_ui)
    
    def _craft_sleep(self, seconds):
        """Sleep with interrupt check."""
        steps = int(seconds / 0.1)
        for _ in range(steps):
            if not self.app.craft_running:
                return False
            time.sleep(0.1)
        rem = seconds - (steps * 0.1)
        if rem > 0:
            time.sleep(rem)
        return self.app.craft_running
    
    def _craft_reset_ui(self):
        """Reset craft UI after stop."""
        self.app.craft_btn_start.configure(state="normal")
        self.app.craft_btn_stop.configure(state="disabled")
        real_count = self.app.craft_real_count if hasattr(self.app, 'craft_real_count') else self.app.craft_potions_count
        self.app.craft_status_lbl.config(
            text=f"Остановлено ({self.app.craft_potions_count} нажатий, {real_count} зелий)", 
            fg=COLORS["danger"]
        )
    
    def _check_craft_log(self, log_path):
        """Check log file for Acquired Item entries."""
        import re
        
        if not log_path or not os.path.exists(log_path):
            return self.app.craft_real_count
        
        try:
            with open(log_path, 'r', encoding='cp1251', errors='ignore') as f:
                f.seek(self.app.craft_log_position)
                new_content = f.read()
                self.app.craft_log_position = f.tell()
                
                # Count "Acquired Item:" entries with "Зелье" (potion)
                matches = re.findall(r'Acquired Item:.*(?:Зелье|зелье|Potion)', new_content, re.IGNORECASE)
                if not matches:
                    matches = re.findall(r'Acquired Item:', new_content)
                
                self.app.craft_real_count += len(matches)
                
                if matches:
                    print(f"[Craft] Found {len(matches)} items in log, total: {self.app.craft_real_count}")
        except Exception as e:
            print(f"[Craft] Log read error: {e}")
        
        return self.app.craft_real_count
    
    def _browse_craft_log(self):
        """Browse for NWN log file."""
        initial_dir = os.path.join(os.path.expanduser("~"), "Documents", "Neverwinter Nights", "logs")
        if not os.path.exists(initial_dir):
            initial_dir = os.path.expanduser("~")
        
        filepath = filedialog.askopenfilename(
            title="Select NWN Log File (nwclientLog1.txt)",
            initialdir=initial_dir,
            filetypes=[("Log files", "*.txt"), ("All files", "*.*")]
        )
        if filepath:
            self.app.craft_log_path.set(filepath)
    
    def _open_craft_settings(self):
        """Open craft settings dialog."""
        from ui.ui_base import ModernButton
        
        dialog = tk.Toplevel(self.app.root)
        dialog.title("Craft Settings")
        dialog.geometry("450x150")
        dialog.configure(bg=COLORS["bg_root"])
        dialog.transient(self.app.root)
        dialog.grab_set()
        
        # Center on parent
        dialog.update_idletasks()
        x = self.app.root.winfo_x() + (self.app.root.winfo_width() - 450) // 2
        y = self.app.root.winfo_y() + (self.app.root.winfo_height() - 150) // 2
        dialog.geometry(f"+{x}+{y}")
        
        content = tk.Frame(dialog, bg=COLORS["bg_root"])
        content.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Log path
        tk.Label(content, text="NWN Log Path:", bg=COLORS["bg_root"], fg=COLORS["fg_dim"]).pack(anchor="w")
        
        log_row = tk.Frame(content, bg=COLORS["bg_root"])
        log_row.pack(fill="x", pady=(5, 15))
        
        log_entry = tk.Entry(
            log_row, textvariable=self.app.craft_log_path, 
            bg=COLORS["bg_input"], fg=COLORS["fg_text"], relief="flat"
        )
        log_entry.pack(side="left", fill="x", expand=True, ipady=3)
        
        ModernButton(
            log_row,
            COLORS["bg_panel"],
            COLORS["border"],
            text="...",
            command=self._browse_craft_log,
            width=3
        ).pack(side="right", padx=(5, 0))
        
        # Info
        tk.Label(
            content, 
            text="Log used to count real crafted potions (Acquired Item entries)",
            bg=COLORS["bg_root"], 
            fg=COLORS["fg_dim"],
            font=("Segoe UI", 9)
        ).pack(anchor="w")
        
        # Close button
        ModernButton(
            content,
            COLORS["accent"],
            COLORS["accent_hover"],
            text="OK",
            command=dialog.destroy,
            width=10
        ).pack(pady=(15, 0))

    def craft_start_recording(self):
        """Start recording a drag macro after 3 second delay."""
        self.app.craft_btn_record.configure(state="disabled")
        self.app.macro_status_lbl.config(text="Recording in 3...", fg=COLORS["warning"])
        
        def countdown_and_record():
            # Countdown
            for i in range(3, 0, -1):
                self.app.root.after(0, lambda n=i: self.app.macro_status_lbl.config(text=f"Recording in {n}... Switch to NWN!"))
                time.sleep(1)
            
            self.app.root.after(0, lambda: self.app.macro_status_lbl.config(text="🔴 RECORDING... Alt+Tab to stop", fg=COLORS["danger"]))
            
            # Start recording
            from utils.win_automation import get_macro_recorder
            recorder = get_macro_recorder()
            
            def on_recording_done(events):
                self.app.recorded_macro = events
                event_count = len(events)
                if event_count > 0:
                    # Calculate duration
                    duration = events[-1][0] if events else 0
                    self.app.root.after(0, lambda: (
                        self.app.macro_status_lbl.config(text=f"✓ Recorded: {event_count} events, {duration:.1f}s", fg=COLORS["success"]),
                        self.app.craft_btn_record.configure(state="normal")
                    ))
                else:
                    self.app.root.after(0, lambda: (
                        self.app.macro_status_lbl.config(text="No events recorded", fg=COLORS["fg_dim"]),
                        self.app.craft_btn_record.configure(state="normal")
                    ))
            
            recorder.start_recording(callback_on_stop=on_recording_done)
        
        threading.Thread(target=countdown_and_record, daemon=True).start()
    
    def craft_clear_macro(self):
        """Clear recorded macro."""
        self.app.recorded_macro = []
        self.app.macro_status_lbl.config(text="No macro recorded", fg=COLORS["fg_dim"])
    
    def craft_save_macro(self):
        """Save current macro to file (with speed setting)."""
        from ui.dialogs import CustomInputDialog
        
        if not self.app.recorded_macro:
            messagebox.showwarning("No Macro", "Record a macro first!")
            return
        
        dialog = CustomInputDialog(self.app.root, "Save Macro", "Enter macro name:")
        self.app.root.wait_window(dialog)
        
        name = getattr(dialog, 'result', None)
        if not name:
            return
        
        # Sanitize name
        name = "".join(c for c in name if c.isalnum() or c in " _-").strip()
        if not name:
            return
        
        # Save to macros folder
        macros_dir = os.path.join(self.app.data_dir, "macros")
        os.makedirs(macros_dir, exist_ok=True)
        
        macro_path = os.path.join(macros_dir, f"{name}.json")
        try:
            # Save macro with speed setting
            macro_data = {
                "events": self.app.recorded_macro,
                "speed": self.app.craft_vars["macro_speed"].get()
            }
            with open(macro_path, "w", encoding="utf-8") as f:
                json.dump(macro_data, f)
            self._refresh_macro_list()
            self.app.craft_vars["selected_macro"].set(name)
            messagebox.showinfo("Saved", f"Macro '{name}' saved!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save: {e}")
    
    def craft_load_selected_macro(self, event=None):
        """Load selected macro from dropdown (with speed setting)."""
        name = self.app.craft_vars["selected_macro"].get()
        if not name:
            return
        
        macros_dir = os.path.join(self.app.data_dir, "macros")
        macro_path = os.path.join(macros_dir, f"{name}.json")
        
        try:
            with open(macro_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # Support both old format (list) and new format (dict with events + speed)
            if isinstance(data, list):
                self.app.recorded_macro = data
            else:
                self.app.recorded_macro = data.get("events", [])
                # Restore speed setting
                if "speed" in data:
                    self.app.craft_vars["macro_speed"].set(data["speed"])
            
            event_count = len(self.app.recorded_macro)
            duration = self.app.recorded_macro[-1][0] if self.app.recorded_macro else 0
            self.app.macro_status_lbl.config(text=f"Loaded: {event_count} events, {duration:.1f}s", fg=COLORS["success"])
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load: {e}")
    
    def craft_delete_macro(self):
        """Delete selected macro."""
        name = self.app.craft_vars["selected_macro"].get()
        if not name:
            return
        
        if not messagebox.askyesno("Delete", f"Delete macro '{name}'?"):
            return
        
        macros_dir = os.path.join(self.app.data_dir, "macros")
        macro_path = os.path.join(macros_dir, f"{name}.json")
        
        try:
            os.remove(macro_path)
            self._refresh_macro_list()
            self.app.craft_vars["selected_macro"].set("")
            self.app.macro_status_lbl.config(text="Macro deleted", fg=COLORS["fg_dim"])
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete: {e}")
    
    def _refresh_macro_list(self):
        """Refresh list of saved macros."""
        macros_dir = os.path.join(self.app.data_dir, "macros")
        if not os.path.exists(macros_dir):
            self.app.macro_combo["values"] = []
            return
        
        macros = []
        for f in os.listdir(macros_dir):
            if f.endswith(".json"):
                macros.append(f[:-5])  # Remove .json
        
        self.app.macro_combo["values"] = sorted(macros)
    
    def craft_drag_potions(self):
        """Play recorded drag macro with Alt+Tab stop."""
        from utils.win_automation import user32, MOUSEEVENTF_LEFTUP
        
        if not self.app.recorded_macro:
            messagebox.showwarning("No Macro", "Please record or load a macro first!\n\nClick RECORD, switch to NWN,\nperform drag action, Alt+Tab to stop.")
            return
        
        repeats = self.app.craft_vars["macro_repeats"].get()
        speed = self.app.craft_vars["macro_speed"].get()
        
        self.app.craft_btn_drag.configure(state="disabled")
        self.app.macro_playback_stop = False
        
        def play_thread():
            try:
                # Try to activate crafter's window automatically
                if self.app.activate_crafter_window():
                    self.app.root.after(0, lambda: self.app.craft_status_lbl.config(text="Crafter activated!", fg=COLORS["success"]))
                    time.sleep(0.3)
                else:
                    # No crafter or failed - countdown for manual switch
                    for i in range(3, 0, -1):
                        self.app.root.after(0, lambda n=i: self.app.craft_status_lbl.config(text=f"Starting in {n}... Switch to NWN!", fg=COLORS["warning"]))
                        time.sleep(1)
                
                target_hwnd = user32.GetForegroundWindow()
                
                played = 0
                for i in range(repeats):
                    if self.app.macro_playback_stop:
                        break
                    
                    # Check for Alt+Tab (window focus change)
                    current_hwnd = user32.GetForegroundWindow()
                    if current_hwnd != target_hwnd:
                        self.app.macro_playback_stop = True
                        break
                    
                    if i > 0:
                        time.sleep(0.3)
                    
                    self.app.root.after(0, lambda n=i+1: self.app.craft_status_lbl.config(text=f"Playing {n}/{repeats}... Alt+Tab to stop"))
                    
                    # Play macro with stop check
                    self._play_macro_interruptible(self.app.recorded_macro, speed, target_hwnd)
                    
                    if not self.app.macro_playback_stop:
                        played += 1
                
                # Ensure mouse released
                user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                
                status = f"Stopped at {played}/{repeats}" if self.app.macro_playback_stop else f"Done! Played {repeats}x"
                color = COLORS["warning"] if self.app.macro_playback_stop else COLORS["success"]
                
                self.app.root.after(0, lambda: (
                    self.app.craft_btn_drag.configure(state="normal"),
                    self.app.craft_status_lbl.config(text=status, fg=color)
                ))
            except Exception as e:
                self.app.root.after(0, lambda: (
                    self.app.craft_btn_drag.configure(state="normal"),
                    self.app.craft_status_lbl.config(text=f"Error: {e}", fg=COLORS["danger"])
                ))
        
        threading.Thread(target=play_thread, daemon=True).start()
    
    def _play_macro_interruptible(self, events, speed_multiplier, target_hwnd):
        """Play macro with Alt+Tab interrupt check."""
        from utils.win_automation import user32, MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP
        
        if not events:
            return
        
        last_time = 0
        for event in events:
            # Check for window change (Alt+Tab)
            if user32.GetForegroundWindow() != target_hwnd:
                self.app.macro_playback_stop = True
                return
            
            if self.app.macro_playback_stop:
                return
            
            timestamp, event_type, x, y = event
            
            # Wait for timing
            delay = (timestamp - last_time) / speed_multiplier
            if delay > 0:
                # Split delay into small chunks for responsive stopping
                while delay > 0.05:
                    if user32.GetForegroundWindow() != target_hwnd:
                        self.app.macro_playback_stop = True
                        return
                    time.sleep(0.05)
                    delay -= 0.05
                if delay > 0:
                    time.sleep(delay)
            last_time = timestamp
            
            # Execute event
            if event_type == "move":
                user32.SetCursorPos(x, y)
            elif event_type == "down":
                user32.SetCursorPos(x, y)
                time.sleep(0.02)
                user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            elif event_type == "up":
                user32.SetCursorPos(x, y)
                time.sleep(0.02)
                user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
