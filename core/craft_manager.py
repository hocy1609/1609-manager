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
import tkinter as tk
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

    def initialize_state(self):
        """Initialize craft-related state on the app (idempotent)."""
        if getattr(self.app, "_craft_state_initialized", False):
            return

        import tkinter as tk
        from app import CraftState

        self.app.craft_state = CraftState(
            running=False,
            vars={
                "open_sequence": tk.StringVar(value="NUMPAD0,NUMPAD4,NUMPAD2"),
                "delay_open": tk.DoubleVar(value=4.0), # Increased delay for initial menu open
                "delay_key": tk.DoubleVar(value=0.2),
                "delay_between": tk.DoubleVar(value=0.2), # Increased delay between crafts
                "potion_limit": tk.IntVar(value=100),
            },
            log_path=tk.StringVar(value=""),
            log_position=0,
            real_count=0,
            potions_count=0,
            thread=None,
        )

        # Log monitoring for potion counting
        default_log = os.path.join(
            os.path.expanduser("~"),
            "Documents",
            "Neverwinter Nights",
            "logs",
            "nwclientLog1.txt",
        )
        if os.path.exists(default_log):
            self.app.craft_state.log_path.set(default_log)

        self.load_favorites()
        self.app._craft_state_initialized = True

    def load_favorites(self):
        """Load favorite potions from file."""
        self.favorites = set()
        try:
            path = os.path.join(self.app.data_dir, "craft_favorites.json")
            if os.path.exists(path):
                with open(path, "r") as f:
                    self.favorites = set(json.load(f))
        except Exception as e:
            print(f"Error loading favorites: {e}")

    def save_favorites(self):
        """Save favorite potions to file."""
        try:
            path = os.path.join(self.app.data_dir, "craft_favorites.json")
            with open(path, "w") as f:
                json.dump(list(self.favorites), f)
        except Exception as e:
            print(f"Error saving favorites: {e}")

    def toggle_favorite(self, seq, parent_frame):
        """Toggle favorite status and refresh list."""
        if seq in self.favorites:
            self.favorites.remove(seq)
        else:
            self.favorites.add(seq)
        self.save_favorites()
        self._populate_craft_list(parent_frame)
    
    def _craft_row(self, parent, row, label, var):
        """Create a settings row in grid."""
        import tkinter as tk
        tk.Label(parent, text=label, bg=COLORS["bg_root"], fg=COLORS["fg_dim"], anchor="w").grid(
            row=row, column=0, sticky="w", pady=2
        )
        tk.Entry(
            parent, textvariable=var, width=25, bg=COLORS["bg_input"], 
            fg=COLORS["fg_text"], relief="flat", insertbackground=COLORS["fg_text"]
        ).grid(row=row, column=1, sticky="w", padx=(10, 0), pady=2)
    
    def _populate_craft_list(self, parent_frame):
        """Populate potion list with checkboxes and quantity sliders."""
        import tkinter as tk
        from ui.ui_base import ModernButton
        
        # Clear existing
        for widget in parent_frame.winfo_children():
            widget.destroy()
            
        self.craft_queue = {}  # sequence -> (name, var_bool, var_int, lbl)
        
        # Sort recipes: Favorites first, then Alphabetical
        sorted_recipes = sorted(
            self.app.potion_recipes,
            key=lambda x: (0 if x[1] in self.favorites else 1, x[0])
        )
        
        for name, seq in sorted_recipes:
            row = tk.Frame(parent_frame, bg=COLORS["bg_input"])
            row.pack(fill="x", padx=5, pady=2)
            
            # Favorite Button (Heart)
            is_fav = seq in self.favorites
            heart_char = "♥" if is_fav else "♡"
            heart_color = COLORS["danger"] if is_fav else COLORS["fg_dim"]
            
            btn_fav = tk.Button(
                row, text=heart_char, bg=COLORS["bg_input"], fg=heart_color,
                bd=0, activebackground=COLORS["bg_input"], activeforeground=COLORS["danger"],
                font=("Segoe UI", 12), width=3, cursor="hand2",
                command=lambda s=seq, p=parent_frame: self.toggle_favorite(s, p)
            )
            btn_fav.pack(side="left")
            
            # Checkbox (Hidden, managed by slider)
            var_bool = tk.BooleanVar(value=False)
            
            # Name
            lbl = tk.Label(
                row, text=name, bg=COLORS["bg_input"], fg=COLORS["fg_text"],
                font=("Segoe UI", 10), anchor="w"
            )
            lbl.pack(side="left", fill="x", expand=True, padx=(5, 0))
            
            # Quantity Slider (Scale) 0-99 & Entry
            var_int = tk.IntVar(value=0)
            
            # 1. Slider (Pack Right)
            scale = tk.Scale(
                row, from_=0, to=99, orient="horizontal", variable=var_int,
                bg=COLORS["bg_input"], fg=COLORS["fg_text"], troughcolor=COLORS["bg_root"],
                activebackground=COLORS["accent"],
                highlightthickness=0, length=120, showvalue=False, # Hide value on slider, use Entry
            )
            scale.pack(side="right", padx=(5, 10))
            
            # 2. Entry (Pack Right, to the left of slider)
            entry = tk.Entry(
                row, textvariable=var_int, width=3,
                bg=COLORS["bg_input"], fg=COLORS["fg_text"],
                insertbackground=COLORS["fg_text"], relief="flat",
                justify="center"
            )
            entry.pack(side="right", padx=(0, 0))
            
            # Monitor changes (trace) to auto-toggle
            var_int.trace_add("write", lambda *_: self._on_quantity_change(seq))
            
            # Save refs
            self.craft_queue[seq] = (name, var_bool, var_int, lbl)
            
            # Bind click on label/row to toggle 1/0
            def toggle(e, vi=var_int):
                if vi.get() > 0:
                    vi.set(0)
                else:
                    vi.set(1)
                
            lbl.bind("<Button-1>", toggle)

    def _on_quantity_change(self, seq):
        """Handle quantity change (slider or entry)."""
        try:
            name, var_bool, var_int, lbl = self.craft_queue[seq]
            try:
                val = var_int.get()
            except:
                val = 0
            
            if val > 0 and not var_bool.get():
                var_bool.set(True)
                self._update_label_style(lbl, True)
            elif val == 0 and var_bool.get():
                var_bool.set(False)
                self._update_label_style(lbl, False)
        except Exception:
            pass

    def _on_queue_change(self, seq):
        """Handle checkbox change."""
        name, var_bool, var_int, lbl = self.craft_queue[seq]
        
        if var_bool.get():
            if var_int.get() == 0:
                var_int.set(1) # Default to 1 if checked
            self._update_label_style(lbl, True)
        else:
            var_int.set(0) # Reset to 0 if unchecked
            self._update_label_style(lbl, False)
            
    def _update_label_style(self, lbl, active):
        if active:
            lbl.config(fg=COLORS["accent"], font=("Segoe UI", 10, "bold"))
        else:
            lbl.config(fg=COLORS["fg_text"], font=("Segoe UI", 10))

    def _reset_queue(self):
        """Reset all selections."""
        for name, var_bool, var_int, lbl in self.craft_queue.values():
            var_bool.set(False)
            var_int.set(0)
            lbl.config(fg=COLORS["fg_text"], font=("Segoe UI", 10))

    def _build_craft_queue(self):
        """Build list of (name, sequence, count) from UI."""
        queue = []
        for seq, (name, var_bool, var_int, lbl) in self.craft_queue.items():
            if var_int.get() > 0:
                queue.append((name, seq, var_int.get()))
        return queue
    
    def craft_start(self):
        """Start crafting process."""
        if self.app.craft_state.running:
            return
        
        self.app.craft_state.running = True
        self.app.craft_state.potions_count = 0
        self.app.craft_btn_start.configure(state="disabled")
        self.app.craft_btn_stop.configure(state="normal")
        self.app.craft_status_lbl.config(text="Status: Running... (0 potions)", fg=COLORS["success"])
        
        self.app.craft_state.thread = threading.Thread(target=self._craft_loop, daemon=True)
        self.app.craft_state.thread.start()
    
    def craft_stop(self):
        """Stop crafting process."""
        self.app.craft_state.running = False
        self.app.craft_status_lbl.config(text="Останавливаем...", fg=COLORS["warning"])
    
    def _craft_loop(self):
        """Main craft loop - runs in thread."""
        from utils.win_automation import press_key_by_name
        
        # Initialize loop vars safely
        total_requested = 0
        
        try:
            delay_open = self.app.craft_state.vars["delay_open"].get()
            delay_key = self.app.craft_state.vars["delay_key"].get()
            delay_between = self.app.craft_state.vars["delay_between"].get()
            open_seq_str = self.app.craft_state.vars["open_sequence"].get()
            
            queue = self._build_craft_queue()
            if not queue:
                self.app.root.after(0, lambda: messagebox.showwarning("Queue Empty", "Select potions to craft!", parent=self.app.root))
                return

            # Parse open sequence (comma-separated key names)
            open_keys = [k.strip() for k in open_seq_str.split(",") if k.strip()]
            
            total_requested = sum(c for _, _, c in queue)
            print(f"[Craft] Starting queue: {len(queue)} types, {total_requested} total items")
            
            # Countdown with hint to switch to NWN
            for i in range(3, 0, -1):
                if not self.app.craft_state.running:
                    return
                self.app.root.after(0, lambda n=i: self.app.craft_status_lbl.config(
                    text=f"Переключись на NWN! {n}...", fg=COLORS["warning"]))
                time.sleep(1)
            
            self.app.root.after(0, lambda: self.app.craft_status_lbl.config(
                text="Крафтим...", fg=COLORS["success"]))

            # Initialize log monitoring (same as before)
            log_path = self.app.craft_state.log_path.get()
            if log_path and os.path.exists(log_path):
                try:
                    with open(log_path, 'r', encoding='cp1251', errors='ignore') as f:
                        f.seek(0, 2)
                        self.app.craft_state.log_position = f.tell()
                    self.app.craft_state.real_count = 0
                except Exception:
                    log_path = None
            else:
                log_path = None

            # Step 1: Open craft menu (ONCE)
            print(f"[Craft] Opening menu")
            for key in open_keys:
                if not self.app.craft_state.running:
                    break
                press_key_by_name(key)
                time.sleep(0.05) # Very fast
            
            # Wait for menu to fully open (3.5s default)
            if self.app.craft_state.running:
                if not self._craft_sleep(delay_open):
                    return

            # Process queue
            for name, seq, count in queue:
                if not self.app.craft_state.running:
                    break
                
                print(f"[Craft] Processing: {name} (x{count})")
                
                for i in range(count):
                    if not self.app.craft_state.running:
                        break
                    
                    # Step 2: Select potion (Fast)
                    # print(f"[Craft] Selecting {name}: {seq}")
                    for char in seq:
                        if not self.app.craft_state.running:
                             break
                        press_key_by_name(char)
                        time.sleep(delay_key)
                    
                    if not self.app.craft_state.running:
                        break
                        
                    # Confirm
                    time.sleep(delay_key)
                    press_key_by_name("1")
                    
                    self.app.craft_state.potions_count += 1
                    
                    # Update status
                    real_c = self._check_craft_log(log_path) if log_path else self.app.craft_state.potions_count
                    attempts = self.app.craft_state.potions_count
                    
                    self.app.root.after(0, lambda n=name, r=real_c, t=total_requested, a=attempts: self.app.craft_status_lbl.config(
                        text=f"Crafting: {n}\nActual: {r} / {t} (Attempts: {a})", fg=COLORS["success"]))
                    
                    # Pause between crafts (minimal delay 0.5s)
                    if not self._craft_sleep(delay_between):
                        break

        except Exception as e:
            self.app.log_error("craft_loop", e)
        finally:
            # Press ESC to close menu
            if self.app.craft_state.running: # Only if finished naturally, or even if stopped? User asked "at the end"
                print("[Craft] Finishing: Pressing ESC")
                try:
                    press_key_by_name("ESC")
                except:
                    pass
            
            self.app.craft_state.running = False
            # Safely reset UI passing the value directly (avoids lambda closure issues)
            self.app.root.after(0, self._craft_reset_ui, total_requested)

    def _craft_reset_ui(self, total_requested=0):
        """Reset craft UI after stop."""
        self.app.craft_btn_start.configure(state="normal")
        self.app.craft_btn_stop.configure(state="disabled")
        
        real_count = self.app.craft_state.real_count
        attempts = self.app.craft_state.potions_count
        
        msg = f"Finished! Actual: {real_count} / {total_requested} (Attempts: {attempts})"
        if attempts < total_requested: # Stopped early
             msg = f"Stopped. Actual: {real_count} / {total_requested} (Attempts: {attempts})"
             
        color = COLORS["success"] if (real_count >= total_requested and total_requested > 0) else COLORS["warning"]
        
        self.app.craft_status_lbl.config(text=msg, fg=color)
    
    def _craft_sleep(self, seconds):
        """Sleep with interrupt check."""
        steps = int(seconds / 0.1)
        for _ in range(steps):
            if not self.app.craft_state.running:
                return False
            time.sleep(0.1)
        rem = seconds - (steps * 0.1)
        if rem > 0:
            time.sleep(rem)
        return self.app.craft_state.running
    

    
    def _check_craft_log(self, log_path):
        """Check log file for Acquired Item entries."""
        import re
        
        if not log_path or not os.path.exists(log_path):
            return self.app.craft_state.real_count
        
        try:
            with open(log_path, 'r', encoding='cp1251', errors='ignore') as f:
                f.seek(self.app.craft_state.log_position)
                new_content = f.read()
                self.app.craft_state.log_position = f.tell()
                
                # Count "Acquired Item:" entries with "Зелье" (potion)
                matches = re.findall(r'Acquired Item:.*(?:Зелье|зелье|Potion)', new_content, re.IGNORECASE)
                if not matches:
                    matches = re.findall(r'Acquired Item:', new_content)
                
                self.app.craft_state.real_count += len(matches)
                
                if matches:
                    print(f"[Craft] Found {len(matches)} items in log, total: {self.app.craft_state.real_count}")
        except Exception as e:
            print(f"[Craft] Log read error: {e}")
        
        return self.app.craft_state.real_count
    



